"""Series and industries tracked by the Industry Market Watch.

Edit SERIES or INDUSTRIES here; fetch_data.py, analyze.py and build.py adapt.

direction:  +1 = a rising value means higher costs for a US buyer
            -1 = a rising value means lower costs (foreign currency per USD:
                 a stronger dollar makes imports cheaper)
DEXUSEU is quoted USD per EUR, so a rising value means a weaker dollar: +1.
Cass shipments is a volume measure: rising volume tightens capacity, so +1.
"""

PUB = {
    "BLS-PPI": ("U.S. Bureau of Labor Statistics, Producer Price Index", "https://www.bls.gov/ppi/"),
    "BLS-CPI": ("U.S. Bureau of Labor Statistics, Consumer Price Index", "https://www.bls.gov/cpi/"),
    "BLS-CES": ("U.S. Bureau of Labor Statistics, Current Employment Statistics", "https://www.bls.gov/ces/"),
    "EIA": ("U.S. Energy Information Administration", "https://www.eia.gov/"),
    "IMF": ("International Monetary Fund, Primary Commodity Prices", "https://www.imf.org/en/Research/commodity-prices"),
    "FRB": ("Board of Governors of the Federal Reserve System, H.10 Foreign Exchange Rates", "https://www.federalreserve.gov/releases/h10/"),
    "CASS": ("Cass Information Systems, Cass Freight Index", "https://www.cassinfo.com/freight-audit-payment/cass-transportation-indexes"),
}

