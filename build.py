"""Build the hub page and one page per industry from data/analytics.json.

Output: index.html (hub) and <slug>/index.html for each industry. Each page is a
single self-contained HTML file with its data embedded.
"""
import json
from pathlib import Path

from series import INDUSTRIES, THRESHOLDS

HERE = Path(__file__).parent
A = json.loads((HERE / "data" / "analytics.json").read_text())
TEMPLATE = (HERE / "template.html").read_text()
AP = HERE / "data" / "agency_analytics.json"
G = json.loads(AP.read_text()) if AP.exists() else dict(spot={}, fx={}, census={}, usaspending={}, industries={}, hub_spot=[], publishers={})


def latest_for(ids):
    """Newest daily/weekly value for FRED rows that have one (EIA spot or Fed daily FX)."""
    out = {}
    for k, s in G["spot"].items():
        if s.get("fred") in ids:
            out[s["fred"]] = {f: s[f] for f in ("latest", "latest_date", "prev_month", "prev_month_avg", "vs_prev_month", "freq", "publisher")}
    for sid, f in G["fx"].items():
        if sid in ids:
            out[sid] = {**f, "freq": "daily", "publisher": G["publishers"]["FRB"][0]}
    return out


def render(title, payload):
    blob = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("/*__TITLE__*/", title).replace("/*__DATA__*/null", blob)


def slim(s, keep=24):
    """Hub only needs the last 24 months for sparklines."""
    return {**s, "series": s["series"][-keep:]}


hub = dict(page="hub", built=A["built"], thresholds=THRESHOLDS, industries=A["industries"],
           series={k: slim(v) for k, v in A["series"].items()},
           latest=latest_for(set(A["series"])), hub_spot=[G["spot"][k] for k in G["hub_spot"]],
           agency_pubs=sorted({tuple(v) for v in G["publishers"].values()}))
(HERE / "index.html").write_text(render("Industry Market Watch", hub))

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
    payload = dict(page="industry", built=A["built"], thresholds=THRESHOLDS, industry=ind,
                   series={i: A["series"][i] for i in ind["series"]}, latest=lt, extras=extras,
                   agency_pubs=sorted({tuple(v) for v in G["publishers"].values() if v[0] in used}))
    out = HERE / ind["slug"] / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(f"{ind['name']} Market Watch", payload))

print(f"built index.html + {len(A['industries'])} industry pages")
assert len(A["industries"]) == len(INDUSTRIES)
