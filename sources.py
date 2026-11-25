"""Where every series comes from, who owns it, and when its publisher releases it.

Each series in series.py is pulled from its original publisher (no intermediary).
collect.py reads this file to decide which publisher to call and when; build.py
uses it for the source, rights and release stamps shown beside every number.

Schedule fields (all times US Eastern, the publishers' own release clock):
  step       "D" business day, "W" week, "M" month, "Q" quarter
  lag        (earliest, latest) days after the end of a period that its first
             release normally falls. Before `earliest` the publisher is not called;
             after `latest` plus `grace` days the series is shown as late.
  hour       release time of day; polling starts then
  polls      most calls to this publisher per day
"""
from series import SERIES

PUBLIC_DOMAIN = "Public domain (U.S. government work)"

SOURCES = {
    "BLS": dict(
        name="U.S. Bureau of Labor Statistics", api="BLS Public Data API v2",
        url="https://www.bls.gov/developers/", rights=PUBLIC_DOMAIN, key="BLS_API_KEY", key_required=False,
        step="M", lag=(3, 20), grace=5, hour=(8, 30), polls=5, polls_keyed=14),
    "EIA": dict(
        name="U.S. Energy Information Administration", api="EIA Open Data API v2",
        url="https://www.eia.gov/opendata/", rights=PUBLIC_DOMAIN, key="EIA_API_KEY", key_required=True,
        step="M", lag=(1, 8), grace=5, hour=(10, 0), polls=8),
    "FRB": dict(
        name="Board of Governors of the Federal Reserve System", api="H.10 Data Download Program",
        url="https://www.federalreserve.gov/releases/h10/", rights=PUBLIC_DOMAIN, key=None, key_required=False,
        step="M", lag=(1, 8), grace=5, hour=(16, 30), polls=6),
    "WB": dict(
        name="World Bank", api="Commodity Price Data (The Pink Sheet), monthly workbook",
        url="https://www.worldbank.org/en/research/commodity-markets",
        rights="Creative Commons Attribution 4.0 (CC BY 4.0)", key=None, key_required=False,
        step="M", lag=(1, 8), grace=5, hour=(11, 0), polls=4),
    "BTS": dict(
        name="U.S. Bureau of Transportation Statistics", api="Transportation Services Index, data.bts.gov",
        url="https://www.bts.gov/transportation-services-index", rights=PUBLIC_DOMAIN, key=None, key_required=False,
        step="M", lag=(35, 55), grace=10, hour=(11, 0), polls=3),
}

# Release windows that differ from the publisher default: days after month end.
# Employment Situation (wages) lands in the first week, CPI around the 10th-15th, PPI a day or two later.
LAG = {"CES": (2, 10), "CUS": (8, 18), "CUU": (8, 18), "APU": (8, 18), "WPU": (9, 20), "PCU": (9, 20)}

# publisher key in series.py -> source here
_PUB_TO_SRC = {"BLS-PPI": "BLS", "BLS-CPI": "BLS", "BLS-CES": "BLS", "EIA": "EIA", "FRB": "FRB", "WB": "WB", "BTS": "BTS"}

# EIA monthly averages as EIA publishes them: (route, facet, value)
EIA_MONTHLY = {
    "DCOILWTICO": ("petroleum/pri/spt", "series", "RWTC"),
    "MHHNGSP": ("natural-gas/pri/fut", "series", "RNGWHHD"),
    "GASDESW": ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_NUS_DPG"),
    "DJFUELUSGULF": ("petroleum/pri/spt", "series", "EER_EPJK_PF4_RGC_DPG"),
}

# Federal Reserve H.10 currency codes. EUR is quoted USD per euro, the rest per USD.
H10 = {"DEXMXUS": "MXN", "DEXJPUS": "JPY", "DEXUSEU": "EUR", "DEXTAUS": "TWD",
       "DEXKOUS": "KRW", "DEXCHUS": "CNY", "DEXCAUS": "CAD"}

# World Bank Pink Sheet column names (matched on the start of the header, case-insensitive)
# and the factor that converts the published unit to the unit shown on the page.
PINK = {
    "WBALUMINUM": ("Aluminum", 1.0), "WBCOPPER": ("Copper", 1.0), "WBNICKEL": ("Nickel", 1.0),
    "WBWHEAT": ("Wheat, US HRW", 1.0), "WBMAIZE": ("Maize", 1.0), "WBSOYBEANS": ("Soybeans", 1.0),
    "WBSOYOIL": ("Soybean oil", 1.0), "WBSUGAR": ("Sugar, world", 1.0),
    "WBCOFFEE": ("Coffee, Arabica", 1.0), "WBBEEF": ("Beef", 1.0),
}

# BLS code where it differs from the id used on the page
BLS_CODE = {"CPIAUCSL": "CUSR0000SA0"}
# Series fetched only as inputs (not shown as drivers): CPI-U all items, to state price levels in today's dollars
EXTRA = {"CPIAUCSL": ("CPI-U, all items (deflator)", "BLS")}


def source_of(sid):
    if sid in EXTRA:
        return EXTRA[sid][1]
    return _PUB_TO_SRC[SERIES[sid][4]]


def code_of(sid):
    """The publisher's own identifier for the series."""
    src = source_of(sid)
    if src == "BLS":
        return BLS_CODE.get(sid, sid)
    if src == "EIA":
        return EIA_MONTHLY[sid][2]
    if src == "FRB":
        cur = H10[sid]
        return f"H10/H10/RXI$US_N.B.EU" if cur == "EUR" else f"H10 {cur}"
    if src == "WB":
        return PINK[sid][0]
    return "TSI freight"


def lag_of(sid):
    src = source_of(sid)
    if src == "BLS":
        return LAG.get(BLS_CODE.get(sid, sid)[:3], SOURCES[src]["lag"])
    return SOURCES[src]["lag"]


def series_url(sid):
    """A page at the publisher where a person can see the same series."""
    src = source_of(sid)
    if src == "BLS":
        return f"https://data.bls.gov/timeseries/{BLS_CODE.get(sid, sid)}"
    if src == "EIA":
        return {"DCOILWTICO": "https://www.eia.gov/dnav/pet/hist/RWTCM.htm",
                "MHHNGSP": "https://www.eia.gov/dnav/ng/hist/rngwhhdM.htm",
                "GASDESW": "https://www.eia.gov/petroleum/gasdiesel/",
                "DJFUELUSGULF": "https://www.eia.gov/dnav/pet/hist/EER_EPJK_PF4_RGC_DPGM.htm"}[sid]
    return SOURCES[src]["url"]


ALL_IDS = list(SERIES) + list(EXTRA)
BY_SOURCE = {}
for _sid in ALL_IDS:
    BY_SOURCE.setdefault(source_of(_sid), []).append(_sid)
