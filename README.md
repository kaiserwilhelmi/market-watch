# Industry Market Watch

**Business question:** Which input costs are moving for buyers in each of 17 industries, where are they likely to be in 6 months, and what should a buyer do about it now?

A hub page ranks 17 industries by input-cost pressure. Each industry page has a dense driver table with buying signals, 6-month forecasts with 80% ranges and backtested accuracy, a history-and-forecast chart, a contract price-escalation calculator, lead/lag pairs and a correlation table. All data is real and official; nothing is sample data.

## Industries and drivers (80 series)

| Industry | Drivers |
|---|---|
| Aerospace & defense | PPI aircraft parts, aircraft engines, nonferrous mill shapes; nickel, aluminum; jet fuel; manufacturing wages |
| Automotive | PPI motor vehicle parts, steel mill products, rubber, semiconductors; aluminum; manufacturing wages; MXN, JPY |
| Machinery & metal fabrication | PPI general purpose machinery, steel, industrial power; copper; manufacturing wages; EUR |
| Electronics & semiconductors | PPI semiconductors, nonferrous wire & cable, plastic resins; copper; TWD, KRW, CNY |
| Chemicals & plastics | WTI crude, Henry Hub gas; PPI petrochemicals, industrial chemicals, resin, plastic products; manufacturing wages |
| Construction | PPI construction materials, lumber, cement, ready-mix, steel; construction wages; CAD |
| Electric utilities | Henry Hub gas; PPI coal, industrial power, transformers, wire & cable; utilities wages |
| Food & beverage manufacturing | Wheat, corn, sugar, soybean oil, coffee; PPI metal cans, glass containers; manufacturing wages |
| Restaurants & food service | PPI processed foods, meats; beef; eggs; CPI food away from home; leisure & hospitality wages; diesel |
| Retail & e-commerce fulfillment | PPI couriers, warehousing, corrugated boxes, plastic products; retail and transportation wages |
| Packaging & CPG | PPI corrugated, converted paper, resin, metal cans, glass containers; aluminum |
| Healthcare | PPI pharmaceuticals, surgical supplies, surgical instruments, plastic products; education & health wages; CNY |
| Trucking & freight | Diesel; PPI truckload, rail, rubber; freight services index, less-than-truckload rates; transportation wages |
| Airlines, air cargo & ocean | Jet fuel; PPI air freight, passenger air, deep sea freight; transportation wages; EUR, CNY |
| Agriculture | PPI fertilizer, ag chemicals, farm machinery; diesel; corn, soybeans, wheat |
| Oil & gas | WTI crude, Henry Hub gas; PPI drilling, oilfield services, steel pipe & tube; mining & logging wages |
| Data centers | PPI industrial power, computers, semiconductors, transformers, HVAC equipment, wire & cable, data hosting; construction wages |

Series IDs, names, units and publishers are in `series.py`.

## Data publishers

Every series is pulled directly from its original publisher by `collect.py`. There is no intermediary. `sources.py` lists each publisher, its usage rights and its release schedule.

| Publisher | Series | Feed | Rights | Key |
| --- | --- | --- | --- | --- |
| U.S. Bureau of Labor Statistics | Producer Price Index, Consumer Price Index and average prices, average hourly earnings (58 series, plus CPI-U as the deflator) | Public Data API v2 | Public domain | `BLS_API_KEY` (optional, raises the daily allowance) |
| World Bank | Commodity Price Data, "The Pink Sheet": aluminum, copper, nickel, wheat, corn, soybeans, soybean oil, sugar, coffee, beef | Monthly workbook | CC BY 4.0 | none |
| Board of Governors of the Federal Reserve System | H.10 foreign exchange rates, 7 currencies | Data Download Program | Public domain | none |
| U.S. Energy Information Administration | WTI crude, Henry Hub natural gas, US retail diesel, US Gulf Coast jet fuel (monthly averages as EIA publishes them) | Open Data API v2 | Public domain | `EIA_API_KEY` |
| U.S. Bureau of Transportation Statistics | Freight Transportation Services Index | data.bts.gov | Public domain | none |

World Bank attribution: The World Bank, Commodity Price Data (The Pink Sheet). The World Bank's dataset terms note that some series within a dataset can come from third parties; the Pink Sheet page lists no such restriction for these ten.

### Release-driven collection

`collect.py` runs every 15 minutes but only calls a publisher when one of its releases is due:

