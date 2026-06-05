# Architecture — Commodity Intelligence Platform

## 1. Principles

1. **Config over code.** A commodity is data (JSON), not code. The engine is generic; behavior
   per commodity comes entirely from its config. Adding a commodity ≠ a deploy of new logic.
2. **Indicator-centric.** Everything is an *indicator*: a named time series with a source
   connector, a transform, a category (supply/demand/inventory/weather/macro/positioning/price),
   and a scoring rule. Sub-scores compose into category scores into a composite.
3. **Explainability first.** Every score and forecast carries its contributing factors. The
   platform must always answer "why" (Sections 10, 16, 17 depend on this).
4. **Compute / serve split.** Scheduled jobs ingest → compute scores/forecasts → write to DB.
   APIs read precomputed results. The UI is always fast.
5. **Graceful degradation.** Missing/paid feeds leave their indicator null; category scores
   renormalize over available indicators. Free-data MVP works day one.

## 2. The four layers

```
            ┌──────────────────────────────────────────────────────────────┐
 CONFIG     │  config/<symbol>.json  ──►  Config Registry (validated)       │
 LAYER      │  defines indicators, sources, weights, regions, seasonality   │
            └───────────────┬──────────────────────────────────────────────┘
                            │ drives
            ┌───────────────▼──────────────────────────────────────────────┐
 DATA &     │  Connector framework → raw observations                       │
 COMPUTE    │  EIA · USDA · CFTC(COT) · FRED · NOAA/Open-Meteo · Yahoo ·    │
 (workers)  │  Comtrade · LME/SHFE · AIS/freight(paid) · news RSS           │
            │        │                                                       │
            │        ▼  Feature/Indicator store (normalized, z/percentile)   │
            │  Scoring engine → 6 category scores → Composite Health 0-100   │
            │  Forecast engine (stat+ML ensemble) → bull/bear/neutral probs  │
            │  Correlation/lead-lag · Seasonality · Early-warning · Digital  │
            │  twin elasticities · News classifier (LLM)                     │
            └───────────────┬──────────────────────────────────────────────┘
                            │ writes
                    ┌───────▼────────┐
                    │  PostgreSQL    │   (TimescaleDB optional for series)
                    └───────┬────────┘
                            │ reads
            ┌───────────────▼──────────────────────────────────────────────┐
 API        │  FastAPI  /api/v1/commodities/{symbol}/{section}              │
            └───────────────┬──────────────────────────────────────────────┘
                            │ JSON
            ┌───────────────▼──────────────────────────────────────────────┐
 UI         │  Next.js · commodity dropdown · 18 sections render per config │
            │  Recharts + Mapbox · dark/light · Portfolio mode · Copilot    │
            └──────────────────────────────────────────────────────────────┘
```

## 3. The Indicator model (the abstraction that makes it generic)

Every input is an **Indicator**:

```
Indicator {
  key            "us_ending_stocks", "mine_production", "rainfall_anom", "usd_index"
  category       supply | demand | inventory | weather | macro | positioning | price
  source         connector id + params (e.g. {eia: {series_id: "..."}} )
  transform      raw | yoy | zscore | percentile | rolling_mean | anomaly_vs_normal
  direction      +1 | -1   (does a HIGH value push price up or down?)
  weight         contribution within its category (config)
  geography      optional: producing/consuming region(s) for weather & trade
  frequency      daily | weekly | monthly | quarterly | seasonal
}
```

The **scoring engine** is one function for all commodities:
`sub_score = direction × normalize(value)` → category_score = Σ(weight·sub_score) →
`composite = Σ(category_weight·category_score)` → mapped to **0–100 Health / Bullish Score**.
Only the *set of indicators and weights* changes per commodity — never the engine.

## 4. Backend module map

