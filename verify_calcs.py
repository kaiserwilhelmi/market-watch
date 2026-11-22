"""Independent check of data/analytics.json.

Recomputes the published numbers with separate code (plain Python where possible)
and reports any difference. Run after analyze.py:  python verify_calcs.py
"""
import csv
import json
import math
import statistics as st
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).parent
A = json.load(open(HERE / "data" / "analytics.json"))
sys.path.insert(0, str(HERE))
from series import SERIES, INDUSTRIES  # noqa: E402

bad = []
def check(cond, msg):
    if not cond:
        bad.append(msg)

def close(a, b, tol=1e-6):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol * max(1.0, abs(b))

def months_add(ym, k):
    y, m = map(int, ym.split("-"))
    t = y * 12 + (m - 1) + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"

def read(sid):
    rows = list(csv.DictReader(open(HERE / "data" / "raw" / f"{sid}.csv")))
    return [(r["date"][:7], float(r["value"]) if r["value"] not in ("", ".") else None) for r in rows]

def fill(obs):
    """Linear interpolation of interior gaps, plain Python."""
    vals = [v for _, v in obs]
    out = vals[:]
    for i, v in enumerate(vals):
        if v is None:
            j = i - 1
            while j >= 0 and vals[j] is None: j -= 1
            k = i + 1
            while k < len(vals) and vals[k] is None: k += 1
            if j >= 0 and k < len(vals):
                out[i] = vals[j] + (vals[k] - vals[j]) * (i - j) / (k - j)
    return [(d, v) for (d, _), v in zip(obs, out)]

n_checks = 0
for sid, (name, group, unit, direction, pub) in SERIES.items():
    s = A["series"][sid]
    obs = fill(read(sid))
    obs = [(d, v) for d, v in obs if v is not None]
    d = dict(obs)
    last_m, last_v = obs[-1]
    check(s["latest_month"] == last_m and close(s["latest"], last_v), f"{sid} latest")
    for key, k in (("m1", 1), ("m3", 3), ("m12", 12)):
        prev = d.get(months_add(last_m, -k))
        mine = None if prev is None else (last_v / prev - 1) * 100
        check(close(s["change"][key], mine), f"{sid} change {key}: {s['change'][key]} vs {mine}")
        cost = None if mine is None else mine * direction
        check(close(s["cost_change"][key], cost), f"{sid} cost {key}")
    vals = [v for _, v in read(sid) if v is not None]
    check(close(s["low"], min(vals)) and close(s["high"], max(vals)), f"{sid} range")
    # naive backtest MAPE, plain Python
    first = "2020-12"; ev = "2022-01"
    months = [m for m, _ in obs]
    for h in (1, 3, 6):
        errs = []
        for i, (m, v) in enumerate(obs):
            if m < first or i + h >= len(obs) or m < ev:
                continue
            errs.append(abs(obs[i + h][1] - v) / obs[i + h][1] * 100)
        mine = sum(errs) / len(errs)
        check(close(s["backtest"]["naive"][f"h{h}"], mine, 1e-6), f"{sid} naive MAPE h{h}: {s['backtest']['naive'][f'h{h}']} vs {mine}")
    # forecast sanity
    fc = s["forecast"]
    check(len(fc) == 6 and fc[0]["month"] == months_add(last_m, 1), f"{sid} forecast months")
    check(all(f["lo"] <= f["hi"] for f in fc), f"{sid} range order")
    if s["backtest"]["chosen"] == "naive":
        check(all(close(f["mid"], last_v) for f in fc), f"{sid} naive forecast not flat")
    check(close(s["forecast_6m_pct"], (fc[-1]["mid"] / last_v - 1) * 100), f"{sid} f6 pct")
    n_checks += 1

# ETS refit for a sample: point forecast and h=3 backtest MAPE with an independent loop
import numpy as np  # noqa: E402
from statsmodels.tsa.holtwinters import ExponentialSmoothing  # noqa: E402
def ets(logy):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.asarray(ExponentialSmoothing(logy, trend="add", damped_trend=True,
                                               initialization_method="estimated").fit().forecast(6))
