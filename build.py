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


def render(title, payload):
    blob = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("/*__TITLE__*/", title).replace("/*__DATA__*/null", blob)


def slim(s, keep=24):
    """Hub only needs the last 24 months for sparklines."""
    return {**s, "series": s["series"][-keep:]}


hub = dict(page="hub", built=A["built"], thresholds=THRESHOLDS, industries=A["industries"],
           series={k: slim(v) for k, v in A["series"].items()})
(HERE / "index.html").write_text(render("Industry Market Watch", hub))

for ind in A["industries"]:
    payload = dict(page="industry", built=A["built"], thresholds=THRESHOLDS, industry=ind,
                   series={i: A["series"][i] for i in ind["series"]})
    out = HERE / ind["slug"] / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(f"{ind['name']} Market Watch", payload))

print(f"built index.html + {len(A['industries'])} industry pages")
assert len(A["industries"]) == len(INDUSTRIES)
