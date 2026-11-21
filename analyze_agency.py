"""Summarise agency data for the pages. Writes data/agency_analytics.json.

- Spot prices: latest value and date, change over 4 weeks and 52 weeks
  (1 and 12 months for monthly series), and latest vs the previous calendar
  month's average, which is what the monthly FRED series will show next.
- Census imports: trailing-12-month import value by country, share of the total,
  year-over-year change, and the Herfindahl-Hirschman Index (HHI, sum of squared
  % shares, 0-10,000). The page labels it with the U.S. DOJ/FTC 2023 Merger
  Guidelines cut-offs (above 1,800 = highly concentrated), used here only as a
  yardstick for how dependent US imports are on a few supplier countries.
- USAspending: monthly contract obligations; trailing 12 complete months vs the
  12 before, leaving out the most recent USA_LAG_MONTHS months that are still
  being reported.
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from agency import AGENCY_PUB, SPOT, FX_DAILY, EXTRAS, HUB_SPOT, TOP_N, CONC_SHARE, USA_LAG_MONTHS

HERE = Path(__file__).parent
IN = HERE / "data" / "agency"
COUNTRY = re.compile(r"^[1-7]\d{3}$")     # Census country codes; groupings use 0xxx or nXXX


def load(name):
    p = IN / name
    return json.loads(p.read_text()) if p.exists() else {}


def asof(s, when):
    """Last value on or before `when`."""
    s = s[s.index <= when]
    return (s.index[-1], float(s.iloc[-1])) if len(s) else (None, None)


def pct(a, b):
    return None if a is None or b in (None, 0) else (a / b - 1) * 100


def daily_summary(rows):
    s = pd.Series({pd.Timestamp(d): v for d, v in rows}).sort_index()
    last_d, last_v = s.index[-1], float(s.iloc[-1])
    d4, v4 = asof(s, last_d - timedelta(days=28))
    d52, v52 = asof(s, last_d - timedelta(days=364))
    prev = (last_d.to_period("M") - 1)
    pm = s[s.index.to_period("M") == prev]
    return dict(latest=last_v, latest_date=last_d.strftime("%Y-%m-%d"),
                chg_short=pct(last_v, v4), short_from=d4.strftime("%Y-%m-%d") if d4 is not None else None,
                chg_year=pct(last_v, v52), year_from=d52.strftime("%Y-%m-%d") if d52 is not None else None,
                prev_month=str(prev), prev_month_avg=float(pm.mean()) if len(pm) else None,
                vs_prev_month=pct(last_v, float(pm.mean())) if len(pm) else None,
                series=[[d.strftime("%Y-%m-%d"), float(v)] for d, v in s[s.index > last_d - timedelta(days=182)].items()])


def monthly_summary(rows):
    s = pd.Series({pd.Period(d[:7], "M"): v for d, v in rows}).sort_index()
    last = s.index[-1]
    get = lambda p: float(s[p]) if p in s.index else None
    v = float(s.iloc[-1])
    return dict(latest=v, latest_date=str(last), chg_short=pct(v, get(last - 1)), short_from=str(last - 1),
                chg_year=pct(v, get(last - 12)), year_from=str(last - 12),
                prev_month=None, prev_month_avg=None, vs_prev_month=None,
                series=[[str(p), float(x)] for p, x in s[s.index > last - 24].items()])


def spot_all():
    raw, out = load("spot.json"), {}
    for key, (name, unit, freq, src, spec, fred, page) in SPOT.items():
        if not raw.get(key):
            continue
        summ = monthly_summary(raw[key]) if freq == "monthly" else daily_summary(raw[key])
        out[key] = dict(key=key, name=name, unit=unit, freq=freq, fred=fred, source=page,
                        publisher=AGENCY_PUB[src][0], publisher_url=AGENCY_PUB[src][1], **summ)
    return out


def fx_all():
    raw, out = load("fx.json"), {}
    for sid in FX_DAILY:
        if raw.get(sid):
            d = daily_summary(raw[sid])
            out[sid] = {k: d[k] for k in ("latest", "latest_date", "prev_month", "prev_month_avg", "vs_prev_month")}
    return out


def census_all():
    raw, out = load("census.json"), {}
    for hs, rows in raw.items():
        df = pd.DataFrame(rows, columns=["month", "code", "name", "value"]).dropna(subset=["value"])
        tot = df[df.code == "-"].groupby("month")["value"].sum().sort_index()
        if len(tot) < 24:
            continue
        last12, prev12 = list(tot.index[-12:]), list(tot.index[-24:-12])
        t12, p12 = float(tot[last12].sum()), float(tot[prev12].sum())
        cty = df[df.code.map(lambda c: bool(COUNTRY.match(str(c))))]
        cur = cty[cty.month.isin(last12)].groupby(["code", "name"])["value"].sum()
        old = cty[cty.month.isin(prev12)].groupby(["code", "name"])["value"].sum()
        shares = (cur / t12 * 100).sort_values(ascending=False)
        top = []
        for (code, name), sh in shares.head(TOP_N).items():
            o = float(old.get((code, name), 0.0))
            top.append(dict(code=code, name=name.title(), value=float(cur[(code, name)]), share=float(sh),
                            yoy=pct(float(cur[(code, name)]), o) if o > 0 else None))
        out[hs] = dict(hs=hs, first=last12[0], last=last12[-1], total=t12, total_prev=p12, yoy=pct(t12, p12),
                       hhi=float((shares ** 2).sum()), top=top, top_share=float(shares.iloc[0]) if len(shares) else None,
                       concentrated=bool(len(shares) and shares.iloc[0] > CONC_SHARE),
                       countries=int((cur > 0).sum()),
                       monthly=[[m, float(v)] for m, v in tot.iloc[-24:].items()])
    return out


def usa_all():
    raw, out = load("usaspending.json"), {}
    this_month = date.today().strftime("%Y-%m")
    for code, rows in raw.items():
        rows = [r for r in rows if r[0] < this_month]           # current month is partial
        if len(rows) < 24 + USA_LAG_MONTHS:
            continue
        done, prov = rows[:-USA_LAG_MONTHS], rows[-USA_LAG_MONTHS:]
        t12 = sum(v for _, v in done[-12:])
        p12 = sum(v for _, v in done[-24:-12])
        out[code] = dict(code=code, t12=t12, p12=p12, yoy=pct(t12, p12), through=done[-1][0],
                         window=[done[-12][0], done[-1][0]], provisional=[m for m, _ in prov],
                         monthly=[[m, v, m in {x for x, _ in prov}] for m, v in rows[-27:]])
    return out


def main():
    spot, fx, census, usa = spot_all(), fx_all(), census_all(), usa_all()
    inds = {}
    for slug, x in EXTRAS.items():
        inds[slug] = dict(
            spot=[k for k in x.get("spot", []) if k in spot],
            hs=[dict(code=h, label=l, **({"data": True} if h in census else {"data": False})) for h, l in x.get("hs", [])],
            naics=[dict(code=c, label=l, data=c in usa) for c, l in x.get("naics", [])])
    payload = dict(spot=spot, fx=fx, census=census, usaspending=usa, industries=inds, hub_spot=[k for k in HUB_SPOT if k in spot],
                   publishers={k: list(v) for k, v in AGENCY_PUB.items()})
    (HERE / "data" / "agency_analytics.json").write_text(json.dumps(payload, indent=1))
    print(f"agency analytics: {len(spot)} spot, {len(fx)} FX, {len(census)} HS codes, {len(usa)} NAICS")
    for k, s in spot.items():
        print(f"  {k:11s} {s['latest']:10.3f} {s['latest_date']}  short {s['chg_short'] if s['chg_short'] is None else round(s['chg_short'], 2)}")


if __name__ == "__main__":
    main()
