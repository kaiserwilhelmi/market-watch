"""Tests for the collector: publisher response parsing, the release schedule and the value log.
Run with:  python -m unittest discover tests
The fixtures are cut from real responses (BLS API v2, Federal Reserve H.10 download, 25 Nov 2026)."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_tmp = tempfile.mkdtemp()
os.environ["MW_DATA_DIR"] = _tmp
import collect  # noqa: E402
from collect import ET  # noqa: E402

BLS = json.dumps({"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": [{"seriesID": "WPU1017", "data": [
    {"year": "2026", "period": "M10", "value": "399.645", "footnotes": [{"code": "P", "text": "Preliminary."}]},
    {"year": "2026", "period": "M09", "value": "398.100", "footnotes": [{}]},
    {"year": "2025", "period": "M13", "value": "380.000", "footnotes": [{}]},
    {"year": "2025", "period": "M10", "value": "-", "footnotes": [{"code": "X"}]}]}]}})
H10 = '''"Series Description","Euro-Area Euro","Mexican Peso"
"Unit:","Currency","Currency"
"Multiplier:","1","1"
"Currency:","EUR","MXN"
"Unique Identifier: ","H10/H10/RXI$US_N.B.EU","H10/H10/RXI_N.B.MX"
"Time Period","RXI$US_N.B.EU","RXI_N.B.MX"
2026-10-30,1.1000,18.00
2026-11-02,1.2000,18.50
2026-11-03,ND,ND
2026-11-04,1.4000,19.50
'''


class Parsers(unittest.TestCase):
    def test_bls(self):
        vals, prelim = collect.parse_bls(BLS)
        self.assertEqual(vals["WPU1017"], {"2026-10": "399.645", "2026-09": "398.100", "2025-10": ""})
        self.assertEqual(prelim["WPU1017"], {"2026-10"})

    def test_bls_error(self):
        with self.assertRaises(ValueError):
            collect.parse_bls(json.dumps({"status": "REQUEST_NOT_PROCESSED", "message": ["daily threshold"]}))

    def test_h10(self):
        d = collect.parse_h10(H10)
        self.assertEqual(d["EUR"], [("2026-10-30", 1.1), ("2026-11-02", 1.2), ("2026-11-04", 1.4)])
        self.assertEqual(collect.monthly_mean(d["MXN"], "2026-12"), {"2026-10": "18.0000", "2026-11": "19.0000"})
        self.assertEqual(collect.monthly_mean(d["MXN"], "2026-11"), {"2026-10": "18.0000"})   # month in progress left out

    def test_bts(self):
        rows = json.dumps([{"obs_date": "2026-08-01T00:00:00.000", "tsi_freight": "139.1"}, {"obs_date": "2026-09-01T00:00:00.000", "tsi_freight": "139.9"}])
        self.assertEqual(collect.parse_bts(rows), {"2026-08": "139.1", "2026-09": "139.9"})


class Schedule(unittest.TestCase):
    def t(self, *a):
        return datetime(*a, tzinfo=ET)

    def test_ppi_window(self):
        # October data in hand: November PPI is expected 9 to 20 days after 30 Nov, at 8:30 Eastern
        state, nxt, earliest, latest = collect.series_state("WPU1017", "2026-10", self.t(2026, 12, 1, 12, 0))
        self.assertEqual((state, nxt), ("current", "2026-11"))
        self.assertEqual((earliest.month, earliest.day, earliest.hour, earliest.minute), (12, 9, 8, 30))
        self.assertEqual(collect.series_state("WPU1017", "2026-10", self.t(2026, 12, 11, 9, 0))[0], "due")
        self.assertEqual(collect.series_state("WPU1017", "2026-10", self.t(2026, 12, 27, 9, 0))[0], "late")

    def test_slots(self):
        slots = collect.release_slots("BLS", keyed=False)
        self.assertEqual(len(slots), 5)                       # keyless BLS allowance: 5 calls a day
        self.assertEqual(slots[0], (8, 35))
        now = self.t(2026, 12, 11, 9, 0)
        self.assertIsNotNone(collect.due_slot(slots, None, now))
        self.assertIsNone(collect.due_slot(slots, self.t(2026, 12, 11, 8, 52), now))     # 8:50 slot already served
        self.assertIsNotNone(collect.due_slot(slots, self.t(2026, 12, 11, 8, 40), now))  # 8:50 slot not yet served
        self.assertEqual(collect.next_slot(slots, self.t(2026, 12, 11, 19, 0)).day, 14)  # Friday evening -> Monday


class Store(unittest.TestCase):
    def test_merge_logs_new_and_revised(self):
        t0, t1 = datetime(2026, 11, 13, 8, 36, tzinfo=ET), datetime(2026, 12, 11, 8, 36, tzinfo=ET)
        self.assertEqual(collect.merge("WPU1017", {"2026-09": "398.1", "2026-10": "399.645"}, t0), ["2026-09", "2026-10"])
        self.assertEqual(collect.first_seen("WPU1017", "2026-10")[1], "seed")
        self.assertEqual(collect.merge("WPU1017", {"2026-10": "399.700", "2026-11": "401.2"}, t1), ["2026-10", "2026-11"])
        self.assertEqual(collect.merge("WPU1017", {"2026-11": "401.200"}, t1), [])       # same number, nothing logged
        self.assertEqual(collect.read_series("WPU1017"), {"2026-09": "398.1", "2026-10": "399.700", "2026-11": "401.2"})
        seen, kind = collect.first_seen("WPU1017", "2026-11")
        self.assertEqual((seen, kind), ("2026-12-11T13:36:00Z", "new"))
        log = (Path(_tmp) / "vintage" / "WPU1017.csv").read_text()
        self.assertIn("2026-10,399.700,2026-12-11T13:36:00Z,revised", log)


if __name__ == "__main__":
    unittest.main()