# id: (short name, group, unit, direction, publisher key)
SERIES = {
    # Materials (PPI goods)
    "PCU336413336413": ("Aircraft parts & equipment", "Materials", "index", +1, "BLS-PPI"),
    "PCU336412336412": ("Aircraft engines & parts", "Materials", "index", +1, "BLS-PPI"),
    "WPU1025": ("Nonferrous mill shapes", "Materials", "index", +1, "BLS-PPI"),
    "PCU336390336390": ("Other motor vehicle parts", "Materials", "index", +1, "BLS-PPI"),
    "WPU1017": ("Steel mill products", "Materials", "index", +1, "BLS-PPI"),
    "WPU101706": ("Steel pipe & tube", "Materials", "index", +1, "BLS-PPI"),
    "WPU071": ("Rubber & rubber products", "Materials", "index", +1, "BLS-PPI"),
    "WPU072": ("Plastic products", "Materials", "index", +1, "BLS-PPI"),
    "PCU334413334413": ("Semiconductors", "Materials", "index", +1, "BLS-PPI"),
    "PCU334111334111": ("Electronic computers (servers)", "Materials", "index", +1, "BLS-PPI"),
    "WPU114": ("General purpose machinery", "Materials", "index", +1, "BLS-PPI"),
    "WPU1026": ("Nonferrous wire & cable", "Materials", "index", +1, "BLS-PPI"),
    "WPU066": ("Plastic resins & materials", "Materials", "index", +1, "BLS-PPI"),
    "PCU325211325211": ("Resin manufacturing (PPI industry)", "Materials", "index", +1, "BLS-PPI"),
    "PCU325110325110": ("Petrochemicals", "Materials", "index", +1, "BLS-PPI"),
    "WPU061": ("Industrial chemicals", "Materials", "index", +1, "BLS-PPI"),
    "WPUSI012011": ("Construction materials", "Materials", "index", +1, "BLS-PPI"),
    "WPU081": ("Lumber", "Materials", "index", +1, "BLS-PPI"),
    "PCU327310327310": ("Cement", "Materials", "index", +1, "BLS-PPI"),
    "PCU327320327320": ("Ready-mix concrete", "Materials", "index", +1, "BLS-PPI"),
    "PCU335311335311": ("Power & specialty transformers", "Materials", "index", +1, "BLS-PPI"),
    "PCU333415333415": ("HVAC & refrigeration equipment", "Materials", "index", +1, "BLS-PPI"),
    "PCU333111333111": ("Farm machinery", "Materials", "index", +1, "BLS-PPI"),
    "PCU332431332431": ("Metal cans", "Materials", "index", +1, "BLS-PPI"),
    "PCU327213327213": ("Glass containers", "Materials", "index", +1, "BLS-PPI"),
    "PCU322211322211": ("Corrugated boxes", "Materials", "index", +1, "BLS-PPI"),
    "WPU0915": ("Converted paper & paperboard", "Materials", "index", +1, "BLS-PPI"),
    "WPU0638": ("Pharmaceutical preparations", "Materials", "index", +1, "BLS-PPI"),
    "PCU339113339113": ("Surgical appliances & supplies", "Materials", "index", +1, "BLS-PPI"),
    "PCU339112339112": ("Surgical & medical instruments", "Materials", "index", +1, "BLS-PPI"),
    "WPU0652": ("Fertilizer materials", "Materials", "index", +1, "BLS-PPI"),
    "PCU325320325320": ("Pesticides & ag chemicals", "Materials", "index", +1, "BLS-PPI"),
    "WPU02": ("Processed foods & feeds", "Materials", "index", +1, "BLS-PPI"),
    "WPU0221": ("Meats (wholesale)", "Materials", "index", +1, "BLS-PPI"),
    # Commodities (IMF, BLS average price)
    "PNICKUSDM": ("Nickel", "Commodities", "$/t", +1, "IMF"),
    "PALUMUSDM": ("Aluminum", "Commodities", "$/t", +1, "IMF"),
    "PCOPPUSDM": ("Copper", "Commodities", "$/t", +1, "IMF"),
    "PWHEAMTUSDM": ("Wheat", "Commodities", "$/t", +1, "IMF"),
    "PMAIZMTUSDM": ("Corn", "Commodities", "$/t", +1, "IMF"),
    "PSOYBUSDM": ("Soybeans", "Commodities", "$/t", +1, "IMF"),
    "PSUGAISAUSDM": ("Sugar No. 11", "Commodities", "¢/lb", +1, "IMF"),
    "PSOILUSDM": ("Soybean oil", "Commodities", "$/t", +1, "IMF"),
    "PCOFFOTMUSDM": ("Coffee, other mild arabica", "Commodities", "¢/lb", +1, "IMF"),
    "PBEEFUSDM": ("Beef", "Commodities", "¢/lb", +1, "IMF"),
    "APU0000708111": ("Eggs, Grade A large", "Commodities", "$/doz", +1, "BLS-CPI"),
    # Energy
    "DCOILWTICO": ("WTI crude oil", "Energy", "$/bbl", +1, "EIA"),
    "MHHNGSP": ("Henry Hub natural gas", "Energy", "$/MMBtu", +1, "EIA"),
    "GASDESW": ("Diesel, US retail", "Energy", "$/gal", +1, "EIA"),
    "DJFUELUSGULF": ("Jet fuel, US Gulf Coast", "Energy", "$/gal", +1, "EIA"),
    "WPU051": ("Coal", "Energy", "index", +1, "BLS-PPI"),
    "WPU0543": ("Industrial electric power", "Energy", "index", +1, "BLS-PPI"),
    # Freight & services
    "PCU484121484121": ("Truckload, long-distance", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU482111482111": ("Line-haul rail", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU483111483111": ("Deep sea freight", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU481112481112": ("Air freight, scheduled", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU481111481111": ("Passenger air", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU492110492110": ("Couriers & express", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU493110493110": ("General warehousing", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU518210518210": ("Data processing & hosting", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU213111213111": ("Oil & gas well drilling", "Freight & services", "index", +1, "BLS-PPI"),
    "PCU213112213112": ("Oilfield support services", "Freight & services", "index", +1, "BLS-PPI"),
    "FRGSHPUSM649NCIS": ("Cass shipments (volume)", "Freight & services", "index", +1, "CASS"),
    "FRGEXPUSM649NCIS": ("Cass expenditures", "Freight & services", "index", +1, "CASS"),
    "CUSR0000SEFV": ("CPI food away from home", "Freight & services", "index", +1, "BLS-CPI"),
    # Labor (average hourly earnings)
    "CES3000000008": ("Mfg wages, production workers", "Labor", "$/hr", +1, "BLS-CES"),
    "CES3000000003": ("Mfg wages, all employees", "Labor", "$/hr", +1, "BLS-CES"),
    "CES2000000003": ("Construction wages", "Labor", "$/hr", +1, "BLS-CES"),
    "CES4422000003": ("Utilities wages", "Labor", "$/hr", +1, "BLS-CES"),
    "CES7000000003": ("Leisure & hospitality wages", "Labor", "$/hr", +1, "BLS-CES"),
    "CES4200000003": ("Retail wages", "Labor", "$/hr", +1, "BLS-CES"),
    "CES4300000003": ("Transportation & warehousing wages", "Labor", "$/hr", +1, "BLS-CES"),
    "CES6500000003": ("Education & health wages", "Labor", "$/hr", +1, "BLS-CES"),
    "CES1000000003": ("Mining & logging wages", "Labor", "$/hr", +1, "BLS-CES"),
    # Currency
    "DEXMXUS": ("Mexican peso per USD", "Currency", "MXN", -1, "FRB"),
    "DEXJPUS": ("Japanese yen per USD", "Currency", "JPY", -1, "FRB"),
    "DEXUSEU": ("USD per euro", "Currency", "USD", +1, "FRB"),
    "DEXTAUS": ("Taiwan dollar per USD", "Currency", "TWD", -1, "FRB"),
    "DEXKOUS": ("Korean won per USD", "Currency", "KRW", -1, "FRB"),
    "DEXCHUS": ("Chinese yuan per USD", "Currency", "CNY", -1, "FRB"),
    "DEXCAUS": ("Canadian dollar per USD", "Currency", "CAD", -1, "FRB"),
}

# Daily or weekly at source; averaged to monthly.
NON_MONTHLY = ("DEX", "DCOILWTICO", "DJFUELUSGULF", "GASDESW")

INDUSTRIES = [
    ("aerospace-defense", "Aerospace & defense",
     "Long-cycle programs with specialty alloys, castings and engines. Escalation clauses usually index to PPI aircraft parts and metals.",
     ["PCU336413336413", "PCU336412336412", "WPU1025", "PNICKUSDM", "PALUMUSDM", "DJFUELUSGULF", "CES3000000008"]),
    ("automotive", "Automotive",
     "High-volume parts with steel, aluminum, rubber and chips, much of it sourced in Mexico and Japan.",
     ["PCU336390336390", "WPU1017", "PALUMUSDM", "WPU071", "PCU334413334413", "CES3000000008", "DEXMXUS", "DEXJPUS"]),
    ("machinery-metal-fab", "Machinery & metal fabrication",
     "Steel- and copper-heavy builds; European components priced in euros.",
     ["WPU114", "WPU1017", "PCOPPUSDM", "WPU0543", "CES3000000008", "DEXUSEU"]),
    ("electronics-semis", "Electronics & semiconductors",
     "Chips, copper and resin, with supply concentrated in Taiwan, Korea and China.",
     ["PCU334413334413", "PCOPPUSDM", "WPU1026", "WPU066", "DEXTAUS", "DEXKOUS", "DEXCHUS"]),
    ("chemicals-plastics", "Chemicals & plastics",
     "Feedstock-driven: crude oil and natural gas flow through petrochemicals into resins within months.",
     ["DCOILWTICO", "MHHNGSP", "PCU325110325110", "WPU061", "PCU325211325211", "WPU072", "CES3000000003"]),
    ("construction", "Construction",
     "Bid-to-build lag makes escalation risk real; lumber and steel swing hardest.",
     ["WPUSI012011", "WPU081", "PCU327310327310", "PCU327320327320", "WPU1017", "CES2000000003", "DEXCAUS"]),
    ("electric-utilities", "Electric utilities",
     "Fuel costs pass through to rates; grid equipment (transformers, cable) has long lead times.",
     ["MHHNGSP", "WPU051", "WPU0543", "PCU335311335311", "WPU1026", "CES4422000003"]),
    ("food-beverage-mfg", "Food & beverage manufacturing",
     "Grains, sweeteners and oils drive ingredient cost; cans and glass drive packaging.",
     ["PWHEAMTUSDM", "PMAIZMTUSDM", "PSUGAISAUSDM", "PSOILUSDM", "PCOFFOTMUSDM", "PCU332431332431", "PCU327213327213", "CES3000000008"]),
    ("restaurants", "Restaurants & food service",
     "Protein, eggs and labor are the big three; distributor delivery fees follow diesel.",
     ["WPU02", "WPU0221", "PBEEFUSDM", "APU0000708111", "CUSR0000SEFV", "CES7000000003", "GASDESW"]),
    ("retail-ecommerce", "Retail & e-commerce fulfillment",
     "Parcel, warehousing and corrugated are the controllable cost lines.",
     ["PCU492110492110", "PCU493110493110", "PCU322211322211", "WPU072", "CES4200000003", "CES4300000003"]),
    ("packaging-cpg", "Packaging & CPG",
     "Substrates (paper, resin, metal, glass) set packaging cost; aluminum drives cans.",
     ["PCU322211322211", "WPU0915", "PCU325211325211", "PCU332431332431", "PCU327213327213", "PALUMUSDM"]),
    ("healthcare", "Healthcare",
     "Drugs, devices and supplies under GPO contracts; many generics and supplies come from China.",
     ["WPU0638", "PCU339113339113", "PCU339112339112", "WPU072", "CES6500000003", "DEXCHUS"]),
    ("trucking-freight", "Trucking & freight",
     "Diesel feeds fuel surcharges within weeks; Cass volumes flag capacity shifts.",
     ["GASDESW", "PCU484121484121", "FRGSHPUSM649NCIS", "FRGEXPUSM649NCIS", "PCU482111482111", "WPU071", "CES4300000003"]),
    ("air-ocean", "Airlines, air cargo & ocean",
     "Jet fuel and ocean rates dominate; China and euro lanes carry FX exposure.",
     ["DJFUELUSGULF", "PCU481112481112", "PCU481111481111", "PCU483111483111", "CES4300000003", "DEXUSEU", "DEXCHUS"]),
    ("agriculture", "Agriculture",
     "Input buyers face fertilizer, chemicals, machinery and fuel; crop prices set what growers can absorb.",
     ["WPU0652", "PCU325320325320", "PCU333111333111", "GASDESW", "PMAIZMTUSDM", "PSOYBUSDM", "PWHEAMTUSDM"]),
    ("oil-gas", "Oil & gas",
     "Oilfield service and tubular pricing follows crude with a lag; rig activity drives the cycle.",
     ["DCOILWTICO", "MHHNGSP", "PCU213111213111", "PCU213112213112", "WPU101706", "CES1000000003"]),
    ("data-centers", "Data centers",
     "Power, servers, chips, transformers and cooling; electrical gear has the longest lead times.",
     ["WPU0543", "PCU334111334111", "PCU334413334413", "PCU335311335311", "PCU333415333415", "WPU1026", "PCU518210518210", "CES2000000003"]),
]

# Signal thresholds on the cost-adjusted % change (% change x direction)
#            alert 3m, alert 12m, watch 3m, watch 12m, opportunity 3m
def fred_url(series_id, start="2018-01-01"):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    if series_id.startswith(NON_MONTHLY):
        url += "&fq=Monthly&fam=avg"
    return url
