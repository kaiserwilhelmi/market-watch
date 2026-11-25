"""Last step of a collector run: fail it (so GitHub emails the repo owner) when too much is failing.

collect.py keeps the previous values when a publisher call fails and records the result in
data/status.json. The pages show which series are late or not updating; this script turns a
publisher that has failed several calls in a row, or a large share of failed agency extras,
into a failed workflow run. The pages are still rebuilt and published first.
"""
import json
import sys

from paths import DATA

FAILS = 3          # consecutive failed calls to one publisher
AGENCY_MAX = 0.25  # more than 25% of the agency items tried in the last run kept old data

path = DATA / "status.json"
if not path.exists():
    sys.exit("data/status.json is missing; collect.py did not record its results")
status = json.loads(path.read_text())
problems = []
for src, s in sorted(status.get("sources", {}).items()):
    print(f"{src}: ok={s.get('ok')} fails={s.get('fails', 0)} checked={s.get('checked')} {s.get('error') or ''}")
    if s.get("fails", 0) >= FAILS:
        problems.append(f"{src} failed {s['fails']} calls in a row: {s.get('error')}")
rs = DATA / "refresh_status.json"
if rs.exists():
    a = json.loads(rs.read_text()).get("agency")
    if a and a.get("tried"):
        share = len(a["failed"]) / a["tried"]
        print(f"agency: {len(a['failed'])} of {a['tried']} not refreshed ({share:.0%}){': ' + ', '.join(a['failed']) if a['failed'] else ''}")
        if share > AGENCY_MAX:
            problems.append(f"agency: {len(a['failed'])} of {a['tried']} failed, above the {AGENCY_MAX:.0%} limit")
late = sorted(i for i, f in status.get("series", {}).items() if f["state"] == "late")
if late:
    print(f"late series ({len(late)}): {', '.join(late)}")
if problems:
    sys.exit("Collector problems. " + "; ".join(problems))
print("refresh check passed")
