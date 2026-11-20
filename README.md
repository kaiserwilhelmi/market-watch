# Procurement Market Watch

A self-updating dashboard that tracks the cost drivers behind an office-supply buyer's prices (paper, packaging, plastic resins, steel, trucking, diesel and two currencies) and flags when to act: **Alert**, **Watch**, **Opportunity** or **Stable**, each with a recommended buyer response.

Data comes from the Federal Reserve Bank of St. Louis (FRED): BLS producer price indexes, EIA diesel prices and Federal Reserve exchange rates. No API key needed.

## How it updates
A GitHub Action (`.github/workflows/update.yml`) runs every morning:
1. `fetch_data.py` downloads the latest data for each series into `data/raw/`
2. `build.py` calculates 1-, 3- and 12-month changes, assigns signals, and rebuilds `index.html`
3. The changes are committed, and GitHub Pages republishes the site

If a download fails, the previous data is kept so the page never breaks.

## Setup
1. Create a public repository and upload everything in this folder, **including the hidden `.github` folder**.
2. **Settings → Pages**: deploy from branch `main`, folder `/ (root)`.
3. **Settings → Actions → General → Workflow permissions**: choose **Read and write permissions** and save.
4. **Actions** tab → *Update market data* → **Run workflow** to test it once.

## Customize
- Add or remove series in `series.py` (any FRED series ID works).
- Adjust signal thresholds in `series.py` (`THRESHOLDS`).

## Files
| File | Purpose |
|---|---|
| `index.html` | The dashboard (single self-contained page) |
| `series.py` | Series list, FRED URLs, signal thresholds |
| `fetch_data.py` | Downloads data (standard library only) |
| `build.py` | Calculates signals, writes `data/market.json`, embeds data into `index.html` |
| `template.html` | Dashboard source |
| `data/raw/*.csv` | Raw monthly data per series |

Signals are illustrative guidance, not financial advice.
