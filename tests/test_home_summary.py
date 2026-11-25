"""home.json must carry every series each industry lists, in the shape the home page reads."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from home_summary import summary

DATA = Path(__file__).resolve().parent.parent / "data"   # the copy in the repo; test_collect points paths.DATA at a temp folder


class HomeSummary(unittest.TestCase):
    def test_summary_shape(self):
        check()


def check():
    a = json.loads((DATA / "analytics.json").read_text())
    h = summary(a)
    assert h["schema"] == 1 and h["built"] == a["built"]
    assert len(h["ind"]) == len(a["industries"]) and len(h["series"]) == len(a["series"])
    for ind in h["ind"]:
        assert ind["s"] and all(k in h["series"] for k in ind["s"])
    for sid, s in h["series"].items():
        src = a["series"][sid]
        assert s["sig"] in ("Alert", "Watch", "Opportunity", "Stable")
        assert len(s["h"]) == min(48, len(src["series"])) and s["h0"] == src["series"][-len(s["h"])][0]
        assert len(s["f"]) == 6 and all(len(f) == 3 for f in s["f"])
        assert abs(s["l"] - src["latest"]) <= abs(src["latest"]) * 1e-4
    assert len(json.dumps(h, separators=(",", ":"))) < 150_000


if __name__ == "__main__":
    unittest.main()
