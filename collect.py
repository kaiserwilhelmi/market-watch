"""Collector: pulls every series from its original publisher, only when a release is due.

Run every 15 minutes by .github/workflows/collect.yml. Each run:
  1. works out, from sources.py, which publishers have a release due (or late) right now;
  2. calls only those publishers, merges new and revised values into data/long and data/raw,
     and logs every new or revised value with the time it was first seen (data/vintage);
  3. writes data/status.json: for every series the period it covers, when the value was
     first seen, whether it is preliminary, and when the next release is expected; for every
     publisher the last call, its result and the next planned call.

A publisher that fails keeps its previous values and is marked failed; nothing is blanked.
Standard library only, except openpyxl for the World Bank workbook.

Usage:  python collect.py            normal run (calls what is due)
        python collect.py --all      call every publisher now (first run, or by hand)
        python collect.py --plan     print what would be called, call nothing
"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from series import SERIES
from sources import SOURCES, BY_SOURCE, EIA_MONTHLY, H10, PINK, BLS_CODE, EXTRA, lag_of, source_of, code_of

HERE = Path(__file__).parent
DATA = Path(os.environ.get("MW_DATA_DIR") or HERE / "data")
LONG, RAW, VINT, AGENCY = DATA / "long", DATA / "raw", DATA / "vintage", DATA / "agency"
STATUS = DATA / "status.json"
ET = ZoneInfo("America/New_York")
START_YEAR, RAW_START = 2004, "2018-01"
UA = {"User-Agent": "industry-market-watch/2.0 (static site data collector)"}
KEYS = {k: os.environ.get(k, "").strip() for k in ("BLS_API_KEY", "EIA_API_KEY", "CENSUS_API_KEY", "USDA_AMS_API_KEY")}
FAIL_AFTER = 3          # consecutive failed calls before a publisher is shown as failed
H10_URL = ("https://www.federalreserve.gov/datadownload/Output.aspx?rel=H10&series=60f32914ab61dfab590e0e470153e3ae"
           "&lastobs=&from=01/01/{y}&to=12/31/{y2}&filetype=csv&label=include&layout=seriescolumn")
PINK_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
PINK_FALLBACK = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
                 "CMO-Historical-Data-Monthly.xlsx")
BTS_URL = "https://data.bts.gov/resource/bw6n-ddqk.json?$limit=5000&$order=obs_date"

# Agency extras fetched by fetch_agency.py: group -> times of day (US Eastern) it is called on business days
GROUP_SLOTS = {"spot": [(9, 30), (12, 0), (15, 0), (18, 0)], "steo": [(13, 0)], "usa": [(7, 0)], "census": [(6, 0)]}


# ------------------------------------------------------------------ small helpers
def scrub(t):
    t = str(t)
    for k in KEYS.values():
        if k:
            t = t.replace(k, "***")
    return " ".join(t.split())[:200]


def http(url, data=None, headers=None, timeout=60, tries=3, binary=False):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            return body if binary else body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = ValueError(f"HTTP {e.code}: {scrub(e.read()[:300].decode('utf-8', 'replace'))}")
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:  # timeouts, resets
            last = e
        time.sleep(3 * (i + 1))
    raise last


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def month_end(p):
    y, m = int(p[:4]), int(p[5:7])
    return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def next_month(p):
    y, m = int(p[:4]), int(p[5:7])
    return f"{y + (m == 12):04d}-{m % 12 + 1:02d}"


def is_business_day(d):
    return d.weekday() < 5


# ------------------------------------------------------------------ release schedule
def window(sid, latest_period):
    """When the period after `latest_period` is expected: (period, earliest, latest) in US Eastern."""
    nxt = next_month(latest_period)
    end = month_end(nxt)
    lo, hi = lag_of(sid)
    src = SOURCES[source_of(sid)]
    h, m = src["hour"]
    earliest = datetime.combine(end + timedelta(days=lo), datetime.min.time(), ET).replace(hour=h, minute=m)
    latest = datetime.combine(end + timedelta(days=hi + src["grace"]), datetime.min.time(), ET).replace(hour=23, minute=59)
    return nxt, earliest, latest


def series_state(sid, latest_period, now):
    nxt, earliest, latest = window(sid, latest_period)
    state = "current" if now < earliest else "due" if now <= latest else "late"
    return state, nxt, earliest, latest


def release_slots(src, keyed):
    """Times of day a publisher is polled while one of its releases is due."""
    h, m = SOURCES[src]["hour"]
    first = h * 60 + m + 5
    cap = SOURCES[src].get("polls_keyed" if keyed else "polls", SOURCES[src]["polls"])
    mins = [first, first + 15, first + 30, first + 45] + [hh * 60 for hh in range(h + 2, 19)]
    if cap < len(mins):     # few calls allowed: keep the first two, then spread the rest over the day
        rest = mins[2:]
        pick = [rest[round(i * (len(rest) - 1) / max(cap - 3, 1))] for i in range(cap - 2)] if cap > 2 else []
        mins = sorted(set(mins[:2] + pick))
    return [(x // 60, x % 60) for x in mins]


def due_slot(slots, last_call, now):
    """The latest slot today that has passed and has not been served by a call yet, else None."""
    hit = None
    for h, m in slots:
        t = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if t <= now and (last_call is None or last_call < t):
            hit = t
    return hit


def next_slot(slots, now):
    """Next slot strictly after now, today or on the next business day."""
    for add in range(0, 8):
        d = (now + timedelta(days=add)).date()
        if not is_business_day(d):
            continue
        for h, m in slots:
            t = datetime.combine(d, datetime.min.time(), ET).replace(hour=h, minute=m)
            if t > now:
                return t
    return None


# ------------------------------------------------------------------ storage
def read_series(sid):
    """{period: value string} from data/long/<sid>.csv ('' = no value published for that month)."""
    p = LONG / f"{sid}.csv"
    if not p.exists():
        return {}
    return {r["date"][:7]: r["value"] for r in csv.DictReader(p.open())}


def write_series(sid, vals):
    rows = sorted(vals.items())
    while rows and rows[0][1] == "":
        rows.pop(0)
    LONG.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    (LONG / f"{sid}.csv").write_text("date,value\n" + "".join(f"{p}-01,{v}\n" for p, v in rows))
    if sid in SERIES:
        (RAW / f"{sid}.csv").write_text("date,value\n" + "".join(f"{p}-01,{v}\n" for p, v in rows if p >= RAW_START))


def same(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


def merge(sid, new, now, replace_all=False):
    """Merge fetched {period: value} into the stored series. Returns the periods that are new or revised.
    Every change is appended to data/vintage/<sid>.csv with the time it was first seen."""
    old = read_series(sid)
    seeded = (VINT / f"{sid}.csv").exists()
    out = dict(new) if replace_all else {**old, **new}
    changes = []
    for p, v in sorted(new.items()):
        if p not in old:
            changes.append((p, v, "new"))
        elif not same(old[p], v):
            changes.append((p, v, "revised"))
    if changes or not old:
        write_series(sid, out)
    VINT.mkdir(parents=True, exist_ok=True)
    f = VINT / f"{sid}.csv"
    if not seeded:
        # first run for this series: history was not watched, so only say what the data looked like today
        last = sorted(p for p, v in out.items() if v != "")[-6:]
        f.write_text("period,value,first_seen,kind\n" + "".join(f"{p},{out[p]},{iso(now)},seed\n" for p in last))
        return [c[0] for c in changes]
    if changes:
        with f.open("a") as fh:
            for p, v, kind in changes:
                fh.write(f"{p},{v},{iso(now)},{kind}\n")
    return [c[0] for c in changes]


def first_seen(sid, period):
    f = VINT / f"{sid}.csv"
    if not f.exists():
        return None, None
    hit = (None, None)
    for r in csv.DictReader(f.open()):
        if r["period"] == period and hit[0] is None:
            hit = (r["first_seen"], r["kind"])
    return hit


# ------------------------------------------------------------------ publishers
def parse_bls(payload):
    """BLS API v2 JSON -> ({id: {period: value}}, {id: set(preliminary periods)})."""
    j = json.loads(payload)
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError("BLS: " + scrub("; ".join(j.get("message", [])) or j.get("status")))
    vals, prelim = {}, {}
    for s in j["Results"]["series"]:
        sid = s["seriesID"]
        for o in s["data"]:
            if not re.fullmatch(r"M(0[1-9]|1[0-2])", o["period"]):
                continue                      # skip annual averages (M13)
            p = f"{o['year']}-{o['period'][1:]}"
            v = o["value"].strip()
            vals.setdefault(sid, {})[p] = "" if v in ("-", "") else v
            if any(f.get("code") == "P" for f in o.get("footnotes", [])):
                prelim.setdefault(sid, set()).add(p)
    return vals, prelim


def fetch_bls(ids, full):
    key = KEYS["BLS_API_KEY"]
    per_query, span = (50, 20) if key else (25, 10)
    this_year = datetime.now(ET).year
    if full:
        spans, y = [], START_YEAR
        while y <= this_year:
            spans.append((y, min(y + span - 1, this_year)))
            y += span
    else:
        spans = [(this_year - 1, this_year)]
    codes = {BLS_CODE.get(i, i): i for i in ids}
    vals, prelim = {i: {} for i in ids}, {i: set() for i in ids}
    batch = sorted(codes)
    for a, b in spans:
        for k in range(0, len(batch), per_query):
            body = {"seriesid": batch[k:k + per_query], "startyear": str(a), "endyear": str(b)}
            if key:
                body["registrationkey"] = key
            txt = http("https://api.bls.gov/publicAPI/v2/timeseries/data/", data=json.dumps(body).encode(),
                       headers={"Content-Type": "application/json"}, timeout=90)
            v, pr = parse_bls(txt)
            for code, d in v.items():
                vals[codes[code]].update(d)
            for code, d in pr.items():
                prelim[codes[code]] |= d
            time.sleep(0.5)
    missing = [i for i in ids if not vals[i]]
    if len(missing) > len(ids) // 2:
        raise ValueError(f"BLS returned no data for {len(missing)} of {len(ids)} series")
    return vals, prelim, missing


def fetch_eia(ids, full):
    key = KEYS["EIA_API_KEY"]
    if not key:
        raise ValueError("no EIA_API_KEY")
    out = {}
    this_month = datetime.now(ET).strftime("%Y-%m")
    for sid in ids:
        route, facet, value = EIA_MONTHLY[sid]
        start = f"{START_YEAR}-01" if full else f"{datetime.now(ET).year - 1}-01"
        q = [("api_key", key), ("frequency", "monthly"), ("data[0]", "value"), ("start", start),
             ("sort[0][column]", "period"), ("sort[0][direction]", "asc"), ("length", "5000"), (f"facets[{facet}][]", value)]
        j = json.loads(http(f"https://api.eia.gov/v2/{route}/data/?" + urllib.parse.urlencode(q)))
        rows = {r["period"][:7]: str(r["value"]) for r in j["response"]["data"] if r.get("value") not in (None, "")}
        rows.pop(this_month, None)            # a month still in progress is not a monthly average yet
        out[sid] = rows
        time.sleep(0.4)
    return out


def parse_h10(text):
    """Fed H.10 CSV -> {currency code: [(YYYY-MM-DD, float)]}."""
    rows = list(csv.reader(io.StringIO(text)))
    cur = next((r for r in rows if r and r[0].startswith("Currency")), None)
    start = next((i for i, r in enumerate(rows) if r and r[0].startswith("Time Period")), None)
    if cur is None or start is None:
        raise ValueError(f"H.10: not the expected CSV ({len(text)} characters): {scrub(text[:140])}")
    start += 1
    out = {c: [] for c in cur[1:]}
    for r in rows[start:]:
        if not r or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[0]):
            continue
        for c, v in zip(cur[1:], r[1:]):
            try:
                out[c].append((r[0], float(v)))
            except ValueError:
                pass                          # "ND": no data that day (holiday)
    return out


def monthly_mean(daily, upto):
    """Average of the daily values in each month before `upto` (YYYY-MM), 4 decimals."""
    acc = {}
    for d, v in daily:
        if d[:7] < upto:
            acc.setdefault(d[:7], []).append(v)
    return {p: f"{sum(v) / len(v):.4f}" for p, v in acc.items()}


def fetch_h10(ids, full):
    now = datetime.now(ET)
    y = START_YEAR if full else now.year - 1
    daily = parse_h10(http(H10_URL.format(y=y, y2=now.year), timeout=120, headers={"Accept": "text/csv,*/*"}))
    out, tail = {}, {}
    for sid in ids:
        d = daily.get(H10[sid], [])
        if len(d) < 20:
            raise ValueError(f"H.10: only {len(d)} daily values for {H10[sid]}")
        out[sid] = monthly_mean(d, now.strftime("%Y-%m"))
        tail[sid] = [[a, b] for a, b in d[-90:]]
    return out, tail


def parse_pink(blob):
    """World Bank monthly workbook -> {page id: {period: value}}."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    ws = next((wb[n] for n in wb.sheetnames if "monthly prices" in n.lower()), None)
    if ws is None:
        raise ValueError(f"Pink Sheet: no 'Monthly Prices' sheet in {wb.sheetnames}")
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    first = next(i for i, r in enumerate(rows) if r and isinstance(r[0], str) and re.fullmatch(r"\d{4}M\d{2}", r[0].strip()))
    names = {}
    for r in rows[:first]:                    # header block: the row that names the commodities
        for c, cell in enumerate(r):
            if isinstance(cell, str) and cell.strip():
                names.setdefault(c, []).append(cell.strip())
    out = {}
    for sid, (want, factor) in PINK.items():
        col = next((c for c, cells in names.items() if any(x.lower().lstrip("* ").startswith(want.lower()) for x in cells)), None)
        if col is None:
            raise ValueError(f"Pink Sheet: no column starting '{want}' among {sorted(x for c in names.values() for x in c)[:120]}")
        vals = {}
        for r in rows[first:]:
            if not (r and isinstance(r[0], str) and re.fullmatch(r"\d{4}M\d{2}", r[0].strip())):
                continue
            p = f"{r[0][:4]}-{r[0].strip()[5:7]}"
            v = r[col] if col < len(r) else None
            if p >= f"{START_YEAR}-01" and isinstance(v, (int, float)):
                vals[p] = f"{v * factor:.4f}".rstrip("0").rstrip(".")
        out[sid] = vals
    return out


