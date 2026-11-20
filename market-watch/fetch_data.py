"""Download the latest data for every tracked series from FRED into data/raw/.

Run by the GitHub Action every day. Uses only the Python standard library.
If a download fails, the previous file is kept so the dashboard never breaks.
"""
import csv
import io
import sys
import time
import urllib.request
from pathlib import Path

from series import SERIES, fred_url

RAW = Path(__file__).parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

failed = []
for sid, name, *_ in SERIES:
    try:
        req = urllib.request.Request(fred_url(sid), headers={"User-Agent": "procurement-market-watch"})
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 13 or rows[0][1] != sid:
            raise ValueError("unexpected response")
        (RAW / f"{sid}.csv").write_text(text)
        print(f"ok   {sid:10s} {name:30s} latest {rows[-1][0]} {rows[-1][1]}")
    except Exception as e:  # keep the old file
        failed.append(sid)
        print(f"FAIL {sid:10s} {name:30s} {e}", file=sys.stderr)
    time.sleep(1)

if len(failed) == len(SERIES):
    sys.exit("All downloads failed; leaving data unchanged.")
