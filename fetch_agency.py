"""Download agency data (EIA, USDA AMS, Census trade, USAspending) into data/agency/.

Called by collect.py, which decides when each group is due and passes it in MW_GROUPS
(spot, steo, census, usa). Run by hand it fetches every group. Daily exchange rates come
from the Federal Reserve directly in collect.py.

Standard library only. Keys come from repository secrets:
  EIA_API_KEY, CENSUS_API_KEY, USDA_AMS_API_KEY.
A source with no key is skipped. Any item that fails keeps its previous values,
so one agency outage never blanks the page.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from agency import SPOT, EXTRAS, CENSUS_START, USA_START

DATA = Path(os.environ.get("MW_DATA_DIR") or Path(__file__).parent / "data")
OUT = DATA / "agency"
GROUPS = set(filter(None, os.environ.get("MW_GROUPS", "spot,steo,census,usa").split(",")))
OUT.mkdir(parents=True, exist_ok=True)
KEY = {k: os.environ.get(k, "").strip() for k in ("EIA_API_KEY", "CENSUS_API_KEY", "USDA_AMS_API_KEY")}
UA = {"User-Agent": "industry-market-watch/2.0 (static site data collector)"}
TODAY = date.today()
log, failed = [], []


def scrub(t):
    for k in KEY.values():
        if k:
            t = t.replace(k, "***")
    return " ".join(t.split())[:160]


def get(url, headers=None, data=None, timeout=60, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})}, data=data)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body, status = r.read().decode("utf-8", "replace"), r.status
            if status == 204 or not body.strip():
                raise ValueError(f"HTTP {status}, empty response (no data for this query)")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                raise ValueError(f"HTTP {status}, not JSON: {scrub(body)}")
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: {scrub(e.read().decode('utf-8', 'replace'))}"
            if e.code in (400, 401, 403, 404) or i == tries - 1:
                raise ValueError(msg) from None
        except ValueError:
            raise
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
for key, (name, unit, freq, src, spec, *_rest) in (SPOT.items() if "spot" in GROUPS else ()):
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

# EIA Short-Term Energy Outlook (monthly history + 18-24 month forecast), used for the
# outlook behind buying advice. All six series must arrive; otherwise the last good
# data/steo.json is kept (context.py ignores it once it is more than 4 months old).
STEO_IDS = {"WTI": ("WTIPUUS", "WTI spot", "$/bbl"), "BRENT": ("BREPUUS", "Brent spot", "$/bbl"),
            "HH": ("NGHHUUS", "Henry Hub spot", "$/MMBtu"), "DIESEL": ("DSRTUUS", "On-highway diesel, retail", "$/gal"),
            "JET": ("JKTCUUS", "Jet fuel", "$/gal"), "ELEC_IND": ("ESICUUS", "Electricity, industrial", "¢/kWh")}
if KEY["EIA_API_KEY"] and "steo" in GROUPS:
    try:
        cur = TODAY.strftime("%Y-%m")
        series = {}
        for k, (code, nm, unit) in STEO_IDS.items():
            q = [("api_key", KEY["EIA_API_KEY"]), ("frequency", "monthly"), ("data[0]", "value"),
                 ("facets[seriesId][]", code), ("start", f"{TODAY.year - 1}-01"),
                 ("sort[0][column]", "period"), ("sort[0][direction]", "asc"), ("length", "5000")]
            j = get("https://api.eia.gov/v2/steo/data/?" + urllib.parse.urlencode(q))
            vals = {r["period"][:7]: num(r["value"]) for r in j["response"]["data"] if num(r["value"]) is not None}
            if cur not in vals or sum(1 for p in vals if p > cur) < 12:
                raise ValueError(f"{code}: no current month or fewer than 12 forecast months")
            series[k] = {"name": nm, "unit": unit, "code": code, "values": vals}
        steo = {"release": cur, "release_label": f"latest, retrieved {TODAY.isoformat()}",
                "source": "U.S. Energy Information Administration, Short-Term Energy Outlook (API v2, route steo)",
                "url": "https://www.eia.gov/outlooks/steo/", "freq": "M", "current": cur, "series": series}
        (DATA / "steo.json").write_text(json.dumps(steo, indent=1))
        log.append(f"ok   STEO {len(series)} series, current {cur}")
    except Exception as e:
        failed.append("STEO")
        log.append(f"FAIL STEO kept previous data/steo.json: {scrub(str(e))}")

# Census imports by HS4 and country
census = load("census.json")
# Census releases monthly (about 5 weeks after month end) and a full pull takes ~10 minutes,
# so refresh weekly (Mondays) or when codes are missing.
want = {h for x in EXTRAS.values() for h, _ in x.get("hs", [])}
census_due = TODAY.weekday() == 0 or not want <= set(census) or os.environ.get("CENSUS_FORCE")
if "census" not in GROUPS:
    pass
elif KEY["CENSUS_API_KEY"] and not census_due:
    log.append("skip Census imports: refreshed weekly on Mondays")
elif KEY["CENSUS_API_KEY"]:
    codes = sorted(want if TODAY.weekday() == 0 or os.environ.get("CENSUS_FORCE") else want - set(census))
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
            if sum(f.startswith("HS") for f in failed) >= 3 and len(census) == 0:
                log.append("stop Census: first 3 codes failed, skipping the rest")
                break
        time.sleep(0.5)
    save("census.json", census)
else:
    log.append("skip Census imports: no CENSUS_API_KEY")

# USAspending contract obligations by NAICS (no key)
usa = load("usaspending.json")
naics = {n[0]: (n[2] if len(n) > 2 else [n[0]]) for x in EXTRAS.values() for n in x.get("naics", [])}
for code, parts in (sorted(naics.items()) if "usa" in GROUPS else ()):
    try:
        body = json.dumps({"group": "month", "filters": {
            "time_period": [{"start_date": USA_START, "end_date": TODAY.isoformat()}],
            "award_type_codes": ["A", "B", "C", "D"], "naics_codes": {"require": parts}}}).encode()
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
# record what kept old data, for check_refresh.py (skipped sources with no key are not counted)
STATUS = DATA / "refresh_status.json"
status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
status["agency"] = dict(checked=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
                        tried=sum(line.startswith(("ok", "FAIL")) for line in log), failed=sorted(failed))
STATUS.write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")
# Never stop the workflow here for an agency outage: old values are kept and the page shows their dates.
# check_refresh.py, the workflow's last step, fails the run afterwards if too many sources failed.
sys.exit(0)