def fetch_pink(ids, full):
    url = None
    try:
        page = http(PINK_PAGE, timeout=60)
        m = re.search(r'https://thedocs\.worldbank\.org/[^"\']+?CMO-Historical-Data-Monthly\.xlsx', page)
        url = m.group(0) if m else None
    except Exception:
        pass
    print(f"       Pink Sheet workbook: {url or PINK_FALLBACK + ' (link not found on the page, using the last known address)'}")
    blob = http(url or PINK_FALLBACK, timeout=120, binary=True)
    data = parse_pink(blob)
    return {i: data[i] for i in ids}


def parse_bts(text):
    """BTS Transportation Services Index rows -> {period: freight index value}."""
    rows = json.loads(text)
    if not rows:
        raise ValueError("BTS: empty response")
    col = next((c for c in ("tsi_freight", "freight_tsi", "tsifreight") if c in rows[-1]), None)
    if col is None:
        col = next((c for c in rows[-1] if "freight" in c.lower() and "tsi" in c.lower()), None)
    if col is None:
        raise ValueError("BTS: no freight TSI column in " + ", ".join(sorted(rows[-1]))[:160])
    out = {}
    for r in rows:
        d = str(r.get("obs_date", ""))[:7]
        if re.fullmatch(r"\d{4}-\d{2}", d) and d >= f"{START_YEAR}-01" and r.get(col) not in (None, ""):
            out[d] = str(r[col])
    return out