- Each series has a release window, counted in days after the end of the period it covers (for example producer prices 9 to 20 days after month end, at 8:30 Eastern). Before the window opens the publisher is not called.
- Inside the window the publisher is polled shortly after its release time and then about hourly, within its daily allowance. A series that passes the end of its window is marked **late**; a publisher that fails three calls in a row is marked **not updating**. Previous values are always kept.
- Every new or revised value is appended to `data/vintage/<id>.csv` with the time it was first seen, so the page can say when a number arrived and a later forecast test can use what was known at the time (Croushore and Stark, 2001).
- `data/status.json` holds the result: per series the period, first-seen time, preliminary flag, state and next expected release; per publisher the last call, its result and the next planned call. The pages embed it and re-read it every minute.
- On Sunday mornings each publisher's full history is pulled again to pick up revisions older than the usual window.

## Agency data (daily, weekly and sourcing)

Pulled straight from the publishing agency by `fetch_agency.py`; items and per-industry assignments are in `agency.py`.

| Source | Publisher | What it adds | Key |
| --- | --- | --- | --- |
| EIA Open Data API | U.S. Energy Information Administration | Daily crude (WTI, Brent), Henry Hub, jet fuel and ULSD spot; weekly retail diesel by PADD region; monthly industrial/commercial electricity and industrial natural gas prices | `EIA_API_KEY` |
| LMR DataMart | USDA Agricultural Marketing Service | Daily boxed beef cutout (Choice, Select; report LM_XB403) | none |
| My Market News API | USDA Agricultural Marketing Service | Daily shell egg index (report 2843), weekly chicken parts (report 3646) | `USDA_AMS_API_KEY` |
| International Trade API | U.S. Census Bureau | Monthly general imports by 4-digit HS code and country | `CENSUS_API_KEY` |
| USAspending API | U.S. Department of the Treasury | Monthly federal contract obligations by NAICS code | none |
| H.10 Data Download | Board of Governors of the Federal Reserve System | Daily exchange rates for the "Daily/weekly" column (the Board posts them weekly) | none |

- **Daily/weekly column.** For monthly rows with a faster source (WTI, Henry Hub, jet fuel, diesel, FX), the newest value is shown against last month's average, which is what the monthly series will print next. Forecasts stay monthly.
- **Import sourcing.** Latest 12 months of general imports vs the prior 12; top 5 countries by share; concentration is the Herfindahl-Hirschman Index of country shares (Rhoades, 1993), labeled with the U.S. DOJ/FTC (2023) Merger Guidelines cut-offs (1,000 and 1,800) as a yardstick.
- **Federal demand.** Trailing 12 complete months of contract obligations vs the prior 12. The latest 3 months are shown but excluded, because agencies (DoD with a 90-day delay) are still reporting them.
- Census is refreshed on Mondays (it is monthly and a full pull takes about 10 minutes). Spot prices are checked four times each business day, the energy outlook and federal spending once.
- A source whose key is missing is skipped and its card is hidden; a failed download keeps the previous values. `verify_agency.py` recomputes every change, share, HHI and total with separate plain-Python code, and the workflow stops if any differ.

## Method

- **Cost impact and signals.** Each % change is multiplied by its direction (+1 for prices; −1 for foreign currency per USD, because a stronger dollar makes imports cheaper; USD per EUR stays +1). Signals (Alert, Watch, Opportunity, Stable) rank each driver's 3- and 12-month cost change against its own history since 2004 (see *Signals and recommendations* below). Industry pressure is the **median** driver.
- **Forecast.** Damped additive-trend exponential smoothing on log levels (Gardner & McKenzie, 1985; Hyndman & Athanasopoulos, 2021), via statsmodels. Benchmark: naive (no change).
- **Backtest.** Rolling origin (Tashman, 2000): refit every month from Dec 2020, forecast 1–6 months ahead, score MAPE from Jan 2022. The published forecast uses whichever of model or naive had the lower average MAPE. Naive often wins for commodities and currencies, consistent with Meese & Rogoff (1983).
- **80% range.** 10th–90th percentile of the chosen method's past log errors at each horizon (empirical prediction intervals; Williams & Goodman, 1971). The hit rate is tested out of sample: since Jan 2023, each range is rebuilt only from errors known at that date.
- **Lead/lag.** Correlation of monthly log changes, X at t−k vs Y at t, k = 0…6; a pair is listed when the best lagged |r| beats the same-month |r| and exceeds 2/√n. Descriptive, not causal.
- **Correlation.** Pearson correlation of 12-month % changes since Jan 2019.
- **Escalation calculator.** P₁ = P₀ × [F + Σ wᵢ × Iᵢ(t₁)/Iᵢ(t₀)], the standard index-linked price adjustment, with fixed share F = 1 − Σwᵢ. Future months use forecast midpoints, with an all-components-at-range-edge stress test.

## Signals and recommendations

