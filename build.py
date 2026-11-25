"""Build the hub page and one page per industry from data/analytics.json.

Output: index.html (hub) and <slug>/index.html for each industry. Each page is a
single self-contained HTML file with its data embedded.
"""
import csv
import hashlib
import html
import os
import json
from pathlib import Path

from series import INDUSTRIES

HERE = Path(__file__).parent
from paths import DATA
A = json.loads((DATA / "analytics.json").read_text())
TEMPLATE = (HERE / "template.html").read_text()
AP = DATA / "agency_analytics.json"
G = json.loads(AP.read_text()) if AP.exists() else dict(spot={}, fx={}, census={}, usaspending={}, industries={}, hub_spot=[], publishers={})
SP = DATA / "status.json"
ST = json.loads(SP.read_text()) if SP.exists() else dict(sources={}, series={})
# series whose publisher failed on its last call keep their previous data (collect.py)
STALE = {i for i, f in ST["series"].items() if ST["sources"].get(f["src"], {}).get("ok") is False}
VERSION = hashlib.sha1((DATA / "analytics.json").read_bytes() + (AP.read_bytes() if AP.exists() else b"")).hexdigest()[:12]
SRC_KEYS = ("name", "api", "url", "rights", "checked", "ok", "next_check", "series")
SOURCES_OUT = {k: {f: v.get(f) for f in SRC_KEYS} for k, v in ST["sources"].items() if v.get("name")}


def refresh(ids):
    """Series among ids whose last download failed, so the page keeps the previous data (collect.py)."""
    bad = sorted(i for i in ids if i in STALE)
    return dict(failed=[A["series"][i]["name"] for i in bad], total=len(ids))


def latest_for(ids):
    """Newest daily/weekly value for monthly rows that have one (EIA spot or Fed daily FX)."""
    out = {}
    for k, s in G["spot"].items():
        if s.get("fred") in ids:
            out[s["fred"]] = {f: s[f] for f in ("latest", "latest_date", "prev_month", "prev_month_avg", "vs_prev_month", "freq", "publisher")}
    for sid, f in G["fx"].items():
        if sid in ids:
            out[sid] = {**f, "freq": "daily", "publisher": G["publishers"]["FRB"][0]}
    return out


def long_hist(sid):
    """2004+ monthly history from data/long (same values as data/raw from 2018 on),
    compact: first month + values; leading blanks trimmed, inside gaps kept as null."""
    rows = [(r["date"][:7], None if r["value"] in ("", ".") else float(r["value"]))
            for r in csv.DictReader((DATA / "long" / f"{sid}.csv").open())]
    while rows and rows[0][1] is None:
        rows.pop(0)
    vals = [v for _, v in rows if v is not None]
    lo, hi = min(vals), max(vals)
    lo_m = next(m for m, v in rows if v == lo)
    hi_m = next(m for m, v in rows if v == hi)
    last = vals[-1]
    return dict(start=rows[0][0], v=[v for _, v in rows], low=lo, low_m=lo_m, high=hi, high_m=hi_m,
                pos=(last - lo) / (hi - lo) * 100 if hi > lo else 50.0)


USED_IN = {}
RELATED = {}
for _ind in A["industries"]:
    for _sid in _ind["series"]:
        USED_IN.setdefault(_sid, []).append(dict(slug=_ind["slug"], name=_ind["name"]))
    for _ll in _ind["leadlag"]:
        for _sid in (_ll["lead"], _ll["follow"]):
            RELATED.setdefault(_sid, {})[(_ll["lead"], _ll["follow"])] = _ll
for _sid, _s in A["series"].items():
    _s["used_in"] = USED_IN.get(_sid, [])
    _s["related"] = [dict(r, lead_name=A["series"][r["lead"]]["name"], follow_name=A["series"][r["follow"]]["name"])
                     for r in sorted(RELATED.get(_sid, {}).values(), key=lambda r: -abs(r["r"]))]
    _s["hist"] = long_hist(_sid)
    _s["fresh"] = ST["series"].get(_sid)
    _obs = [(m, v) for m, v in _s["series"] if v is not None]
    _s["low_m"] = next(m for m, v in _obs if v == _s["low"])
    _s["high_m"] = next(m for m, v in _obs if v == _s["high"])


