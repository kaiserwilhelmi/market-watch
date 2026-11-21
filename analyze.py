"""Compute changes, buying signals, 6-month forecasts with backtests, lead/lag and
correlations for every series and industry. Writes data/analytics.json.

Methods (see README for references):
- Forecast model: damped additive-trend exponential smoothing on log levels
  (Gardner & McKenzie 1985; Hyndman & Athanasopoulos, FPP3 ch. 8), fitted with
  statsmodels. Benchmark: naive random walk (last value carried forward).
- Rolling-origin backtest (Tashman 2000): refit at every month from Dec 2020 on,
  forecast 1-6 months ahead, compare with what actually happened.
- The model used for the published forecast is whichever had lower mean absolute
  percentage error (MAPE) over 1-6 months ahead in the backtest.
- Ranges: empirical 10th-90th percentile of the chosen model's past log errors
  at each horizon (an 80% range; Williams & Goodman 1971). Coverage is tested
  out of sample: each range is built only from errors already known at that date.
- Lead/lag: correlation of monthly log changes, driver X at month t-k vs Y at t,
  k = 0..6. Correlation is not causation; |r| > 2/sqrt(n) is a rough 95% screen.
"""
import json
import warnings
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from series import SERIES, INDUSTRIES, PUB
import context as ctxmod

HERE = Path(__file__).parent
H = 6
FIRST_ORIGIN = pd.Period("2020-12", "M")     # >= 36 months of training data
EVAL_FROM = pd.Period("2022-01", "M")        # backtest scoring window starts here
COVER_FROM = pd.Period("2023-01", "M")       # out-of-sample range coverage test
MIN_ERRS = 24
STEO = ctxmod.load_steo()
CPI = ctxmod.load_long(ctxmod.DEFLATOR)


def load(sid):
    df = pd.read_csv(HERE / "data" / "raw" / f"{sid}.csv")
    s = pd.Series(pd.to_numeric(df["value"], errors="coerce").values,
                  index=pd.PeriodIndex(df["date"].str[:7], freq="M"), name=sid)
    return s.sort_index()


def pct_at(s, months):
    """% change from `months` before the latest observation. An isolated missing
    month (e.g. Oct 2025, when the federal shutdown halted BLS collection) is
    linearly interpolated from its neighbours."""
    s = s.interpolate(limit_area="inside")
    last = s.dropna().index[-1]
    prev = last - months
    if prev not in s.index or pd.isna(s[prev]):
        return None
    return float((s[last] / s[prev] - 1) * 100)


def ets_forecast(logy):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = ExponentialSmoothing(logy, trend="add", damped_trend=True,
                                 initialization_method="estimated").fit()
        return np.asarray(m.forecast(H))


def analyze_series(sid):
    raw = load(sid)
    s = raw.dropna()
    full = raw.loc[s.index[0]:s.index[-1]].interpolate(limit_area="inside")  # fills isolated gaps
    y = np.log(full.values.astype(float))
    idx = full.index
    n = len(y)

    # rolling-origin backtest
    errs = {"ets": {}, "naive": {}}          # origin_pos -> array of log errors (actual - forecast), len<=H
    fcs = {}
    for o in range(n):
        if idx[o] < FIRST_ORIGIN or o >= n - 1:
            continue
        f = ets_forecast(y[:o + 1])
        fcs[o] = f
        k = min(H, n - 1 - o)
        act = y[o + 1:o + 1 + k]
        errs["ets"][o] = act - f[:k]
        errs["naive"][o] = act - y[o]

    def mape(model, h, from_p=EVAL_FROM):
        e = [v[h - 1] for o, v in errs[model].items() if idx[o] >= from_p and len(v) >= h]
        return (float(np.mean(np.abs(1 - np.exp(-np.array(e)))) * 100), len(e)) if e else (None, 0)

    bt = {}
    for model in ("ets", "naive"):
        bt[model] = {f"h{h}": mape(model, h)[0] for h in (1, 3, 6)}
        bt[model]["avg"] = float(np.mean([mape(model, h)[0] for h in range(1, H + 1)]))
    bt["n_origins_h3"] = mape("ets", 3)[1]
    bt["n_origins_h6"] = mape("ets", 6)[1]
    chosen = "ets" if bt["ets"]["avg"] < bt["naive"]["avg"] else "naive"

    # out-of-sample coverage of the 80% range
    cover = {}
    for h in (3, 6):
        hits, tot = 0, 0
        for o, v in errs[chosen].items():
            if idx[o] < COVER_FROM or len(v) < h:
                continue
            past = [w[h - 1] for p, w in errs[chosen].items() if len(w) >= h and p + h <= o]
            if len(past) < MIN_ERRS:
                continue
            lo, hi = np.quantile(past, [0.1, 0.9])
            hits += int(lo <= v[h - 1] <= hi)
            tot += 1
        cover[f"h{h}"] = (hits / tot * 100) if tot else None
        cover[f"n{h}"] = tot
    bt["coverage80"] = cover
    bt["chosen"] = chosen

    # final forecast
    point = ets_forecast(y) if chosen == "ets" else np.repeat(y[-1], H)
    fc = []
    for h in range(1, H + 1):
        e = [w[h - 1] for w in errs[chosen].values() if len(w) >= h]
        q10, q90 = np.quantile(e, [0.1, 0.9])
        fc.append(dict(month=str(idx[-1] + h), mid=float(np.exp(point[h - 1])),
                       lo=float(np.exp(point[h - 1] + q10)), hi=float(np.exp(point[h - 1] + q90))))

    name, group, unit, direction, pub = SERIES[sid]
    ch = {k: pct_at(raw, m) for k, m in (("m1", 1), ("m3", 3), ("m12", 12))}
    cost = {k: (v * direction if v is not None else None) for k, v in ch.items()}
    vals = s.values
    last = float(vals[-1])
    lo, hi = float(vals.min()), float(vals.max())
    f6 = (fc[-1]["mid"] / last - 1) * 100
    cx = ctxmod.assess(sid, group, direction, cost["m3"], cost["m12"], chosen, f6 * direction,
                       STEO, CPI)
    sig = cx["signal"]
    return sid, dict(
        id=sid, name=name, group=group, unit=unit, direction=direction,
        publisher=PUB[pub][0], publisher_url=PUB[pub][1],
        source=f"https://fred.stlouisfed.org/series/{sid}",
        latest_month=str(s.index[-1]), latest=last,
        change=ch, cost_change=cost, signal=sig,
        low=lo, high=hi, range_pct=(last - lo) / (hi - lo) * 100 if hi > lo else 50.0,
        forecast=fc, forecast_6m_pct=f6, forecast_6m_cost=f6 * direction,
        backtest=bt, context=cx,
        gaps=[str(p) for p, v in raw.loc[s.index[0]:].items() if pd.isna(v)],
        series=[[str(p), (None if pd.isna(v) else float(v))] for p, v in raw.items()],
    )