def fetch_bts(ids, full):
    return {ids[0]: parse_bts(http(BTS_URL, timeout=90))}


# ------------------------------------------------------------------ run
def load_status():
    if STATUS.exists():
        try:
            return json.loads(STATUS.read_text())
        except json.JSONDecodeError:
            pass
    return {"sources": {}, "series": {}, "groups": {}}


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


def plan(status, now, force=False):
    """Which publishers and agency groups to call in this run, with the reason."""
    calls, groups = {}, {}
    for src, ids in BY_SOURCE.items():
        st = status["sources"].get(src, {})
        last = parse_ts(st.get("checked"))
        missing = [i for i in ids if not (LONG / f"{i}.csv").exists()]
        if force or missing:
            calls[src] = dict(full=True, why="first download" if missing else "requested")
            continue
        states = [series_state(i, max(p for p, v in read_series(i).items() if v != ""), now)[0] for i in ids]
        keyed = bool(SOURCES[src]["key"] and KEYS.get(SOURCES[src]["key"]))
        if SOURCES[src]["key_required"] and not keyed:
            continue
        if any(s in ("due", "late") for s in states) and is_business_day(now.date()):
            if due_slot(release_slots(src, keyed), last, now):
                calls[src] = dict(full=False, why="release due")
                continue
        # Sunday morning: re-pull the full history to pick up revisions older than the usual window
        if now.weekday() == 6 and due_slot([(6, 0)], last, now):
            calls[src] = dict(full=True, why="weekly full refresh")
        elif src == "FRB" and is_business_day(now.date()) and due_slot([(17, 0)], last, now):
            calls[src] = dict(full=False, why="daily rates")
    only = set(filter(None, os.environ.get("MW_ONLY", "").split(",")))     # testing: limit a run to named publishers
    if only:
        calls = {k: dict(full=True, why="test run") for k in BY_SOURCE if k in only}
        return calls, {g: True for g in GROUP_SLOTS if g in only}
    for g, slots in GROUP_SLOTS.items():
        last = parse_ts(status["groups"].get(g, {}).get("checked"))
        day_ok = now.weekday() == 0 if g == "census" else is_business_day(now.date())
        if force or (day_ok and due_slot(slots, last, now)) or not status["groups"].get(g):
            groups[g] = True
    return calls, groups


