# Commodity Intelligence Platform (CIP)

A next-generation, **config-driven** commodity intelligence & forecasting platform.
Add *any* commodity — agriculture, metals, energy — through a JSON config. **No hardcoding.**

> It doesn't show prices. It answers:
> **Why is this commodity moving? · What happens next? · What are the leading indicators? ·
> What are the hidden risks? · What's the probability of bull / bear / neutral?**

It reasons through seven professional lenses simultaneously — **trader, quant, economist,
meteorologist, supply-chain analyst, agronomist, data scientist** — and fuses them into one
explainable **Commodity Health Score (0–100)** plus probabilistic forecasts.

---

## The core idea: one engine, many commodities

Every commodity is a **JSON config** (`config/<symbol>.json`) describing its identity, contract
specs, producing/consuming regions, the *indicators that matter for it*, where each indicator's
data comes from, how indicators roll into category scores, and its seasonality & forecast setup.

The platform is a **generic engine** that reads the config and:
1. ingests only the data sources that config references,
2. computes normalized sub-scores → 6 category scores → composite,
3. renders only the dashboard sections relevant to that commodity
   (a metal hides "acreage/sowing"; cotton shows it),
4. produces bull/bear/neutral probabilities and an explainable scorecard.

Adding "Aluminium" or "Coffee" = drop in a new JSON file + (if needed) one new data connector.

---

## What it reuses from the existing terminal

This generalizes the commodity module already built (Phase C1) and reuses proven infrastructure:

| Already built | Reused as |
|---|---|
| Weather pipeline (Open-Meteo, NASA POWER, NOAA ONI, BoM IOD/MJO) | **Section 5 Weather & Climate Intelligence** (per-commodity producing regions) |
| Commodity price pipeline (Yahoo Finance OHLCV) | **Section 1 Overview** + Futures/Technicals |
| Scoring / probability / signal patterns | **Scoring engine + Section 11 AI Prediction + 17 Scorecard** |
| ML harness (sklearn/XGBoost/LightGBM/Prophet/LSTM/Transformer) | **Section 11 forecasting** |
| Local LLM (Ollama) copilot + news digest | **Section 10 News Engine + 16 Research Copilot** |
| Scheduler, dark/light theme, charts, DB, ngrok hosting | platform-wide |

---

## Deliverables in this folder (your 10 requested outputs)

| # | Deliverable | File |
|---|-------------|------|
| 1 | Complete architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 2 | Database schema | [DATABASE.sql](DATABASE.sql) |
| 3 | Folder structure | [ARCHITECTURE.md](ARCHITECTURE.md#folder-structure) |
| 4 | API design | [API.md](API.md) |
| 5 | UI wireframes | [WIREFRAMES.md](WIREFRAMES.md) |
| 6 | Forecasting framework | [FORECASTING.md](FORECASTING.md) |
| 7 | ML model suggestions | [FORECASTING.md](FORECASTING.md#ml-models) |
| 8 | Data source mapping | [DATA_SOURCES.md](DATA_SOURCES.md) |
| 9 | Deployment plan | [DEPLOYMENT.md](DEPLOYMENT.md) |
| 10 | Implementation roadmap | [ROADMAP.md](ROADMAP.md) |
| ★ | **Commodity config spec (the heart)** | [COMMODITY_CONFIG.md](COMMODITY_CONFIG.md) + [config/cotton.json](config/cotton.json) |
| 📕 | **Domain smarts from Jim Rogers' *Hot Commodities*** (supply-cycle intelligence) | [ROGERS_INSIGHTS.md](ROGERS_INSIGHTS.md) |

## Tech stack (your spec)
Next.js + React + TypeScript + Tailwind + **Recharts** + **Mapbox** (frontend) · Python + FastAPI
(backend) · PostgreSQL · pandas/scikit-learn/XGBoost/LightGBM/Prophet/PyTorch · local LLM (Ollama)
or Claude API · Vercel / Railway / Render ready.

## Honest framing
This is a **hedge-fund-grade platform** — a multi-month build. The blueprint is complete and the
engine is generic; we deliver it **phase by phase** (see ROADMAP). Many premium data feeds (vessel
AIS, port congestion, real-time freight, satellite soil moisture) are **paid or hard** — every
indicator is tagged with access/cost in [DATA_SOURCES.md](DATA_SOURCES.md), and the config lets you
start with free sources and upgrade later without code changes.
