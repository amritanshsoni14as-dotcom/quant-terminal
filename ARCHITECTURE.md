# System Architecture — RAINMUMBAI Terminal

## 1. Design principles

1. **Signal-first.** Every module feeds one daily decision: trade RAINMUMBAI or not. UI is a
   research terminal, not a weather widget.
2. **Degrade gracefully.** Each data source is optional. Missing ECMWF/NCDEX data must not
   break the pipeline — the system runs on free data and improves as premium feeds are added.
3. **Reproducible & versioned.** Every forecast is stored with the model version, feature
   snapshot, and inputs that produced it. This is what makes the *forecast revision* signal
   (Module 7) possible — you cannot measure a revision without a versioned history of forecasts.
4. **Separation of compute and serving.** Heavy jobs (ingest, training, daily forecast) run on
   a schedule and **write results to Postgres**. The API only *reads* precomputed results, so
   the dashboard is always fast.

## 2. High-level data flow

```
            ┌─────────────────────────────────────────────────────────┐
            │                  SCHEDULED JOBS (worker)                  │
            │                                                           │
 EXTERNAL   │  ingest →  feature store →  ML train/predict →  signals   │
 SOURCES ──►│  (raw)     (engineered)     (forecasts)        (fair val, │──┐
            │                                                 revision,  │  │
            │                                                 signal)    │  │
            └─────────────────────────────────────────────────────────┘  │
                                                                          ▼
   Open-Meteo, NASA POWER, NOAA CPC (ONI),                       ┌──────────────┐
   BoM (IOD/MJO), IMD bulletins, NCDEX CSV,           writes →   │  PostgreSQL  │
   news/reports (Module 11)                                      └──────┬───────┘
                                                                        │ reads
                                                                        ▼
                                                          ┌──────────────────────┐
                                                          │   FastAPI (read-only) │
                                                          │   /api/v1/* per module│
                                                          └──────────┬────────────┘
                                                                     │ JSON
                                                                     ▼
                                                          ┌──────────────────────┐
                                                          │  Next.js dashboard    │
                                                          │  (12 module routes)   │
                                                          └───────────────────────┘
```

## 3. Backend module map

| App package        | Responsibility | Dashboard module(s) |
|--------------------|----------------|---------------------|
| `ingest/`          | Source connectors → `raw_*` tables. Idempotent upserts. | feeds all |
| `features/`        | Build `features_daily` from raw tables (lags, rolling sums, anomalies, monsoon progress, driver alignment) | 5, 6 |
| `ml/`              | Train/evaluate/register models; horizon-specific forecasts; leaderboard | 6 |
| `signals/probability.py` | Empirical + Bayesian probability of above/below normal & threshold bins | 8 |
| `signals/revision.py`    | Predict whether next forecast revises up/down, expected size & market impact | **7** |
| `signals/fairvalue.py`   | Map seasonal rainfall distribution → contract payoff → fair value | 2 |
| `signals/engine.py`      | Combine drivers + model consensus + revision + mispricing → 5-state signal | 9 |
| `signals/scenarios.py`   | Conditional rainfall distributions under ENSO/IOD/monsoon-timing scenarios | 10 |
| `services/scheduler.py`  | APScheduler jobs (ingest daily, retrain weekly, forecast daily) | — |
| `services/copilot.py`    | Claude-API research assistant grounded on the feature store + signals | 12 |
| `api/`             | One FastAPI router per module; read-only views over Postgres | all |

## 4. The core insight: Forecast Revision Engine (Module 7)

Rainfall derivatives are repriced not by *today's rain* but by *how the forecast for the
season changes*. So the alpha is in predicting **forecast revisions**, not rainfall levels.

Implementation:
- Every daily run stores the full forecast vector in `forecasts` (versioned).
- `forecast_revisions` is computed as the diff between consecutive runs for the same target.
- We train a classifier on `(current drivers, recent revision momentum, model disagreement,
  MJO phase transition, SST anomaly trend)` → **P(next revision is upward)** + expected size.
