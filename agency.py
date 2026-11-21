"""Agency data added beside the FRED series: EIA, USDA AMS, Census trade, USAspending.

Edit the dictionaries here; fetch_agency.py, analyze_agency.py and build.py adapt.
Every item credits its original publisher (AGENCY_PUB).
"""

AGENCY_PUB = {
    "EIA": ("U.S. Energy Information Administration, Open Data API", "https://www.eia.gov/opendata/"),
    "AMS-LMR": ("USDA Agricultural Marketing Service, Livestock Mandatory Reporting", "https://mpr.datamart.ams.usda.gov/"),
    "AMS-MMN": ("USDA Agricultural Marketing Service, My Market News", "https://mymarketnews.ams.usda.gov/"),
    "CENSUS": ("U.S. Census Bureau, International Trade API", "https://www.census.gov/data/developers/data-sets/international-trade.html"),
    "USASPENDING": ("U.S. Department of the Treasury, USAspending.gov", "https://www.usaspending.gov/"),
    "FRB": ("Board of Governors of the Federal Reserve System, H.10 Foreign Exchange Rates", "https://www.federalreserve.gov/releases/h10/"),
}

# ---------------------------------------------------------------- spot prices
# key: (name, unit, frequency, publisher, fetch spec, FRED series it refreshes or None, source page)
# EIA spec: (route, facet name, facet value, data column)
SPOT = {
    "WTI": ("WTI crude, Cushing", "$/bbl", "daily", "EIA", ("petroleum/pri/spt", "series", "RWTC", "value"), "DCOILWTICO",
            "https://www.eia.gov/dnav/pet/hist/RWTCD.htm"),
    "BRENT": ("Brent crude", "$/bbl", "daily", "EIA", ("petroleum/pri/spt", "series", "RBRTE", "value"), None,
              "https://www.eia.gov/dnav/pet/hist/RBRTED.htm"),
    "HH": ("Henry Hub natural gas", "$/MMBtu", "daily", "EIA", ("natural-gas/pri/fut", "series", "RNGWHHD", "value"), "MHHNGSP",
           "https://www.eia.gov/dnav/ng/hist/rngwhhdD.htm"),
    "JET": ("Jet fuel, US Gulf Coast", "$/gal", "daily", "EIA", ("petroleum/pri/spt", "series", "EER_EPJK_PF4_RGC_DPG", "value"), "DJFUELUSGULF",
            "https://www.eia.gov/dnav/pet/hist/EER_EPJK_PF4_RGC_DPGD.htm"),
    "ULSD_NYH": ("ULSD, New York Harbor", "$/gal", "daily", "EIA", ("petroleum/pri/spt", "series", "EER_EPD2DXL0_PF4_Y35NY_DPG", "value"), None,
                 "https://www.eia.gov/dnav/pet/hist/EER_EPD2DXL0_PF4_Y35NY_DPGD.htm"),
    "ULSD_GULF": ("ULSD, US Gulf Coast", "$/gal", "daily", "EIA", ("petroleum/pri/spt", "series", "EER_EPD2DXL0_PF4_RGC_DPG", "value"), None,
                  "https://www.eia.gov/dnav/pet/hist/EER_EPD2DXL0_PF4_RGC_DPGD.htm"),
    "DIESEL_US": ("Diesel retail, US", "$/gal", "weekly", "EIA", ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_NUS_DPG", "value"), "GASDESW",
                  "https://www.eia.gov/petroleum/gasdiesel/"),
    "DIESEL_R10": ("Diesel retail, East Coast", "$/gal", "weekly", "EIA", ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_R10_DPG", "value"), None,
                   "https://www.eia.gov/petroleum/gasdiesel/"),
    "DIESEL_R20": ("Diesel retail, Midwest", "$/gal", "weekly", "EIA", ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_R20_DPG", "value"), None,
                   "https://www.eia.gov/petroleum/gasdiesel/"),
    "DIESEL_R30": ("Diesel retail, Gulf Coast", "$/gal", "weekly", "EIA", ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_R30_DPG", "value"), None,
                   "https://www.eia.gov/petroleum/gasdiesel/"),
    "DIESEL_R40": ("Diesel retail, Rocky Mountain", "$/gal", "weekly", "EIA", ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_R40_DPG", "value"), None,
                   "https://www.eia.gov/petroleum/gasdiesel/"),
    "DIESEL_R50": ("Diesel retail, West Coast", "$/gal", "weekly", "EIA", ("petroleum/pri/gnd", "series", "EMD_EPD2D_PTE_R50_DPG", "value"), None,
                   "https://www.eia.gov/petroleum/gasdiesel/"),
    "ELEC_IND": ("Electricity, industrial (US avg)", "¢/kWh", "monthly", "EIA", ("electricity/retail-sales", "sectorid", "IND", "price"), None,
                 "https://www.eia.gov/electricity/monthly/"),
    "ELEC_COM": ("Electricity, commercial (US avg)", "¢/kWh", "monthly", "EIA", ("electricity/retail-sales", "sectorid", "COM", "price"), None,
                 "https://www.eia.gov/electricity/monthly/"),
    "NG_IND": ("Natural gas, industrial (US avg)", "$/Mcf", "monthly", "EIA", ("natural-gas/pri/sum", "series", "N3035US3", "value"), None,
               "https://www.eia.gov/dnav/ng/ng_pri_sum_dcu_nus_m.htm"),
    # USDA AMS. LMR DataMart needs no key; My Market News needs USDA_AMS_API_KEY.
    "BEEF_CH": ("Boxed beef cutout, Choice", "$/cwt", "daily", "AMS-LMR", ("2453", "Current Cutout Values", "choice_600_900_current"), None,
                "https://mymarketnews.ams.usda.gov/viewReport/2453"),
    "BEEF_SE": ("Boxed beef cutout, Select", "$/cwt", "daily", "AMS-LMR", ("2453", "Current Cutout Values", "select_600_900_current"), None,
                "https://mymarketnews.ams.usda.gov/viewReport/2453"),
    "EGGS": ("Shell eggs, Large white, national FOB", "¢/doz", "daily", "AMS-MMN",
             ("2843", "Report Detail Weighted", {"egg_type": "Graded Loose", "environment": "Caged", "color": "White",
                                                 "class": "Large", "origin": "National", "freight": "FOB"}), None,
             "https://mymarketnews.ams.usda.gov/viewReport/2843"),
    "CHX_BREAST": ("Chicken breast, boneless/skinless, FOB", "¢/lb", "weekly", "AMS-MMN",
                   ("3646", "Report Detail", {"item": "Breast - B/S", "freight": "FOB"}), None,
                   "https://mymarketnews.ams.usda.gov/viewReport/3646"),
    "CHX_WINGS": ("Chicken wings, whole, FOB", "¢/lb", "weekly", "AMS-MMN",
                  ("3646", "Report Detail", {"item": "Wings - Whole", "freight": "FOB"}), None,
                  "https://mymarketnews.ams.usda.gov/viewReport/3646"),
}