The old rule flagged any rise above a fixed % per group and said "lock in pricing". That ignores context: locking in at the peak of a war- or outage-driven spike can mean overpaying for the whole contract. `context.py` now adds three pieces of context and picks the advice from them. `verify_calcs.py` recomputes all of it in plain Python.

| Step | Rule | Why |
|---|---|---|
| 1. How unusual is the move? | Rank the latest 3- and 12-month cost change against all of that series' own 3- and 12-month changes since Jan 2004. **Alert** ≥ 90th percentile, **Watch** ≥ 75th, **Opportunity** 3-month fall ≤ 10th. The move must also be ≥ 1% (3 mo) or ≥ 2% (12 mo). | Judge variation against the process's own normal range, as in control charts (Montgomery). Use empirical ranks, not a normal curve, because price changes are fat-tailed (Mandelbrot 1963). Cut-offs and floors are judgment calls. |
| 2. Where is the price? | Percentile of the latest level among monthly levels since 2004, **after inflation** (CPI-U). Currencies use nominal levels, and wages are not ranked. High ≥ 80th, low ≤ 20th. | Spikes tend to be short relative to slumps (Cashin, McDermott & Scott 2002; Deaton & Laroque 1992). A high level is a reason for caution, not a forecast. |
| 3. What does the outlook say? | Crude, natural gas, diesel, jet fuel and industrial power use EIA's Short-Term Energy Outlook: the average over the next 12 months vs the current period (≤ −5% counts as easing). Other series use the backtested forecast only where it beat "no change". | Futures and no-change forecasts are hard to beat (Alquist, Kilian & Vigfusson 2013), so outside energy no direction is assumed. EIA stopped publishing free NYMEX futures in April 2024, so futures curves are not used. |
| 4. Advice | Rising and high, outlook easing: avoid long fixed prices and use short terms or index-linked pricing with a cap. Rising and high: cover in stages and cap rather than fix. Rising from a normal level: securing more in stages is reasonable. Labor: budget for it, with an index-linked escalator and a cap. FX: hedge, don't forecast. Falling and low: rebid and fix a larger share. Falling from high: get pass-through but stay index-linked. | Hedge to limit bad outcomes, not to beat the market (Stulz 1996). Firms gain little from timing hedges (Brown, Crabb & Haushalter 2006). Use a portfolio of fixed, capped and spot volume (Martínez-de-Albéniz & Simchi-Levi 2005). Use index-based price adjustment when markets are unstable (FAR 16.203). Wages rarely fall (Dickens et al. 2007). Category strategy still matters (Kraljic 1983; Mena, van Hoek & Christopher 2021, ch. 3, and p. 174: "keep the most options open" in volatile markets). |

Each "What to do now" item shows its three context numbers and a "Why this advice" list. The EIA outlook is refreshed from the EIA API (`steo` route) by `fetch_agency.py`. If that fails, the last good `data/steo.json` is kept, and it is ignored once it is more than 4 months old. The initial file is the November 2026 STEO Table 2 (quarterly), typed from EIA's PDF.

**Not automated:** the cause of a move. Kilian (2009) shows oil price rises last different lengths of time depending on whether they come from supply cuts, global demand or precautionary buying. EIA's STEO text names the drivers it sees, so check it before committing to long terms.

## Data quality checks

- Migration check (Nov 25, 2026): when the series moved from FRED copies to the publishers' own feeds, every overlapping month since 2004 was compared in a separate script. All 15,681 BLS values (58 series) matched exactly, and all 1,918 monthly Federal Reserve exchange-rate averages matched within 0.01% (rounding). Henry Hub and diesel matched exactly. EIA's own monthly averages for WTI and Gulf Coast jet fuel differ from an average of daily prices in some months (largest gap 1.63% for WTI, 6.54% for jet fuel, mostly before 2018); the site now uses EIA's monthly figure. The World Bank, BTS and less-than-truckload series are new and have no earlier copy to compare.
- `verify_calcs.py` independently recomputes every % change, signal, range, naive backtest, industry median, correlation and lead/lag coefficient, and refits the model for a sample of series. The collector run stops before publishing if any check fails.

## Limitations

- Detailed industry wage series (e.g. restaurants, food manufacturing) need the detailed BLS establishment series, which are planned for a later phase, so supersector average hourly earnings are used as proxies.
- PPI values are revised for four months after release; the page tags them as preliminary until then.
- GitHub runs scheduled jobs on a best-effort basis, so a 15-minute run can start several minutes late. The page shows the real time of the last publisher call.
- Five World Bank series (wheat, soybeans, soybean oil, sugar, beef) are different benchmark quotes from the IMF series used before November 2026, so their history and signals differ somewhat. Aluminum, copper, nickel, corn and coffee are the same benchmarks.
- October 2025 is missing for CPI food away from home and egg prices (no collection during the federal shutdown); it is interpolated for calculations.