def head_meta(title, desc, path):
    """Search description, site icon and link-preview (Open Graph) tags."""
    e = lambda s: html.escape(s, quote=True)
    url = "https://dawsonwilhelmi.com/market-watch/" + path
    return "\n".join([
        f'<meta name="description" content="{e(desc)}">',
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        '<meta property="og:type" content="website">', '<meta property="og:site_name" content="Dawson Wilhelmi">',
        f'<meta property="og:title" content="{e(title)}">', f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{url}">', '<meta property="og:image" content="https://dawsonwilhelmi.com/og.png">',
        f'<link rel="canonical" href="{url}">',
        '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">'])


def render(title, payload, desc, path=""):
    blob = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return (TEMPLATE.replace("/*__TITLE__*/", html.escape(title + " · Dawson Wilhelmi", quote=False)).replace("/*__META__*/", head_meta(title, desc, path))
            .replace("/*__DATA__*/null", blob))


def slim(s, keep=24):
    """Hub only needs the last 24 months for sparklines."""
    return {**s, "series": s["series"][-keep:]}


hub = dict(page="hub", built=A["built"], version=VERSION, status_url="data/status.json", sources=SOURCES_OUT, industries=A["industries"], refresh=refresh(list(A["series"])),
           series={k: slim(v) for k, v in A["series"].items()},
           latest=latest_for(set(A["series"])), hub_spot=[G["spot"][k] for k in G["hub_spot"]],
           agency_pubs=sorted({tuple(v) for v in G["publishers"].values()}))
OUT = Path(os.environ.get("MW_OUT_DIR") or HERE)     # the scheduled run builds into a folder that is uploaded to Pages
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text(render("Industry Market Watch", hub,
    f"Input-cost signals for {len(A['industries'])} industries from published price, wage, freight and currency data, pulled from each publisher as it releases."))

for ind in A["industries"]:
    x = G["industries"].get(ind["slug"], dict(spot=[], hs=[], naics=[]))
    extras = dict(spot=[G["spot"][k] for k in x["spot"]],
                  hs=[{**h, **G["census"].get(h["code"], {})} for h in x["hs"]],
                  naics=[{**n, **G["usaspending"].get(n["code"], {})} for n in x["naics"]],
                  census_configured=bool(G["census"]))
    used = {s["publisher"] for s in extras["spot"]}
    if x["hs"]:
        used.add(G["publishers"]["CENSUS"][0])
    if x["naics"]:
        used.add(G["publishers"]["USASPENDING"][0])
    lt = latest_for(set(ind["series"]))
    used |= {v["publisher"] for v in lt.values()}
    payload = dict(page="industry", built=A["built"], version=VERSION, status_url="../data/status.json", sources=SOURCES_OUT, industry=ind, refresh=refresh(ind["series"]),
                   series={i: A["series"][i] for i in ind["series"]}, latest=lt, extras=extras,
                   agency_pubs=sorted({tuple(v) for v in G["publishers"].values() if v[0] in used}))
    out = OUT / ind["slug"] / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(f"{ind['name']} Market Watch", payload, f"{ind['name']}: input-cost drivers, buying signals and 6-month forecasts. {ind['blurb']}", ind["slug"] + "/"))

# the page compares this with its own version every minute to offer newly published data
if SP.exists():
    ST["version"] = VERSION
    SP.write_text(json.dumps(ST, indent=1, sort_keys=True) + "\n")
    if OUT != HERE or DATA != HERE / "data":
        (OUT / "data").mkdir(exist_ok=True)
        (OUT / "data" / "status.json").write_text(SP.read_text())

# a small summary for the portfolio home page, published beside the pages (see home_summary.py)
if OUT != HERE or DATA != HERE / "data":
    from home_summary import summary
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "data" / "home.json").write_text(json.dumps(summary(A), separators=(",", ":")))

print(f"built index.html + {len(A['industries'])} industry pages")
assert len(A["industries"]) == len(INDUSTRIES)
