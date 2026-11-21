"""Independent check of data/agency_analytics.json against the raw agency files.

Plain Python (no pandas), written separately from analyze_agency.py.
Run after analyze_agency.py:  python verify_agency.py
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from agency import SPOT, USA_LAG_MONTHS, TOP_N  # noqa: E402

A = json.loads((HERE / "data" / "agency_analytics.json").read_text())
raw = {n: json.loads(p.read_text()) if (p := HERE / "data" / "agency" / f"{n}.json").exists() else {}
       for n in ("spot", "fx", "census", "usaspending")}
bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


def close(a, b, tol=1e-9):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol * max(1.0, abs(b))


def chg(a, b):
    return None if a is None or not b else (a / b - 1) * 100


def on_or_before(rows, day):
    best = None
    for d, v in rows:
        if d <= day:
            best = v
    return best


def ym_add(ym, k):
    y, m = map(int, ym.split("-"))
    t = y * 12 + m - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


# spot prices
for key, s in A["spot"].items():
    rows = sorted(raw["spot"][key])
    d, v = rows[-1]
    check(close(s["latest"], v) and s["latest_date"][:len(d)] == d[:len(s["latest_date"])], f"{key} latest")
    if SPOT[key][2] == "monthly":
        m = d[:7]
        dd = {r[0][:7]: r[1] for r in rows}
        check(close(s["chg_short"], chg(v, dd.get(ym_add(m, -1)))), f"{key} 1m")
        check(close(s["chg_year"], chg(v, dd.get(ym_add(m, -12)))), f"{key} 12m")
    else:
        last = date.fromisoformat(d)
        check(close(s["chg_short"], chg(v, on_or_before(rows, (last - timedelta(days=28)).isoformat()))), f"{key} 4w")
        check(close(s["chg_year"], chg(v, on_or_before(rows, (last - timedelta(days=364)).isoformat()))), f"{key} 52w")
        pm = ym_add(d[:7], -1)
        vals = [x for dd, x in rows if dd[:7] == pm]
        check(close(s["prev_month_avg"], sum(vals) / len(vals) if vals else None), f"{key} prev-month avg")

# Census: trailing-12 shares, YoY, HHI
for hs, c in A["census"].items():
    rows = raw["census"][hs]
    tot = {}
    for m, code, name, v in rows:
        if code == "-" and v is not None:
            tot[m] = tot.get(m, 0) + v
    months = sorted(tot)
    last12, prev12 = months[-12:], months[-24:-12]
    t12 = sum(tot[m] for m in last12)
    check(close(c["total"], t12, 1e-9), f"HS{hs} total")
    check(close(c["yoy"], chg(t12, sum(tot[m] for m in prev12))), f"HS{hs} yoy")
    by = {}
    for m, code, name, v in rows:
        if m in last12 and v is not None and len(code) == 4 and code[0] in "1234567" and code.isdigit():
            by[code] = by.get(code, 0) + v
    sh = sorted((v / t12 * 100 for v in by.values()), reverse=True)
    check(close(c["hhi"], sum(x * x for x in sh), 1e-9), f"HS{hs} HHI")
    check([round(t["share"], 9) for t in c["top"]] == [round(x, 9) for x in sh[:TOP_N]], f"HS{hs} top shares")
    check(c["concentrated"] == (sh[0] > 50.0), f"HS{hs} concentration flag")

# USAspending: trailing 12 complete months vs prior 12
this_month = date.today().strftime("%Y-%m")
for code, u in A["usaspending"].items():
    rows = [r for r in sorted(raw["usaspending"][code]) if r[0] < this_month]
    done = rows[:len(rows) - USA_LAG_MONTHS]
    t12 = sum(v for _, v in done[-12:])
    p12 = sum(v for _, v in done[-24:-12])
    check(close(u["t12"], t12) and close(u["p12"], p12), f"NAICS{code} sums")
    check(u["through"] == done[-1][0], f"NAICS{code} window end")
    check(close(u["yoy"], chg(t12, p12)), f"NAICS{code} yoy")

print(f"agency check: {len(A['spot'])} spot, {len(A['census'])} HS, {len(A['usaspending'])} NAICS; problems: {len(bad)}")
for b in bad:
    print("  ", b)
sys.exit(1 if bad else 0)