def main():
    force, dry = "--all" in sys.argv, "--plan" in sys.argv
    now = datetime.now(ET)
    status = load_status()
    for k in ("sources", "series", "groups"):
        status.setdefault(k, {})
    calls, groups = plan(status, now, force)
    print(f"collector run {iso(now)} ({now:%a %H:%M} Eastern)")
    print("  keys: " + ", ".join(f"{s['key']} {'set' if KEYS.get(s['key']) else 'not set'}" for s in SOURCES.values() if s["key"]))
    for src, c in calls.items():
        print(f"  call {src:4s} {'full history' if c['full'] else 'recent'}: {c['why']}")
    for g in groups:
        print(f"  call agency group {g}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"calls={len(calls) + len(groups)}\n")
    if dry:
        return
    changed = {"monthly": [], "agency": False, "called": bool(calls or groups)}
    prelim_all = {}
    fetchers = {"BLS": fetch_bls, "EIA": fetch_eia, "FRB": fetch_h10, "WB": fetch_pink, "BTS": fetch_bts}

    for src, c in calls.items():
        ids = BY_SOURCE[src]
        st = status["sources"].setdefault(src, {})
        st["checked"] = iso(now)
        try:
            res = fetchers[src](ids, c["full"])
            tail, missing = None, []
            if src == "BLS":
                vals, prelim_all, missing = res
            elif src == "FRB":
                vals, tail = res
            else:
                vals = res
            for sid in ids:
                if not vals.get(sid):
                    continue
                if len(vals[sid]) < (24 if c["full"] else 1):
                    raise ValueError(f"{sid}: only {len(vals[sid])} values")
                if merge(sid, vals[sid], now):
                    changed["monthly"].append(sid)
            if tail is not None:
                AGENCY.mkdir(parents=True, exist_ok=True)
                old = (AGENCY / "fx.json").read_text() if (AGENCY / "fx.json").exists() else ""
                new = json.dumps(tail, indent=0, sort_keys=True)
                if new != old:
                    (AGENCY / "fx.json").write_text(new)
                    changed["agency"] = True
            st.update(ok=True, error=None, fails=0, last_ok=iso(now), missing=sorted(missing))
            if src == "BLS":
                st["preliminary"] = {i: sorted(p)[-6:] for i, p in prelim_all.items() if p}
            print(f"ok   {src}: {len(ids) - len(missing)} series" + (f", no data for {', '.join(missing)}" if missing else ""))
            for sid in ids:
                v = sorted(vals.get(sid, {}).items())
                if v:
                    print(f"       {sid:18s} {len(v):4d} months  {v[0][0]} {v[0][1]:>10s}  ..  {v[-1][0]} {v[-1][1]:>10s}")
        except Exception as e:
            st.update(ok=False, error=scrub(e) or type(e).__name__, fails=st.get("fails", 0) + 1)
            print(f"FAIL {src}: {type(e).__name__} {scrub(e)}", file=sys.stderr)

    if groups:
        env = {**os.environ, "MW_GROUPS": ",".join(groups), "MW_DATA_DIR": str(DATA)}
        if "census" in groups:
            env["CENSUS_FORCE"] = "1"
        before = {p.name: p.read_bytes() for p in AGENCY.glob("*.json")} if AGENCY.exists() else {}
        steo_before = (DATA / "steo.json").read_bytes() if (DATA / "steo.json").exists() else b""
        r = subprocess.run([sys.executable, str(HERE / "fetch_agency.py")], env=env, capture_output=True, text=True)
        print(r.stdout[-6000:])
        if r.returncode:
            print(scrub(r.stderr[-400:]), file=sys.stderr)
        after = {p.name: p.read_bytes() for p in AGENCY.glob("*.json")} if AGENCY.exists() else {}
        if after != before or ((DATA / "steo.json").exists() and (DATA / "steo.json").read_bytes() != steo_before):
            changed["agency"] = True
        rs = DATA / "refresh_status.json"
        ag = json.loads(rs.read_text()).get("agency", {}) if rs.exists() else {}
        for g in groups:
            status["groups"][g] = dict(checked=iso(now), ok=r.returncode == 0,
                                       failed=[f for f in ag.get("failed", [])] if r.returncode == 0 else ["run failed"])

    write_status(status, now)
    (DATA / "changed.json").write_text(json.dumps(changed))
    print(f"changed: {len(changed['monthly'])} monthly series, agency {changed['agency']}")


def write_status(status, now):
    """Per-series and per-publisher freshness, for the pages and for check_refresh.py."""
    series = {}
    for src, ids in BY_SOURCE.items():
        st = status["sources"].setdefault(src, {})
        keyed = bool(SOURCES[src]["key"] and KEYS.get(SOURCES[src]["key"]))
        any_due, soonest = False, None
        for sid in ids:
            vals = {p: v for p, v in read_series(sid).items() if v != ""}
            if not vals:
                continue
            period = max(vals)
            state, nxt, earliest, latest = series_state(sid, period, now)
            seen, kind = first_seen(sid, period)
            if st.get("fails", 0) >= FAIL_AFTER:
                state = "failed"
            any_due |= state in ("due", "late")
            soonest = earliest if soonest is None or earliest < soonest else soonest
            if sid in EXTRA:
                continue
            series[sid] = dict(src=src, code=code_of(sid), period=period, value=vals[period],
                               first_seen=seen if kind != "seed" else None, tracked_since=seen if kind == "seed" else None,
                               preliminary=period in st.get("preliminary", {}).get(sid, []),
                               state=state, next_period=nxt, next_from=iso(earliest), next_by=iso(latest))
        if any_due:
            nx = next_slot(release_slots(src, keyed), now)
        else:
            nx = soonest
        st.update(name=SOURCES[src]["name"], api=SOURCES[src]["api"], url=SOURCES[src]["url"], rights=SOURCES[src]["rights"],
                  keyed=keyed, next_check=iso(nx) if nx else None, series=len([i for i in ids if i not in EXTRA]))
        st.setdefault("ok", None)
    status["series"] = series
    status["run"] = iso(now)
    status["schema"] = 1
    DATA.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
