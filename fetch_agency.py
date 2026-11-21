"""Download agency data (EIA, USDA AMS, Census trade, USAspending, daily FX) into data/agency/.

Standard library only. Keys come from repository secrets:
  EIA_API_KEY, CENSUS_API_KEY, USDA_AMS_API_KEY, FRED_API_KEY (daily FX).
A source with no key is skipped. Any item that fails keeps its previous values,
so one agency outage never blanks the page.
"""
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from agency import SPOT, FX_DAILY, EXTRAS, CENSUS_START, USA_START

OUT = Path(__file__).parent / "data" / "agency"
OUT.mkdir(parents=True, exist_ok=True)
KEY = {k: os.environ.get(k, "").strip() for k in ("EIA_API_KEY", "CENSUS_API_KEY", "USDA_AMS_API_KEY", "FRED_API_KEY")}
UA = {"User-Agent": "industry-market-watch/1.0 (+https://github.com/)"}
TODAY = date.today()
log, failed = [], []


def get(url, headers=None, data=None, timeout=60, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})}, data=data)
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def load(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else {}


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=0, sort_keys=True))


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def mdy(d):
    return d.strftime("%m/%d/%Y")


def iso(s):
    m, d, y = s[:10].split("/")
    return f"{y}-{m}-{d}"


# ------------------------------------------------------------------ EIA
def eia(key, spec, freq):
    route, facet, value, col = spec
    start = (TODAY - timedelta(days=400)).isoformat() if freq != "monthly" else f"{TODAY.year - 4}-01"
    q = [("api_key", KEY["EIA_API_KEY"]), ("frequency", freq), ("data[0]", col), ("start", start),
         ("sort[0][column]", "period"), ("sort[0][direction]", "asc"), ("length", "5000"),
         (f"facets[{facet}][]", value)]
    if route.startswith("electricity"):
        q.append(("facets[stateid][]", "US"))
    j = get(f"https://api.eia.gov/v2/{route}/data/?" + urllib.parse.urlencode(q))
    rows = [(r["period"], num(r[col])) for r in j["response"]["data"]]
    return [[d, v] for d, v in rows if v is not None]


# ------------------------------------------------------------------ USDA AMS
def ams(src, spec):
    slug, section, pick = spec
    start = TODAY - timedelta(days=400)
    if src == "AMS-LMR":     # Livestock Mandatory Reporting DataMart, public
        url = (f"https://mpr.datamart.ams.usda.gov/services/v1.1/reports/{slug}/"
               f"{urllib.parse.quote(section)}?q=report_date={mdy(start)}:{mdy(TODAY)}")
        res = get(url)["results"]
        rows = [(iso(r["report_date"]), num(r.get(pick))) for r in res]
    else:                    # My Market News API, key as basic-auth user name
        auth = base64.b64encode(f"{KEY['USDA_AMS_API_KEY']}:".encode()).decode()
        url = (f"https://marsapi.ams.usda.gov/services/v1.2/reports/{slug}/"
               f"{urllib.parse.quote(section)}?q=report_begin_date={mdy(start)}:{mdy(TODAY)}")
        res = get(url, headers={"Authorization": "Basic " + auth})["results"]
        by_day = {}
        for r in res:
            if all(str(r.get(k, "")).strip().lower() == v.lower() for k, v in pick.items()):
                v = num(r.get("wtd_avg_price"))
                if v is None:
                    continue
                d = iso(r.get("report_end_date") or r["report_begin_date"])
                vol = num(r.get("volume")) or 0.0
                if d not in by_day or vol > by_day[d][1]:     # duplicate rows: keep the larger trade volume
                    by_day[d] = (v, vol)
        rows = [(d, v) for d, (v, _) in by_day.items()]
    rows = sorted({d: v for d, v in rows if v is not None}.items())
    return [[d, v] for d, v in rows]


# ------------------------------------------------------------------ run
spot = load("spot.json")
for key, (name, unit, freq, src, spec, *_rest) in SPOT.items():
    need = "EIA_API_KEY" if src == "EIA" else "USDA_AMS_API_KEY" if src == "AMS-MMN" else None
    if need and not KEY[need]:
        log.append(f"skip {key:11s} no {need}")
        continue
    try:
        rows = eia(key, spec, freq) if src == "EIA" else ams(src, spec)
        if len(rows) < 8:
            raise ValueError(f"only {len(rows)} rows")
        spot[key] = rows
        log.append(f"ok   {key:11s} {name:42s} {len(rows):4d} rows, latest {rows[-1][0]} {rows[-1][1]}")
    except Exception as e:
        failed.append(key)
        log.append(f"FAIL {key:11s} {name:42s} {e}")
    time.sleep(0.4)
