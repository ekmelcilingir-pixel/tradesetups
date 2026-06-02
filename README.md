# Tradesetups — daily auto-generated swing-trade report

A small pipeline that, **every weekday**, scans your portfolio, detects swing-trade
setups, has **Claude** write the narrative, renders a dark-theme HTML report, and
saves it as a **new dated row** that your Portfolio Platform page lists. No server to
run — it lives in GitHub Actions and commits the results back to the repo.

```
GitHub Actions (cron, weekdays)
        │
        ▼
scripts/generate_report.py
   1. portfolio.json ──────────────► holdings to scan
   2. fetch_data.py  (Yahoo daily candles, ~6 mo; FMP optional for quote)
   3. detect_setups.py (EMA/RSI/ATR → Pullback / Bull Flag / Breakout / Bounce, top 5)
   4. Claude API  (writes trigger / playbook / in-short / validity, returns JSON)
   5. render.py   (master dark-theme HTML, inline SVG mini-charts)
        │
        ▼
reports/tradesetups-YYYY-MM-DD-*.html   +   reports/manifest.json
        │  (committed by the workflow)
        ▼
Portfolio_Platform_EN.html  ──fetch(manifest)──►  one row per day, "Open →" loads that day's report
```

## What you get
- `scripts/` — the generator (data fetch, indicators, setup detection, renderer, orchestrator)
- `templates/` — the report CSS + SVG chart renderer (the master format)
- `.github/workflows/daily-tradesetups.yml` — the daily cron job
- `portfolio.json` — the holdings list you scan (edit freely)
- `reports/manifest.json` — the index the front-end reads

## Setup (one time)
1. Create a GitHub repo and push this folder into it.
2. **Settings → Secrets and variables → Actions → New repository secret**
   - `ANTHROPIC_API_KEY` — required
   - `FMP_API_KEY` — optional (only used for the latest quote)
3. (Optional) **Settings → Pages** → deploy from the `main` branch root, so reports are
   served at `https://<user>.github.io/<repo>/reports/...`.
4. In `Portfolio_Platform_EN.html`, set the live source near the top of the reports script:
   ```js
   var MANIFEST_URL='https://<user>.github.io/<repo>/reports/manifest.json';
   ```
   Leave it empty (`''`) to keep the offline demo (localStorage) behaviour.
5. The workflow runs weekdays at **11:30 UTC** (edit the `cron`), or run it manually from
   the **Actions** tab. Each run commits a new report + updates the manifest.

## Run locally
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/generate_report.py
```
Output lands in `reports/` and `manifest.json` is updated.

## Tuning
- **Which tickers** → edit `portfolio.json` (or replace it with a live pull from your
  `/api/portfolio`).
- **Setup logic & thresholds** → `scripts/detect_setups.py` (RSI bands, volume multiple,
  ATR multiples for stops/targets). This is a transparent baseline, not a guaranteed edge.
- **Model** → `MODEL` env (default `claude-sonnet-4-6`; use a stronger model for richer prose).
- **$ cost column** → set `PRICE_IN_PER_MTOK` / `PRICE_OUT_PER_MTOK` env to show estimated
  cost in the manifest; otherwise it shows `—`.

## Notes / limitations
- Yahoo's chart endpoint is unofficial and free; if it rate-limits, add retries/back-off
  or swap in a paid history source. The FMP **free** plan does not provide historical EOD.
- The report is **informational, not investment advice**. Every setup states a stop —
  honour it; size positions to risk ~1–2% of the portfolio.
- The front-end resolves each report URL **relative to** `MANIFEST_URL`, so keeping the
  reports next to `manifest.json` (as the pipeline does) "just works".
