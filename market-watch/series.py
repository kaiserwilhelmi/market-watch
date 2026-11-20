"""Series tracked by the dashboard. Add or remove rows here; everything else adapts.

direction:  +1 = a rising value means higher costs for a US buyer
            -1 = a rising value means lower costs (foreign currency per USD:
                 a stronger dollar makes imports cheaper)
"""
SERIES = [
    # id, name, group, unit, direction, what it means for a buyer
    ("WPU0913", "Paper", "Materials", "index", +1,
     "Copy paper, printing paper and paper stock pricing."),
    ("WPU0915", "Converted paper & packaging", "Materials", "index", +1,
     "Corrugated boxes, envelopes, labels and paper packaging."),
    ("WPU066", "Plastic resins", "Materials", "index", +1,
     "Feeds pricing for plastic office products, bags, film and binders."),
    ("WPU1017", "Steel mill products", "Materials", "index", +1,
     "Drives costs for shelving, filing cabinets, furniture frames and fasteners."),
    ("PCU484484", "Truck transportation", "Freight & fuel", "index", +1,
     "What carriers charge to move freight; shows up in delivered pricing."),
    ("GASDESW", "Diesel (US retail)", "Freight & fuel", "$/gal", +1,
     "Fuel surcharges on inbound freight move with diesel."),
    ("DEXMXUS", "Mexican peso per USD", "Currency", "MXN", -1,
     "Higher = stronger dollar = Mexican-sourced goods cost less."),
    ("DEXCHUS", "Chinese yuan per USD", "Currency", "CNY", -1,
     "Higher = stronger dollar = China-sourced goods cost less."),
]

# FRED CSV download (no API key needed). Daily/weekly series are averaged to monthly.
def fred_url(series_id, start="2021-01-01"):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    if series_id.startswith(("DEX", "GAS")):
        url += "&fq=Monthly&fam=avg"
    return url

# Signal thresholds on the cost-adjusted change (% change x direction)
THRESHOLDS = {
    #            alert 3m, alert 12m, watch 3m, watch 12m, opportunity 3m
    "Materials":      (5.0, 10.0, 2.0, 5.0, -3.0),
    "Freight & fuel": (8.0, 15.0, 3.0, 7.0, -5.0),
    "Currency":       (4.0,  8.0, 2.0, 4.0, -3.0),
}