save("spot.json", spot)

# Daily exchange rates (Federal Reserve H.10 via FRED)
fx = load("fx.json")
if KEY["FRED_API_KEY"]:
    for sid in FX_DAILY:
        try:
            q = {"series_id": sid, "api_key": KEY["FRED_API_KEY"], "file_type": "json",
                 "observation_start": (TODAY - timedelta(days=120)).isoformat()}
            j = get("https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(q))
            rows = [[o["date"], num(o["value"])] for o in j["observations"] if num(o["value"]) is not None]
            if len(rows) < 20:
                raise ValueError(f"only {len(rows)} rows")
            fx[sid] = rows
            log.append(f"ok   {sid:11s} daily FX {len(rows)} rows, latest {rows[-1][0]} {rows[-1][1]}")
        except Exception as e:
            failed.append(sid)
            log.append(f"FAIL {sid:11s} {e}")
        time.sleep(0.6)
    save("fx.json", fx)
else:
    log.append("skip daily FX: no FRED_API_KEY")

# Census imports by HS4 and country
census = load("census.json")
if KEY["CENSUS_API_KEY"]:
    codes = sorted({h for x in EXTRAS.values() for h, _ in x.get("hs", [])})
    for hs in codes:
        try:
            q = [("get", "CTY_CODE,CTY_NAME,GEN_VAL_MO"), ("I_COMMODITY", hs), ("COMM_LVL", "HS4"),
                 ("time", f"from {CENSUS_START}"), ("key", KEY["CENSUS_API_KEY"])]
            j = get("https://api.census.gov/data/timeseries/intltrade/imports/hs?" + urllib.parse.urlencode(q), timeout=120)
            hdr, body = j[0], j[1:]
            ix = {h: i for i, h in enumerate(hdr)}
            rows = sorted([r[ix["time"]], r[ix["CTY_CODE"]], r[ix["CTY_NAME"]], num(r[ix["GEN_VAL_MO"]])] for r in body)
            if not any(r[1] == "-" for r in rows):
                raise ValueError("no total row")
            census[hs] = rows
            last = max(r[0] for r in rows)
            log.append(f"ok   HS{hs:9s} {len(rows):5d} rows, latest month {last}")
        except Exception as e:
            failed.append("HS" + hs)
            log.append(f"FAIL HS{hs:9s} {e}")
        time.sleep(0.5)
    save("census.json", census)
else:
    log.append("skip Census imports: no CENSUS_API_KEY")

# USAspending contract obligations by NAICS (no key)
usa = load("usaspending.json")
for code in sorted({c for x in EXTRAS.values() for c, _ in x.get("naics", [])}):
    try:
        body = json.dumps({"group": "month", "filters": {
            "time_period": [{"start_date": USA_START, "end_date": TODAY.isoformat()}],
            "award_type_codes": ["A", "B", "C", "D"], "naics_codes": {"require": [code]}}}).encode()
        j = get("https://api.usaspending.gov/api/v2/search/spending_over_time/", data=body,
                headers={"Content-Type": "application/json"}, timeout=120)
        rows = []
        for r in j["results"]:
            fy, fm = int(r["time_period"]["fiscal_year"]), int(r["time_period"]["month"])
            cm = (fm + 8) % 12 + 1                       # fiscal month 1 = October
            cy = fy - 1 if fm <= 3 else fy
            ym = f"{cy:04d}-{cm:02d}"
            if ym <= TODAY.strftime("%Y-%m"):
                rows.append([ym, float(r["aggregated_amount"] or 0.0)])
        rows.sort()
        if len(rows) < 24:
            raise ValueError(f"only {len(rows)} months")
        usa[code] = rows
        log.append(f"ok   NAICS{code:7s} {len(rows)} months, latest {rows[-1][0]} ${rows[-1][1] / 1e6:,.0f}M")
    except Exception as e:
        failed.append("NAICS" + code)
        log.append(f"FAIL NAICS{code:7s} {e}")
    time.sleep(0.5)
save("usaspending.json", usa)

print("\n".join(log))
print(f"agency fetch done; {len(failed)} failed: {', '.join(failed) or 'none'}")
# Never fail the workflow for an agency outage: old values are kept and the page shows their dates.
sys.exit(0)