# Daily FX from the Federal Reserve (via FRED, existing FRED_API_KEY) for the "Latest" column.
FX_DAILY = ["DEXMXUS", "DEXJPUS", "DEXUSEU", "DEXTAUS", "DEXKOUS", "DEXCHUS", "DEXCAUS"]

# ------------------------------------------------------- per-industry extras
# spot: SPOT keys shown in the "Latest spot prices" card
# hs:   (HS4 code, label) imported products for the sourcing card (Census)
# naics: (code, label[, 4- or 6-digit codes]) federal contract obligations (USAspending;
#        the API takes 2-, 4- or 6-digit NAICS, so 3-digit sectors list their 4-digit parts)
EXTRAS = {
    "aerospace-defense": dict(spot=["JET", "BRENT"],
                              hs=[("8411", "Turbojets & gas turbines"), ("8803", "Aircraft parts"), ("7502", "Unwrought nickel")],
                              naics=[("3364", "Aerospace products & parts")]),
    "automotive": dict(spot=["DIESEL_US"],
                       hs=[("8708", "Motor vehicle parts"), ("4011", "New rubber tires"), ("8544", "Insulated wire & harnesses")]),
    "machinery-metal-fab": dict(spot=["ELEC_IND", "NG_IND"],
                                hs=[("8481", "Valves"), ("8482", "Ball & roller bearings"), ("7208", "Hot-rolled steel")]),
    "electronics-semis": dict(spot=[],
                              hs=[("8542", "Integrated circuits"), ("8541", "Diodes, transistors, solar cells"), ("8473", "Computer parts")]),
    "chemicals-plastics": dict(spot=["WTI", "BRENT", "HH", "NG_IND"],
                               hs=[("3901", "Polyethylene & ethylene polymers"), ("2902", "Cyclic hydrocarbons"), ("3907", "Polyesters & epoxides")]),
    "construction": dict(spot=["DIESEL_US"],
                         hs=[("4407", "Sawn lumber"), ("7214", "Steel bars & rebar"), ("2523", "Cement")],
                         naics=[("236", "Construction of buildings", ["2361", "2362"]), ("237", "Heavy & civil engineering", ["2371", "2372", "2373", "2379"])]),
    "electric-utilities": dict(spot=["HH", "ELEC_IND", "ELEC_COM"],
                               hs=[("8504", "Transformers & power supplies"), ("8544", "Insulated wire & cable"), ("8541", "Solar cells & diodes")]),
    "food-beverage-mfg": dict(spot=["DIESEL_US", "BEEF_CH", "EGGS"],
                              hs=[("1701", "Cane & beet sugar"), ("0901", "Coffee"), ("1507", "Soybean oil")]),
    "restaurants": dict(spot=["BEEF_CH", "BEEF_SE", "CHX_BREAST", "CHX_WINGS", "EGGS", "DIESEL_US"],
                        hs=[("0202", "Frozen beef"), ("0306", "Crustaceans (shrimp, crab)"), ("0804", "Avocados, mangoes & other fruit")]),
    "retail-ecommerce": dict(spot=["DIESEL_US"],
                             hs=[("9503", "Toys"), ("6403", "Leather footwear"), ("8517", "Phones & network gear")]),
    "packaging-cpg": dict(spot=["HH", "NG_IND"],
                          hs=[("4819", "Cartons & boxes"), ("3923", "Plastic packaging"), ("7010", "Glass containers")]),
    "healthcare": dict(spot=[],
                       hs=[("3004", "Medicines, dosed"), ("9018", "Medical instruments"), ("4015", "Rubber gloves & apparel")],
                       naics=[("3254", "Pharmaceuticals"), ("3391", "Medical equipment & supplies")]),
    "trucking-freight": dict(spot=["DIESEL_US", "DIESEL_R10", "DIESEL_R20", "DIESEL_R30", "DIESEL_R40", "DIESEL_R50", "ULSD_GULF"],
                             hs=[("4011", "New rubber tires"), ("8704", "Trucks")]),
    "air-ocean": dict(spot=["JET", "BRENT", "ULSD_NYH"],
                      hs=[("8411", "Turbojets & gas turbines"), ("8803", "Aircraft parts")]),
    "agriculture": dict(spot=["DIESEL_US", "HH"],
                        hs=[("3102", "Nitrogen fertilizers"), ("3104", "Potash fertilizers"), ("3808", "Pesticides & herbicides")]),
    "oil-gas": dict(spot=["WTI", "BRENT", "HH"],
                    hs=[("7304", "Seamless pipe & tube (OCTG)"), ("2709", "Crude oil")]),
    "data-centers": dict(spot=["ELEC_IND", "ELEC_COM"],
                         hs=[("8471", "Computers & servers"), ("8504", "Transformers & power supplies"), ("8473", "Computer parts")],
                         naics=[("518210", "Data processing & hosting"), ("541512", "Computer systems design")]),
}

HUB_SPOT = ["WTI", "BRENT", "HH", "DIESEL_US", "JET", "ULSD_NYH"]

# Census: first month pulled, top countries shown, single-country share flagged as concentrated
CENSUS_START = "2023-01"
TOP_N = 5
CONC_SHARE = 50.0
# USAspending: fiscal-year start pulled; months at the end treated as incomplete (DoD reports with a 90-day delay)
USA_START = "2022-10-01"
USA_LAG_MONTHS = 3