for sid in ("CES3000000008", "PCU322211322211", "WPU101706", "PCU492110492110"):
    s = A["series"][sid]
    obs = [(m, v) for m, v in fill(read(sid)) if v is not None]
    y = np.log([v for _, v in obs])
    if s["backtest"]["chosen"] == "ets":
        f = np.exp(ets(y))
        check(all(close(a["mid"], b, 1e-6) for a, b in zip(s["forecast"], f)), f"{sid} ETS forecast reproduce")
    errs = []
    for i, (m, v) in enumerate(obs):
        if m < "2022-01" or i + 3 >= len(obs):
            continue
        f = math.exp(ets(y[:i + 1])[2])
        errs.append(abs(obs[i + 3][1] - f) / obs[i + 3][1] * 100)
    mine = sum(errs) / len(errs)
    check(close(s["backtest"]["ets"]["h3"], mine, 1e-6), f"{sid} ETS MAPE h3 {s['backtest']['ets']['h3']} vs {mine}")

# industry medians, correlations and lead/lag r values
def logdiff(sid):
    o = fill(read(sid))
    return {o[i][0]: math.log(o[i][1] / o[i - 1][1]) for i in range(1, len(o))
            if o[i][1] is not None and o[i - 1][1] is not None}
def yoy(sid):
    o = dict(fill(read(sid)))
    return {m: (v / o[months_add(m, -12)] - 1) * 100 for m, v in o.items()
            if v is not None and o.get(months_add(m, -12)) is not None and m >= "2019-01"}
def pearson(a, b):
    ma, mb = st.fmean(a), st.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))

for ind, (slug, name, blurb, ids) in zip(A["industries"], INDUSTRIES):
    S = A["series"]
    check(close(ind["pressure_3m"], st.median([S[i]["cost_change"]["m3"] for i in ids])), f"{slug} median 3m")
    check(close(ind["pressure_12m"], st.median([S[i]["cost_change"]["m12"] for i in ids])), f"{slug} median 12m")
    check(close(ind["pressure_f6"], st.median([S[i]["forecast_6m_cost"] for i in ids])), f"{slug} median f6")
    Y = {i: yoy(i) for i in ids}
    for a in range(len(ids)):
        for b in range(len(ids)):
            common = sorted(set(Y[ids[a]]) & set(Y[ids[b]]))
            r = round(pearson([Y[ids[a]][m] for m in common], [Y[ids[b]][m] for m in common]), 2)
            check(abs(ind["corr"][a][b] - r) <= 0.0100001, f"{slug} corr {ids[a]}~{ids[b]} {ind['corr'][a][b]} vs {r}")
    for ll in ind["leadlag"]:
        x, y = logdiff(ll["lead"]), logdiff(ll["follow"])
        pairs = [(x[months_add(m, -ll["lag"])], y[m]) for m in y if months_add(m, -ll["lag"]) in x]
        r = pearson([p[0] for p in pairs], [p[1] for p in pairs])
        check(abs(r - ll["r"]) < 1e-9 and len(pairs) == ll["n"], f"{slug} leadlag {ll['lead']}->{ll['follow']} {ll['r']} vs {r}")


# ---- signal context, recomputed in plain Python (no pandas, no context.py) ----
STEO = json.load(open(HERE / "data" / "steo.json"))
from datetime import date  # noqa: E402
_ry, _rm = map(int, STEO["release"][:7].split("-")) if "-" in STEO["release"] else (0, 0)
STEO_OK = (date.today().year * 12 + date.today().month) - (_ry * 12 + _rm) <= 4
STEO_MAP = {"DCOILWTICO": "WTI", "MHHNGSP": "HH", "GASDESW": "DIESEL", "DJFUELUSGULF": "JET", "WPU0543": "ELEC_IND"}
def read_long(sid):
    rows = list(csv.DictReader(open(HERE / "data" / "long" / f"{sid}.csv")))
    obs = fill([(r["date"][:7], float(r["value"]) if r["value"] not in ("", ".") else None) for r in rows])
    return [(m, v) for m, v in obs if v is not None]
