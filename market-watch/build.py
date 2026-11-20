"""Read data/raw/*.csv, calculate changes and buying signals, write data/market.json
and embed it into index.html (one self-contained page)."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from series import SERIES, THRESHOLDS

HERE = Path(__file__).parent

def load(sid):
    rows = list(csv.reader(open(HERE / "data" / "raw" / f"{sid}.csv")))[1:]
    return [(d[:7], float(v)) for d, v in rows if v not in ("", ".")]

def pct(obs, months):
    if len(obs) <= months:
        return None
    return (obs[-1][1] / obs[-1 - months][1] - 1) * 100

def signal(group, cost3, cost12):
    a3, a12, w3, w12, opp3 = THRESHOLDS[group]
    if cost3 >= a3 or (cost12 is not None and cost12 >= a12):
        return "Alert"
    if cost3 <= opp3:   # a sharp recent drop beats an older 12-month rise
        return "Opportunity"
    if cost3 >= w3 or (cost12 is not None and cost12 >= w12):
        return "Watch"
    return "Stable"

ACTIONS = {
    "Alert": "Costs rising fast. Lock in pricing or extend contracts now, and expect supplier increase notices.",
    "Watch": "Costs trending up. Check contract escalation clauses and pull forward planned buys.",
    "Opportunity": "Costs easing. Ask suppliers to pass through decreases and rebid before the next contract renewal.",
    "Stable": "No action needed. Keep standard reorder schedule.",
}

out = []
for sid, name, group, unit, direction, note in SERIES:
    obs = load(sid)
    ch = {k: pct(obs, m) for k, m in (("m1", 1), ("m3", 3), ("m12", 12))}
    cost = {k: (v * direction if v is not None else None) for k, v in ch.items()}
    vals = [v for _, v in obs]
    lo, hi = min(vals), max(vals)
    sig = signal(group, cost["m3"], cost["m12"])
    out.append(dict(
        id=sid, name=name, group=group, unit=unit, direction=direction, note=note,
        latest_month=obs[-1][0], latest=obs[-1][1],
        change=ch, cost_change=cost,
        range_pct=(obs[-1][1] - lo) / (hi - lo) * 100 if hi > lo else 50,
        high=hi, low=lo, signal=sig, action=ACTIONS[sig],
        series=obs,
        source=f"https://fred.stlouisfed.org/series/{sid}",
    ))

payload = dict(built=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), series=out)
(HERE / "data" / "market.json").write_text(json.dumps(payload, indent=1))
html = (HERE / "template.html").read_text().replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":")))
(HERE / "index.html").write_text(html)

for s in out:
    c = s["change"]
    print(f"{s['name']:30s} {s['latest_month']} {s['latest']:>9.3f}  1m {c['m1']:+6.2f}%  3m {c['m3']:+6.2f}%  "
          f"12m {c['m12']:+6.2f}%  {s['signal']}")