def lead_lag(ids, logd):
    out = []
    for x in ids:
        for yid in ids:
            if x == yid:
                continue
            best = None
            r0 = None
            for k in range(0, 7):
                pair = pd.concat([logd[x].shift(k), logd[yid]], axis=1).dropna()
                if len(pair) < 36:
                    continue
                r = float(np.corrcoef(pair.iloc[:, 0], pair.iloc[:, 1])[0, 1])
                if k == 0:
                    r0 = r
                elif best is None or abs(r) > abs(best[1]):
                    best = (k, r, len(pair))
            if best is None or r0 is None:
                continue
            k, r, n = best
            if abs(r) > 2 / np.sqrt(n) and abs(r) > abs(r0):
                out.append(dict(lead=x, follow=yid, lag=k, r=r, r0=r0, n=n))
    out.sort(key=lambda d: -abs(d["r"]))
    # keep one direction per pair
    seen, res = set(), []
    for d in out:
        key = frozenset((d["lead"], d["follow"]))
        if key in seen:
            continue
        seen.add(key)
        res.append(d)
    return res[:6]


def main():
    with Pool() as pool:
        res = dict(pool.map(analyze_series, list(SERIES)))
    levels = pd.DataFrame({sid: load(sid) for sid in SERIES}).sort_index()
    levels = levels.interpolate(limit_area="inside")
    logd = np.log(levels).diff()
    yoy = (levels / levels.shift(12) - 1) * 100

    inds = []
    for slug, name, blurb, ids in INDUSTRIES:
        c3 = [res[i]["cost_change"]["m3"] for i in ids if res[i]["cost_change"]["m3"] is not None]
        c12 = [res[i]["cost_change"]["m12"] for i in ids if res[i]["cost_change"]["m12"] is not None]
        f6 = [res[i]["forecast_6m_cost"] for i in ids]
        sigs = [res[i]["signal"] for i in ids]
        sub = yoy.loc[pd.Period("2019-01", "M"):, ids]
        corr = sub.corr(min_periods=36).round(2)
        inds.append(dict(
            slug=slug, name=name, blurb=blurb, series=ids,
            pressure_3m=float(np.median(c3)), pressure_12m=float(np.median(c12)),
            pressure_f6=float(np.median(f6)),
            alerts=sigs.count("Alert"), watches=sigs.count("Watch"),
            opportunities=sigs.count("Opportunity"),
            top_driver=max(ids, key=lambda i: res[i]["cost_change"]["m12"] or -1e9),
            leadlag=lead_lag(ids, logd),
            corr=[[None if pd.isna(v) else float(v) for v in row] for row in corr.values],
        ))
    payload = dict(built=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                   series=res, industries=inds)
    (HERE / "data" / "analytics.json").write_text(json.dumps(payload, indent=1))
    for d in inds:
        print(f"{d['name']:32s} 3m {d['pressure_3m']:+6.2f}% 12m {d['pressure_12m']:+6.2f}% "
              f"f6 {d['pressure_f6']:+6.2f}% A{d['alerts']} W{d['watches']} O{d['opportunities']}")


if __name__ == "__main__":
    main()