- This probability is the dominant input to the Trading Signal Engine (Module 9).

## 5. Fair value model (Module 2)

NCDEX rainfall contracts settle against a rainfall index over a window. General approach:
1. Estimate the **seasonal cumulative-rainfall distribution** (from Module 8 + scenarios).
2. Map the distribution through the **contract payoff function** (configurable per contract spec
   in `contract_specs`) → expected settlement → discounted **fair value**.
3. `mispricing = fair_value − market_price`. Feeds the signal engine.

Because the exact tick/strike/index spec varies by contract, the payoff function is a pluggable
config object, not hard-coded.

## 6. ML design (Module 6)

- **Targets:** 1/3/7/15/30-day rainfall + cumulative seasonal, as both regression and
  above/below-normal classification.
- **Models:** LinearReg, RandomForest, XGBoost, LightGBM, Prophet, LSTM, Transformer.
- **Validation:** strict time-series CV (expanding window, no leakage). Metrics: RMSE, MAE,
  hit rate, directional accuracy → `model_runs` table → leaderboard endpoint.
- **Registry:** best model per horizon is promoted; `forecasts` records which model_version
  produced each number.
- **Phasing:** ship XGBoost/LightGBM/Prophet first (high signal, low cost). LSTM/Transformer
  are Phase 4 once the data + harness are proven.

## 7. Frontend architecture

- Next.js App Router, one route per module under `app/(modules)/`.
- Server Components fetch from FastAPI; charts (Plotly/ECharts) render client-side.
- A shared `lib/api.ts` typed client mirrors the OpenAPI schema FastAPI emits.
- A persistent **"Daily Brief"** header shows the 8 final outputs on every page.
- shadcn/ui for primitives; dark "terminal" theme by default.

## 8. Deployment path

- **Local (Phase 0–2):** docker-compose for Postgres; uvicorn + next dev; APScheduler in-process.
- **Vercel (later):** Next.js → Vercel. FastAPI → a container host (Render/Fly/Railway) or
  Vercel Python functions for light endpoints. Postgres → Neon/Supabase. Scheduled jobs →
  Vercel Cron hitting a protected `/jobs/*` route, or a small always-on worker.
- Secrets via env vars; never commit keys. `.env.example` documents every variable.

## 9. Folder structure (full)

```
backend/app/
  main.py                 FastAPI app factory + router registration
  core/
    config.py             pydantic-settings; reads .env
    db.py                 SQLAlchemy engine/session
    logging.py
  ingest/
    base.py               connector interface + upsert helpers
    open_meteo.py         daily weather (historical + forecast) for Mumbai
    nasa_power.py         40y daily reanalysis backfill
    noaa_oni.py           ENSO / ONI index
    bom_iod.py            IOD (DMI) + MJO (RMM) indices
    imd.py                IMD bulletin scraper (best-effort)
    ncdex.py              RAINMUMBAI contract CSV/manual ingest
    backfill.py           one-shot 30y backfill orchestrator
  features/
    builder.py            assemble features_daily
    monsoon.py            monsoon onset/progress logic
  ml/
    datasets.py           target/feature assembly per horizon
    train.py              per-model trainers
    evaluate.py           TS-CV metrics + leaderboard writer
    registry.py           best-model promotion
    predict.py            daily forecast writer
  signals/
    probability.py        Module 8 (Bayesian)
    revision.py           Module 7
    fairvalue.py          Module 2
    engine.py             Module 9
    scenarios.py          Module 10
  services/
    scheduler.py          APScheduler job defs
    copilot.py            Module 12
    news.py               Module 11 ingest + AI summarize
  api/
    weather.py modules.py derivative.py drivers.py research.py
    ml.py revision.py probability.py signal.py scenarios.py copilot.py brief.py
```
