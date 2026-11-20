"""Download the latest data for every tracked series from FRED into data/raw/.

Run by the GitHub Action every day. Uses only the Python standard library.

- If a FRED_API_KEY is available (GitHub secret), uses the official FRED API,
  which is reliable from cloud servers.
- Otherwise falls back to FRED's public CSV download.
If a download fails, the previous file is kept so the dashboard never breaks.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from series import SERIES, fred_url

RAW = Path(__file__).parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
API_KEY = os.environ.get("FRED_API_KEY", "").strip()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "text/csv,application/json;q=0.9,*/*;q=0.8",
}

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")

def via_api(sid):
    params = {"series_id": sid, "api_key": API_KEY, "file_type": "json", "observation_start": "2021-01-01"}
    if sid.startswith(("DEX", "GAS")):           # daily/weekly -> monthly average
        params.update(frequency="m", aggregation_method="avg")
    data = json.loads(get("https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)))
    lines = [f"observation_date,{sid}"] + [f"{o['date']},{'' if o['value'] == '.' else o['value']}"
                                           for o in data["observations"]]
    return "\n".join(lines) + "\n"

def via_csv(sid):
    return get(fred_url(sid))

print("Source:", "FRED API" if API_KEY else "FRED CSV download (no FRED_API_KEY set)")
failed = []
for sid, name, *_ in SERIES:
    try:
        text = via_api(sid) if API_KEY else via_csv(sid)
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 13 or rows[0][1] != sid:
            raise ValueError("unexpected response")
        (RAW / f"{sid}.csv").write_text(text)
        print(f"ok   {sid:10s} {name:30s} latest {rows[-1][0]} {rows[-1][1]}")
    except Exception as e:  # keep the old file
        failed.append(sid)
        print(f"FAIL {sid:10s} {name:30s} {e}", file=sys.stderr)
    time.sleep(0.5)

if len(failed) == len(SERIES):
    sys.exit("All downloads failed; leaving data unchanged. "
             "Add a free FRED API key as the FRED_API_KEY repository secret (see README).")
