"""Context for buying signals: how unusual a move is, where the price sits in its
own history, and what the outlook says. Turns these into a signal and a plain
recommendation. Used by analyze.py; checked independently by verify_calcs.py.

Why this design (full references in README.md, "Signals and recommendations"):
- A fixed % threshold treats a 5% move in a calm series the same as in a volatile
  one. Instead each move is ranked against that series' own past moves, the idea
  behind control charts (Montgomery, Introduction to Statistical Quality Control).
  Ranks use the empirical distribution, not a normal curve, because commodity
  price changes have fat tails (Mandelbrot 1963).
- Momentum alone can say "lock in" at the top of a spike. Prices are hard to
  forecast (Alquist, Kilian & Vigfusson 2013; Meese & Rogoff 1983), spikes tend to
  be shorter than slumps (Cashin, McDermott & Scott 2002; Deaton & Laroque 1992),
  and firms gain little from timing hedges on a market view (Brown, Crabb &
  Haushalter 2006). So the advice leans on risk-sharing tools (index-linked
  pricing with caps, short terms, layered cover; FAR 16.203; Martinez-de-Albeniz &
  Simchi-Levi 2005) more when the price is already high or expected to ease.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
LONG = HERE / "data" / "long"
DEFLATOR = "CPIAUCSL"            # CPI-U, all items (BLS), to put levels in today's dollars
MIN_MONTHS = 120                 # need 10+ years for a level percentile

# Move ranks (percent of past moves of the same length that were smaller)
ALERT_PCT, WATCH_PCT, OPP_PCT = 90.0, 75.0, 10.0
# Materiality floors: a statistically unusual move still has to matter in money
MIN_MOVE = {"m3": 1.0, "m12": 2.0}
# Level and outlook bands
HIGH_LEVEL, LOW_LEVEL = 80.0, 20.0
OUTLOOK_BAND = 5.0               # % change that counts as "expected to ease / rise"

# EIA Short-Term Energy Outlook series matched to tracked series
STEO_MAP = {"DCOILWTICO": "WTI", "MHHNGSP": "HH", "GASDESW": "DIESEL",
            "DJFUELUSGULF": "JET", "WPU0543": "ELEC_IND"}


def load_long(sid):
    p = LONG / f"{sid}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    s = pd.Series(pd.to_numeric(df["value"], errors="coerce").values,
                  index=pd.PeriodIndex(df["date"].str[:7], freq="M"))
    return s.sort_index().interpolate(limit_area="inside").dropna()


def rank_pct(hist, x):
    """Share of values in hist that are <= x, in percent (weak percentile rank)."""
    h = np.asarray(hist, dtype=float)
    return float((h <= x).mean() * 100)


def moves(s, k, direction):
    """All k-month % changes (cost terms) in the series."""
    ch = (s / s.shift(k) - 1).dropna() * 100 * direction
    return ch


def steo_outlook(sid, steo):
    """Average price EIA expects over the next 12 months vs its current-period value, %."""
    key = STEO_MAP.get(sid)
    if not steo or key not in steo.get("series", {}):
        return None
    vals = steo["series"][key]["values"]
    periods = sorted(vals)
    cur = steo["current"]
    ahead = [p for p in periods if p > cur]
    n = 4 if steo["freq"] == "Q" else 12
    ahead = ahead[:n]
    if cur not in vals or len(ahead) < n:
        return None
    avg = sum(vals[p] for p in ahead) / n
    return dict(pct=(avg / vals[cur] - 1) * 100, current=vals[cur], avg_next12=avg,
                key=key, name=steo["series"][key]["name"], release=steo["release_label"])


def assess(sid, group, direction, cost_m3, cost_m12, backtest_chosen, f6_cost, steo, cpi):
    """Return the context dict for one series."""
    s = load_long(sid)
    out = dict(window_start=None, p3=None, p12=None, level_pct=None, level_basis=None,
               outlook=None, outlook_source=None, steo=None)
    if s is not None and len(s) > 24:
        out["window_start"] = str(s.index[0])
        m3, m12 = moves(s, 3, direction), moves(s, 12, direction)
        if cost_m3 is not None and len(m3) >= 60:
            out["p3"] = rank_pct(m3.values, cost_m3)
        if cost_m12 is not None and len(m12) >= 60:
            out["p12"] = rank_pct(m12.values, cost_m12)
        if group != "Labor" and len(s) >= MIN_MONTHS:
            if group == "Currency" or cpi is None:
                lv = s.copy()
                out["level_basis"] = "nominal"
            else:
                c = cpi.reindex(s.index)
                lv = (s / c * cpi.iloc[-1]).dropna()
                out["level_basis"] = "real"
            lv = lv * direction           # cost terms: for X-per-USD, a weak dollar ranks high
            out["level_pct"] = rank_pct(lv.values, lv.iloc[-1])

    st = steo_outlook(sid, steo)
    if st is not None:
        out["steo"] = st
        out["outlook"], out["outlook_source"] = st["pct"] * direction, "EIA"
    elif backtest_chosen == "ets":
        out["outlook"], out["outlook_source"] = f6_cost, "model"

    out["signal"] = signal(cost_m3, cost_m12, out["p3"], out["p12"])
    out["stance"], out["action"] = recommend(group, out["signal"], out["level_pct"], out["outlook"])
    out["reasons"] = reasons(group, cost_m3, cost_m12, out, backtest_chosen)
    return out


def signal(c3, c12, p3, p12):
    def hot(c, p, key, cut):
        return c is not None and p is not None and c >= MIN_MOVE[key] and p >= cut
    if hot(c3, p3, "m3", ALERT_PCT) or hot(c12, p12, "m12", ALERT_PCT):
        return "Alert"
    if c3 is not None and p3 is not None and c3 <= -MIN_MOVE["m3"] and p3 <= OPP_PCT:
        return "Opportunity"
    if hot(c3, p3, "m3", WATCH_PCT) or hot(c12, p12, "m12", WATCH_PCT):
        return "Watch"
    return "Stable"


ACTIONS = {
    "rise_high_easing": "Don't lock in long fixed prices at this level. Keep terms short or use index-linked pricing with a cap. If you fix part of the volume, keep it small and compare the quote with the outlook, not today's price.",
    "rise_high": "The price is already high for this series and hard to forecast. Cover upcoming needs in stages, a share now and more later, instead of all at once. Prefer index-linked pricing with a cap over long fixed terms.",
    "rise_easing": "Costs are rising, but the outlook expects them to ease. Keep terms short or index-linked and cover only a modest share at fixed prices.",
    "rise": "Costs are rising from a normal level, with no sign of easing. Securing more of the next 6 to 12 months is reasonable, in stages. Check escalation clauses and expect supplier increase notices.",
    "rise_labor": "Wages are rising unusually fast for this sector. Expect supplier labor-rate increases and budget for them. Tie labor escalators to a published BLS index with a cap. Wages rarely fall back, so waiting is unlikely to help.",
    "rise_fx": "A weaker dollar raises the cost of buying in this currency. Exchange rates can't be forecast reliably, so hedge committed foreign-currency spend with forwards, or agree USD pricing or currency-adjustment clauses, instead of waiting.",
    "fall_low": "Costs are falling and low after inflation compared with history. This is a good time to rebid and to fix a larger share, or a longer term, in stages.",
    "fall_high": "Costs are easing from a high level. Ask suppliers to pass decreases through. Avoid long fixed terms for now, because index-linked pricing captures further declines.",
    "fall": "Costs are easing. Ask suppliers to pass decreases through and rebid before renewal. Fixing part of the volume can secure the savings.",
    "fall_fx": "A stronger dollar lowers the cost of buying in this currency. Consider locking in part of known foreign-currency spend with forwards.",
    "stable": "No unusual move. Review at the normal contract cycle.",
}


def recommend(group, sig, level, outlook):
    high = level is not None and level >= HIGH_LEVEL
    low = level is not None and level <= LOW_LEVEL
    easing = outlook is not None and outlook <= -OUTLOOK_BAND
    if sig in ("Alert", "Watch"):
        if group == "Labor":
            k = "rise_labor"
        elif group == "Currency":
            k = "rise_fx"
        elif high and easing:
            k = "rise_high_easing"
        elif high:
            k = "rise_high"
        elif easing:
            k = "rise_easing"
        else:
            k = "rise"
    elif sig == "Opportunity":
        k = "fall_fx" if group == "Currency" else "fall_low" if low else "fall_high" if high else "fall"
    else:
        k = "stable"
    return k, ACTIONS[k]


def ordinal(p):
    p = int(p)  # floor, so "80th" never shows for a value below the 80 cut-off
    suf = "th" if 10 <= p % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")
    return f"{p}{suf}"


def reasons(group, c3, c12, ctx, chosen):
    r = []
    since = ctx["window_start"][:4] if ctx["window_start"] else None
    if ctx["p3"] is not None:
        r.append(f"3-month move {c3:+.1f}% (cost terms) is at the {ordinal(ctx['p3'])} percentile of 3-month moves since {since}.")
    if ctx["p12"] is not None:
        r.append(f"12-month move {c12:+.1f}% is at the {ordinal(ctx['p12'])} percentile of 12-month moves.")
    if ctx["level_pct"] is not None:
        basis = "after inflation" if ctx["level_basis"] == "real" else "in cost terms"
        r.append(f"Price level {basis} is at the {ordinal(ctx['level_pct'])} percentile of monthly levels since {since}.")
    if ctx["steo"]:
        st = ctx["steo"]
        r.append(f"EIA ({st['release']} outlook, {st['name']}): next-12-month average {st['pct']:+.0f}% vs the current quarter.")
    elif chosen == "ets":
        r.append(f"Backtested model expects {ctx['outlook']:+.1f}% cost change over 6 months.")
    elif group != "Labor":
        r.append("No forecast beat \"no change\" in backtests, so no direction is assumed.")
    return r


def load_steo(today=None):
    """The EIA outlook, or None if missing or more than 4 months old (stale advice is worse than none)."""
    p = HERE / "data" / "steo.json"
    if not p.exists():
        return None
    st = json.loads(p.read_text())
    today = pd.Period(today or pd.Timestamp.today(), freq="M")
    return st if (today - pd.Period(st["release"], freq="M")).n <= 4 else None
