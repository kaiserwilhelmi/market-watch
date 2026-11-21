"""Download the latest data for every tracked series from FRED into data/raw/.

Uses only the Python standard library.
- With a FRED_API_KEY (GitHub secret) it uses the official FRED API (recommended;
  the public CSV endpoint often times out from cloud runners).
- Otherwise it falls back to FRED's public CSV download.
Daily and weekly series are averaged to monthly, and the current, incomplete
month is dropped. If a download fails, the previous file is kept.

History from January 2004 goes to data/long/ (used to rank moves and price levels,
see context.py); data/raw/ keeps January 2018 on for forecasts and charts. CPI-U
(CPIAUCSL) is fetched to data/long/ only, to put price levels in today's dollars.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from series import SERIES, NON_MONTHLY, fred_url

RAW = Path(__file__).parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
API_KEY = os.environ.get("FRED_API_KEY", "").strip()
START = "2004-01-01"
RAW_START = "2018-01-01"
LONG = Path(__file__).parent / "data" / "long"
LONG.mkdir(parents=True, exist_ok=True)
EXTRA = {"CPIAUCSL": ("CPI-U, all items (deflator)",)}
HEADERS = {"User-Agent": "industry-market-watch/1.0 (+https://github.com/)", "Accept": "text/csv,application/json"}


def get(url, timeout=40):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def via_api(sid):
    params = {"series_id": sid, "api_key": API_KEY, "file_type": "json", "observation_start": START}
    if sid.startswith(NON_MONTHLY):
        params.update(frequency="m", aggregation_method="avg")
    data = json.loads(get("https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)))
    return [(o["date"], "" if o["value"] == "." else o["value"]) for o in data["observations"]]


def via_csv(sid):
    rows = list(csv.reader(io.StringIO(get(fred_url(sid, START)))))[1:]
    return [(d, "" if v == "." else v) for d, v in rows]


print("Source:", "FRED API" if API_KEY else "FRED CSV download (no FRED_API_KEY set)")
this_month = date.today().strftime("%Y-%m")
failed = []
for sid, (name, *_rest) in {**SERIES, **EXTRA}.items():
    try:
        rows = via_api(sid) if API_KEY else via_csv(sid)
        if sid.startswith(NON_MONTHLY) and rows and rows[-1][0][:7] == this_month:
            rows = rows[:-1]                       # partial month
        if len(rows) < 24:
            raise ValueError(f"only {len(rows)} rows")
        (LONG / f"{sid}.csv").write_text("date,value\n" + "".join(f"{d},{v}\n" for d, v in rows))
        if sid in SERIES:
            (RAW / f"{sid}.csv").write_text("date,value\n" + "".join(f"{d},{v}\n" for d, v in rows if d >= RAW_START))
        print(f"ok   {sid:18s} {name:34s} latest {rows[-1][0]} {rows[-1][1]}")
    except Exception as e:  # keep the old file
        failed.append(sid)
        print(f"FAIL {sid:18s} {name:34s} {e}", file=sys.stderr)
    time.sleep(0.6)

if len(failed) >= len(SERIES):
    sys.exit("All downloads failed; leaving data unchanged. Add FRED_API_KEY as a repository secret.")
print(f"{len(SERIES) + len(EXTRA) - len(failed)} of {len(SERIES) + len(EXTRA)} series updated")
