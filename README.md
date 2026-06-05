# RAINMUMBAI Terminal

A hedge-fund-style weather research & trading terminal for the **NCDEX RAINMUMBAI** rainfall
derivative. It ingests open meteorological + climate-driver data, builds a feature store,
trains an ensemble of forecasting models, and produces a daily **probabilistic rainfall
forecast, a contract fair value, and a trading signal** — with explainable reasoning.

> The product is not a weather display. It is a *signal generator*. Every module exists to
> sharpen one daily output: **is RAINMUMBAI mispriced, and in which direction is the forecast
> likely to be revised?**

---

## What it produces every day

1. Probabilistic rainfall forecast (1/3/7/15/30-day + cumulative seasonal)
2. Forecast confidence score
3. **Forecast revision probability** (the primary alpha — Module 7)
4. Expected seasonal rainfall + deviation from climatology
5. RAINMUMBAI fair value vs. market price → expected mispricing
6. Trading signal: Strong Buy / Buy / Neutral / Sell / Strong Sell
7. Top 5 bullish factors + Top 5 bearish factors (explainable)

## Tech stack

| Layer        | Choice |
|--------------|--------|
| Frontend     | Next.js (App Router), React, TailwindCSS, shadcn/ui, Plotly + Apache ECharts |
| Backend API  | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database     | PostgreSQL (+ optional TimescaleDB extension) |
| Analytics/ML | pandas, NumPy, scikit-learn, XGBoost, LightGBM, Prophet, PyTorch (LSTM/Transformer) |
| Orchestration| APScheduler (local) → Cron / Vercel Cron + a worker (prod) |
| AI Copilot   | Anthropic Claude API (pluggable) |

## Repository layout

```
rainmumbai-terminal/
├── backend/            FastAPI app, ingestion, feature store, ML, signals
│   └── app/
│       ├── core/       config, db session, logging
│       ├── ingest/     data-source connectors (Open-Meteo, NASA POWER, NOAA, BoM...)
│       ├── models/     SQLAlchemy ORM + Pydantic schemas + ML model wrappers
│       ├── features/   feature engineering / feature store builders
│       ├── ml/         training, evaluation, leaderboard, registry
│       ├── signals/    probability engine, revision engine, fair value, signal engine
│       ├── api/        FastAPI routers (one per dashboard module)
│       └── services/   scheduler, cache, copilot
├── frontend/           Next.js dashboard (one route group per module)
├── db/                 schema.sql + seed data
├── docs/               DATA_SOURCES.md, API.md, ARCHITECTURE.md
├── ARCHITECTURE.md     full system design
└── ROADMAP.md          phased implementation plan (start here)
```

## Quick start (after Phase 0 scaffolding)

```bash
# 1. Database
docker compose up -d db                # Postgres on :5432
psql "$DATABASE_URL" -f db/schema.sql  # create tables

# 2. Backend
cd backend && python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt
cp ../.env.example .env                 # fill in keys
python -m app.ingest.backfill           # backfill 30y of weather + climate drivers
uvicorn app.main:app --reload           # API on :8000, docs at /docs

# 3. Frontend
cd ../frontend && npm install && npm run dev   # dashboard on :3000
```

See **[ROADMAP.md](ROADMAP.md)** for the build order and **[ARCHITECTURE.md](ARCHITECTURE.md)**
for the full design.
