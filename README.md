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
| Trucking & freight | Diesel; PPI truckload, rail, rubber; Cass shipments and expenditures; transportation wages |
| Airlines, air cargo & ocean | Jet fuel; PPI air freight, passenger air, deep sea freight; transportation wages; EUR, CNY |
| Agriculture | PPI fertilizer, ag chemicals, farm machinery; diesel; corn, soybeans, wheat |
| Oil & gas | WTI crude, Henry Hub gas; PPI drilling, oilfield services, steel pipe & tube; mining & logging wages |
| Data centers | PPI industrial power, computers, semiconductors, transformers, HVAC equipment, wire & cable, data hosting; construction wages |

Series IDs, names, units and publishers are in `series.py`.

## Data publishers

Credited to the original publisher; FRED (Federal Reserve Bank of St. Louis) is the delivery layer.

- U.S. Bureau of Labor Statistics: Producer Price Index, Consumer Price Index and average price data, Current Employment Statistics (average hourly earnings)
- U.S. Energy Information Administration: WTI crude, Henry Hub natural gas, US retail diesel, US Gulf Coast jet fuel
- International Monetary Fund: Primary Commodity Prices (metals, grains, softs, beef)
- Board of Governors of the Federal Reserve System: H.10 foreign exchange rates
- Cass Information Systems: Cass Freight Index (shipments and expenditures)

## Method

- **Cost impact and signals.** Each % change is multiplied by its direction (+1 for prices; −1 for foreign currency per USD, because a stronger dollar makes imports cheaper; USD per EUR stays +1). Signals (Alert, Watch, Opportunity, Stable) use 3- and 12-month cost impact with thresholds per group in `series.py`. Industry pressure is the **median** driver.
- **Forecast.** Damped additive-trend exponential smoothing on log levels (Gardner & McKenzie, 1985; Hyndman & Athanasopoulos, 2021), via statsmodels. Benchmark: naive (no change).
- **Backtest.** Rolling origin (Tashman, 2000): refit every month from Dec 2020, forecast 1–6 months ahead, score MAPE from Jan 2022. The published forecast uses whichever of model or naive had the lower average MAPE. Naive often wins for commodities and currencies, consistent with Meese & Rogoff (1983).
- **80% range.** 10th–90th percentile of the chosen method's past log errors at each horizon (empirical prediction intervals; Williams & Goodman, 1971). The hit rate is tested out of sample: since Jan 2023, each range is rebuilt only from errors known at that date.
- **Lead/lag.** Correlation of monthly log changes, X at t−k vs Y at t, k = 0…6; a pair is listed when the best lagged |r| beats the same-month |r| and exceeds 2/√n. Descriptive, not causal.
- **Correlation.** Pearson correlation of 12-month % changes since Jan 2019.
- **Escalation calculator.** P₁ = P₀ × [F + Σ wᵢ × Iᵢ(t₁)/Iᵢ(t₀)], the standard index-linked price adjustment, with fixed share F = 1 − Σwᵢ. Future months use forecast midpoints, with an all-components-at-range-edge stress test.

## Data quality checks

- Every value (80 series, Jan 2018–Oct 2026) was cross-checked against FRED's own annual averages for 2018–2025 and quarterly averages through 2026 Q3: 640 annual and 880 quarterly comparisons. Three 2026 Q1 energy flags (WTI, jet fuel, diesel) came from daily vs. monthly weighting during the March 2026 price spike; the monthly values were re-pulled and match FRED exactly.
- `verify_calcs.py` independently recomputes every % change, signal, range, naive backtest, industry median, correlation and lead/lag coefficient, and refits the model for a sample of series. The daily workflow stops before publishing if any check fails.

## Limitations

- Detailed industry wage series (e.g. restaurants, food manufacturing) are not on FRED, so supersector average hourly earnings are used as proxies.
- IMF commodity prices run about one month behind BLS data. PPI values are revised for four months after release.
- October 2025 is missing for CPI food away from home and egg prices (no collection during the federal shutdown); it is interpolated for calculations.

## Run it

```
pip install -r requirements.txt
export FRED_API_KEY=...        # free key from https://fred.stlouisfed.org/docs/api/api_key.html
python fetch_data.py           # data/raw/*.csv
python analyze.py              # data/analytics.json (about 5 minutes; refits ~5,000 models)
python verify_calcs.py         # independent checks, exits non-zero on any mismatch
python build.py                # index.html + <industry>/index.html
```

`.github/workflows/update.yml` runs the same steps daily and needs the `FRED_API_KEY` repository secret.

## References

- Gardner, E. S., & McKenzie, E. (1985). Forecasting trends in time series. *Management Science*, 31(10), 1237–1246.
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts. https://otexts.com/fpp3/
- Meese, R. A., & Rogoff, K. (1983). Empirical exchange rate models of the seventies: Do they fit out of sample? *Journal of International Economics*, 14(1–2), 3–24.
- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International Journal of Forecasting*, 16(4), 437–450.
- Williams, W. H., & Goodman, M. L. (1971). A simple method for the construction of empirical confidence limits for economic forecasts. *Journal of the American Statistical Association*, 66(336), 752–754.