```
backend/app/
  core/            config (settings), db, logging, config_registry (loads+validates JSON)
  configs/         <symbol>.json commodity configs (the no-hardcode layer)
  connectors/      one module per data source, uniform interface:
                     base.py  eia.py  usda.py  cftc_cot.py  fred.py  comtrade.py
                     yahoo.py  weather.py(reuse)  lme.py  freight.py  news_rss.py
  ingest/          orchestrator: read config → run referenced connectors → raw_observations
  indicators/      builder: raw → normalized indicator_values (z/percentile/yoy…)
  scoring/         category scores + composite Health Score (generic, config-weighted)
  forecast/        datasets, models (stat+ML ensemble), probabilities per horizon
  analytics/       seasonality, correlation/lead-lag discovery, futures-curve, positioning
  twin/            digital-twin elasticity model (scenario → price impact)
  early_warning/   threshold/anomaly rule engine → alerts
  intel/           news classifier + sentiment (LLM), research copilot (LLM, grounded)
  scoring/scorecard.py  + portfolio.py (cross-commodity ranking)
  services/        scheduler (per-commodity cadence), cache
  api/             one router per section (overview, supply, demand, inventory, weather,
                     macro, tradeflow, futures, positioning, news, forecast, seasonality,
                     correlation, alerts, twin, copilot, scorecard, portfolio)
```

## 5. Folder structure (full)<a id="folder-structure"></a>

```
commodity-intel/
├── backend/
│   ├── app/                      (module map above)
│   │   ├── configs/
│   │   │   ├── _schema.json      JSON-Schema validating every commodity config
│   │   │   ├── cotton.json
│   │   │   ├── crude.json
│   │   │   ├── copper.json
│   │   │   └── ...               (one per commodity — add freely)
│   │   ├── core/ connectors/ ingest/ indicators/ scoring/ forecast/
│   │   ├── analytics/ twin/ early_warning/ intel/ services/ api/ models/
│   ├── requirements.txt
│   └── alembic/
├── frontend/
│   ├── app/
│   │   ├── (platform)/[symbol]/  dynamic route per commodity
│   │   │   ├── overview/ supply/ demand/ inventory/ weather/ macro/
│   │   │   ├── tradeflow/ futures/ positioning/ news/ forecast/
│   │   │   ├── seasonality/ correlations/ alerts/ twin/ copilot/ scorecard/
│   │   │   └── layout.tsx        commodity dropdown + section nav (config-driven)
│   │   ├── portfolio/            Section 18 cross-commodity
│   │   └── api/                  route handlers proxying interactive POSTs
│   ├── components/  (charts via Recharts, MapView via Mapbox, ui/, ScoreGauge…)
│   ├── lib/         api client, config types, theme
│   └── package.json
├── db/  DATABASE.sql
├── docs/ (this folder)
└── docker-compose.yml
```

## 6. Section → engine mapping (the 18 sections come from generic capabilities)

| Section | Powered by |
|---|---|
| 1 Overview | price connector + scoring (trend/fundamental/risk/composite) |
| 2 Supply / 3 Demand / 4 Inventory | indicators in those categories → category score |
| 5 Weather | weather connectors over config's producing regions → Weather Risk Index |
| 6 Macro | FRED/Yahoo macro indicators + correlation |
| 7 Trade Flow | Comtrade + (paid) AIS/freight → Mapbox map |
| 8 Futures | futures-curve analytics (contango/backwardation/spreads/roll) |
| 9 Positioning | CFTC COT → positioning extremes |
| 10 News | news connectors → LLM classifier → sentiment |
| 11 Forecast | forecast engine → bull/bear/neutral probs |
| 12 Seasonality | analytics/seasonality |
| 13 Correlation | analytics/correlation lead-lag discovery |
| 14 Early Warning | early_warning rule engine over indicators |
| 15 Digital Twin | twin elasticities (config-defined) |
| 16 Copilot | intel/copilot (LLM grounded on all the above) |
| 17 Scorecard | scoring/scorecard (the 6 category scores → Health 0-100) |
| 18 Portfolio | scoring across all configured commodities, ranked |

## 7. Per-commodity scheduling
The scheduler reads each config's indicator frequencies and pulls accordingly (e.g. EIA weekly
on Wed, COT Fri, USDA monthly WASDE, weather daily, prices daily). One generic scheduler;
cadence is data, not code.
