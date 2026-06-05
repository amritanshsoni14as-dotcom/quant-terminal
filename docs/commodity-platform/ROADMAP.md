# Implementation Roadmap

Built phase-by-phase; each phase is runnable and delivers value. Reuses the existing terminal's
infrastructure heavily (marked ♻️). Legend: ✅ signal value · 🧱 infra · 🔬 depth · 🎀 polish.

## Phase 0 — Config-driven foundation 🧱
- `configs/_schema.json` + **config registry** (load + validate every `<symbol>.json`).
- DB from `DATABASE.sql`; ORM (commodity-agnostic).
- **Connector framework** (uniform interface) ♻️ from existing ingest base.
- **Generic scoring engine** (sub-score → category → composite Health 0-100).
- Next.js shell: commodity dropdown + config-driven section nav + Health bar + dark/light ♻️.
- **Exit:** add a JSON → it appears in the dropdown with an (empty) scaffold.

## Phase 1 — Overview + Scorecard MVP (free data) ✅
- Yahoo price connector ♻️ (we already load gold/silver/copper/crude/natgas).
- Indicators: price + a few free ones (USD index via FRED, COT via CFTC).
- **Section 1 Overview** (spot, %changes, vol, percentile, 52w, trend/risk/composite scores) +
  **Section 17 Scorecard** (6 category gauges → Health 0-100, with whatever indicators exist).
- Seed configs: **CRUDE** (richest free data via EIA), **COPPER**, **GOLD**, **COTTON**.
- **Exit:** pick a commodity → see price + an explainable Health Score.

## Phase 2 — Supply / Demand / Inventory + indices ✅🔬
- Connectors: **EIA** (energy: stocks, production, refinery), **USDA NASS/PSD** (ag: acreage,
  condition, ending stocks, stocks-to-use), **FRED** (PMI, IP).
- **Sections 2/3/4** with Supply Tightness, Demand Strength, Inventory Stress indices.
- Real category scores feeding the composite.
- **Exit:** "why is it moving" answered fundamentally for crude & cotton.

## Phase 3 — Weather + Macro + Seasonality + Correlation 🔬
- **Section 5 Weather** ♻️ (Open-Meteo/NASA/NOAA over each config's producing regions) +
  Weather Risk Index + **Mapbox** choropleth.
- **Section 6 Macro** (FRED + correlations). **Section 12 Seasonality**. **Section 13 Correlation
  discovery** (lead/lag, auto-surface hidden indicators) ♻️ from research-lab patterns.
- **Exit:** weather-driven ag commodities light up; lead indicators discovered.

## Phase 4 — Forecast + Futures + Positioning ✅🔬
- **Section 11 Forecast** engine ♻️ (XGBoost/LightGBM/Prophet ensemble → bull/bear/neutral probs
  per horizon, calibrated). **Section 8 Futures** curve (contango/backwardation/spreads/roll).
  **Section 9 Positioning** (CFTC COT + extremes).
- **Exit:** "what happens next" with probabilities + curve/positioning context.

## Phase 5 — News + Copilot + Early Warning 🎀✅
- **Section 10 News** (Google News/GDELT → LLM classify into supply/demand/weather/geo/policy/
  currency/logistics + sentiment) ♻️. **Section 16 Copilot** ♻️ grounded on all sections.
  **Section 14 Early-Warning** rule engine over indicators → alerts.
- **Exit:** ask "why is cotton rising?" and get an evidence-backed answer; alerts fire.

## Phase 6 — Trade Flow + Digital Twin + Portfolio 🔬🎀
- **Section 7 Trade Flow** (UN Comtrade + Mapbox arcs; freight proxy). **Section 15 Digital Twin**
  (elasticity simulator → price impact waterfall). **Section 18 Portfolio** (rank all commodities).
- **Exit:** cross-commodity ranking + scenario simulation.

## Phase 7 — Depth + premium feeds + cloud 🔬🧱
- Deep learning (TFT/LSTM/N-BEATS) added to the leaderboard where data depth justifies.
- Premium connectors (LME full, AIS/freight, intraday curve, broker/MCX) — config-swapped.
- Conformal calibration, backtesting harness, SHAP attribution into Copilot.
- Deploy: Vercel + Railway/Render + Neon (see DEPLOYMENT.md).

## Suggested first build
**Phase 0 → 1 → 2 for CRUDE first.** Crude has the best *free* fundamental data (EIA weekly:
stocks, production, refinery runs, Cushing, SPR) so it most fully exercises the Supply/Demand/
Inventory engine and proves the config-driven design end-to-end. Cotton then showcases the
weather + USDA + seasonality strengths we already have infrastructure for.

## Effort & honesty
- Phases 0–2 = a genuinely useful multi-commodity terminal on free data (overview, fundamentals,
  scorecard) — the achievable near-term MVP.
- Phases 3–6 add the differentiated intelligence (weather, forecast, news, copilot, twin, portfolio).
- Phase 7 is the "hedge-fund-grade" long tail (deep models, paid feeds, full cloud).
- Hardest/paid dependencies: LME stocks, AIS/freight/port congestion, intraday curve, some PMIs.
  All are isolated behind connectors + config so the platform never blocks on them.