def prank(xs, x):
    return 100.0 * sum(1 for v in xs if v <= x) / len(xs)
cpi = dict(read_long("CPIAUCSL"))
cpi_last = cpi[max(cpi)]
n_ctx = 0
for sid, (name, group, unit, direction, pub) in SERIES.items():
    s = A["series"][sid]; c = s["context"]
    obs = read_long(sid); d = dict(obs); ms = [m for m, _ in obs]
    c3, c12 = s["cost_change"]["m3"], s["cost_change"]["m12"]
    def ch(k):
        return [(d[m] / d[months_add(m, -k)] - 1) * 100 * direction for m in ms if months_add(m, -k) in d]
    p3 = prank(ch(3), c3) if c3 is not None and len(ch(3)) >= 60 else None
    p12 = prank(ch(12), c12) if c12 is not None and len(ch(12)) >= 60 else None
    check(close(c["p3"], p3) and close(c["p12"], p12), f"{sid} move ranks {c['p3']},{c['p12']} vs {p3},{p12}")
    lvl = None
    if group != "Labor" and len(obs) >= 120:
        if group == "Currency":
            lv = [v * direction for _, v in obs]
        else:
            cpi_at = lambda m: cpi[m] if m in cpi else (cpi_last if m > max(cpi) else None)  # latest CPI carried forward
            lv = [v / cpi_at(m) * cpi_last * direction for m, v in obs if cpi_at(m)]
        lvl = prank(lv, lv[-1])
    check(close(c["level_pct"], lvl), f"{sid} level pct {c['level_pct']} vs {lvl}")
    out = None
    if sid in STEO_MAP and STEO_OK:
        vals = STEO["series"][STEO_MAP[sid]]["values"]; cur = STEO["current"]
        nxt = sorted(p for p in vals if p > cur)[:4 if STEO["freq"] == "Q" else 12]
        out = (sum(vals[p] for p in nxt) / len(nxt) / vals[cur] - 1) * 100 * direction
    elif s["backtest"]["chosen"] == "ets":
        out = s["forecast_6m_cost"]
    check(close(c["outlook"], out), f"{sid} outlook {c['outlook']} vs {out}")
    # signal rule
    up = lambda cc, pp, floor, cut: cc is not None and pp is not None and cc >= floor and pp >= cut
    if up(c3, p3, 1, 90) or up(c12, p12, 2, 90): sig = "Alert"
    elif c3 is not None and p3 is not None and c3 <= -1 and p3 <= 10: sig = "Opportunity"
    elif up(c3, p3, 1, 75) or up(c12, p12, 2, 75): sig = "Watch"
    else: sig = "Stable"
    check(s["signal"] == sig == c["signal"], f"{sid} signal {s['signal']} vs {sig}")
    high, low = lvl is not None and lvl >= 80, lvl is not None and lvl <= 20
    easing = out is not None and out <= -5
    if sig in ("Alert", "Watch"):
        st_ = ("rise_labor" if group == "Labor" else "rise_fx" if group == "Currency" else
               "rise_high_easing" if high and easing else "rise_high" if high else "rise_easing" if easing else "rise")
    elif sig == "Opportunity":
        st_ = "fall_fx" if group == "Currency" else "fall_low" if low else "fall_high" if high else "fall"
    else:
        st_ = "stable"
    check(c["stance"] == st_, f"{sid} stance {c['stance']} vs {st_}")
    n_ctx += 1
for ind in A["industries"]:
    S = A["series"]
    for key, sg in (("alerts", "Alert"), ("watches", "Watch"), ("opportunities", "Opportunity")):
        check(ind[key] == sum(1 for i in ind["series"] if S[i]["signal"] == sg), f"{ind['slug']} {key} count")
print(f"checked signal context for {n_ctx} series")

print(f"checked {n_checks} series, {len(A['industries'])} industries; problems: {len(bad)}")
for b in bad:
    print("  ", b)
sys.exit(1 if bad else 0)