## Run it

```
pip install -r requirements.txt
export EIA_API_KEY=... CENSUS_API_KEY=... USDA_AMS_API_KEY=...   # free keys; BLS_API_KEY is optional
python run.py --all --rebuild  # call every publisher, recalculate, check and build
python run.py                  # later runs: only what is due
python collect.py --plan       # show what would be called right now, call nothing
python -m unittest discover tests
```

`run.py` chains `collect.py`, `analyze.py` (about 5 minutes; refits ~5,000 models), `verify_calcs.py`, `analyze_agency.py`, `verify_agency.py` and `build.py`, and skips the steps whose inputs did not change.

`.github/workflows/collect.yml` runs it every 15 minutes. Data is kept on the `data` branch, the site is published straight to GitHub Pages (Settings > Pages > Source: GitHub Actions), and the main branch holds code only.

## References

- Alquist, R., Kilian, L., & Vigfusson, R. J. (2013). Forecasting the price of oil. In *Handbook of Economic Forecasting* (Vol. 2A, pp. 427–507). Elsevier.
- Brown, G. W., Crabb, P. R., & Haushalter, D. (2006). Are firms successful at selective hedging? *Journal of Business*, 79(6), 2925–2949.
- Carter, D. A., Rogers, D. A., & Simkins, B. J. (2006). Does hedging affect firm value? Evidence from the US airline industry. *Financial Management*, 35(1), 53–86.
- Cashin, P., McDermott, C. J., & Scott, A. (2002). Booms and slumps in world commodity prices. *Journal of Development Economics*, 69(1), 277–296.
- Croushore, D., & Stark, T. (2001). A real-time data set for macroeconomists. *Journal of Econometrics*, 105(1), 111–130.
- Deaton, A., & Laroque, G. (1992). On the behaviour of commodity prices. *Review of Economic Studies*, 59(1), 1–23.
- Dickens, W. T., Goette, L., Groshen, E. L., Holden, S., Messina, J., Schweitzer, M. E., Turunen, J., & Ward, M. E. (2007). How wages change: Micro evidence from the International Wage Flexibility Project. *Journal of Economic Perspectives*, 21(2), 195–214.
- Federal Acquisition Regulation, 48 CFR 16.203, Fixed-price contracts with economic price adjustment. https://www.acquisition.gov/far/16.203-2
- Kilian, L. (2009). Not all oil price shocks are alike: Disentangling demand and supply shocks in the crude oil market. *American Economic Review*, 99(3), 1053–1069.
- Kraljic, P. (1983). Purchasing must become supply management. *Harvard Business Review*, 61(5), 109–117.
- Mandelbrot, B. (1963). The variation of certain speculative prices. *Journal of Business*, 36(4), 394–419.
- Martínez-de-Albéniz, V., & Simchi-Levi, D. (2005). A portfolio approach to procurement contracts. *Production and Operations Management*, 14(1), 90–114.
- Mena, C., van Hoek, R., & Christopher, M. (2021). *Leading Procurement Strategy: Driving Value Through the Supply Chain* (3rd ed.). Kogan Page.
- Montgomery, D. C. *Introduction to Statistical Quality Control*. Wiley.
- Stulz, R. M. (1996). Rethinking risk management. *Journal of Applied Corporate Finance*, 9(3), 8–25.
- U.S. Energy Information Administration. (2026). *Short-Term Energy Outlook*, November 2026, Table 2. https://www.eia.gov/outlooks/steo/
- Gardner, E. S., & McKenzie, E. (1985). Forecasting trends in time series. *Management Science*, 31(10), 1237–1246.
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts. https://otexts.com/fpp3/
- Rhoades, S. A. (1993). The Herfindahl-Hirschman Index. *Federal Reserve Bulletin*, 79(3), 188–189.
- U.S. Department of Justice & Federal Trade Commission. (2023). *Merger Guidelines*. https://www.justice.gov/atr/2023-merger-guidelines
- Meese, R. A., & Rogoff, K. (1983). Empirical exchange rate models of the seventies: Do they fit out of sample? *Journal of International Economics*, 14(1–2), 3–24.
- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International Journal of Forecasting*, 16(4), 437–450.
- Williams, W. H., & Goodman, M. L. (1971). A simple method for the construction of empirical confidence limits for economic forecasts. *Journal of the American Statistical Association*, 66(336), 752–754.

## Rights

© 2026 Dawson Wilhelmi. All rights reserved. The code is public so it can be read; it is not licensed for reuse. Data belongs to its publishers and is used under their terms, credited on each page.
