"""Last step of the daily run: fail it (so GitHub emails the repo owner) when too many downloads failed.

fetch_data.py and fetch_agency.py keep the old file when a download fails and list it in
data/refresh_status.json. The pages say how many series were not refreshed; this script turns
a large share of failures into a failed workflow run. The pages are still rebuilt and pushed first.
"""
import json
import sys
from pathlib import Path

FRED_MAX = 0.10    # more than 10% of the FRED series kept old data
AGENCY_MAX = 0.25  # more than 25% of the agency sources that were tried kept old data

path = Path(__file__).parent / "data" / "refresh_status.json"
if not path.exists():
    sys.exit("data/refresh_status.json is missing; the download steps did not record their results")
status = json.loads(path.read_text())
problems = []
for part, limit in (("fred", FRED_MAX), ("agency", AGENCY_MAX)):
    s = status.get(part)
    if not s or not s.get("tried"):
        continue
    failed = s["failed"]
    share = len(failed) / s["tried"]
    print(f"{part}: {len(failed)} of {s['tried']} not refreshed ({share:.0%}){': ' + ', '.join(failed) if failed else ''}")
    if share > limit:
        problems.append(f"{part}: {len(failed)} of {s['tried']} failed, above the {limit:.0%} limit")
if problems:
    sys.exit("Too many downloads failed. " + "; ".join(problems))
print("refresh check passed")
