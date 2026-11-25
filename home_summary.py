"""Small summary of analytics.json for the portfolio home page (dawsonwilhelmi.com/).

The home page draws a map of every cost series feeding each industry and a short preview of one
industry. It only needs the latest value, the changes, the signal, 48 months of history and the
6-month forecast, so this is about a tenth of the size of analytics.json. build.py publishes it as
data/home.json; the home page build in the site repository imports summary() for its first-paint copy.
"""
SCHEMA = 1


def _r(v, digits=5):
    return None if v is None else float(f"{v:.{digits}g}")


def summary(analytics):
    series = {}
    for sid, s in analytics["series"].items():
        hist = s["series"][-48:]
        p12 = s.get("context", {}).get("p12")
        series[sid] = {
            "n": s["name"], "g": s["group"], "u": s["unit"],
            "l": _r(s["latest"]), "lm": s["latest_month"],
            "m12": round(s["cost_change"]["m12"], 1),      # in cost terms: a weaker dollar counts as a rise
            "raw12": round(s["change"]["m12"], 1),         # as published
            "sig": s["signal"],
            "p12": None if p12 is None else round(p12),    # percentile of the 12-month move in its own history
            "h0": hist[0][0], "h": [_r(v) for _, v in hist],
            "f": [[_r(f["mid"]), _r(f["lo"]), _r(f["hi"])] for f in s["forecast"]],
        }
    industries = [{"slug": i["slug"], "name": i["name"], "s": i["series"], "p12": round(i["pressure_12m"], 1),
                   "a": i["alerts"], "w": i["watches"], "o": i["opportunities"]} for i in analytics["industries"]]
    return {"schema": SCHEMA, "built": analytics["built"], "series": series, "ind": industries}
