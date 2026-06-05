# Implementation Roadmap

Build order is chosen to reach a **working daily signal as fast as possible**, then deepen.
Each phase ends with something runnable. Modules from the spec are mapped to phases.

Legend: ✅ delivers signal · 🧱 infra · 🔬 research depth · 🎀 polish

---

## Phase 0 — Foundation (scaffolding) 🧱
**Goal: empty but runnable full-stack skeleton.**
- [ ] `docker-compose.yml` (Postgres), apply `db/schema.sql`
- [ ] FastAPI app factory, `core/config.py`, `core/db.py`, health route
- [ ] Next.js + Tailwind + shadcn/ui shell, dark terminal theme, sidebar with 12 module routes
- [ ] Typed API client `lib/api.ts`, "Daily Brief" header component (empty state)
- **Exit:** `localhost:3000` renders the shell; `localhost:8000/docs` serves OpenAPI.

## Phase 1 — Data backbone (Modules 1, 5 partial) 🧱✅
**Goal: 30 years of Mumbai weather + climate drivers in Postgres.**
- [ ] `ingest/open_meteo.py` (historical + forecast), `ingest/nasa_power.py` (40y backfill)
- [ ] `ingest/noaa_oni.py`, `ingest/bom_iod.py` (IOD + MJO)
- [ ] `ingest/backfill.py` orchestrator; `features/builder.py`; `climatology` table populated
- [ ] **Module 1 — Weather Command Center**: today/weekly/monthly/seasonal, deviation %,
      historical average, monsoon progress + the 4 charts
- **Exit:** Module 1 fully live on real data.

## Phase 2 — Probability + Fair Value + first Signal (Modules 8, 2, 9 v1) ✅
**Goal: a real (if simple) daily trading signal end-to-end.**
- [ ] `signals/probability.py` — empirical + Bayesian above/below/threshold probabilities → Module 8
- [ ] `contract_specs` seeded with RAINMUMBAI payoff config; `ingest/ncdex.py` CSV importer
- [ ] `signals/fairvalue.py` → Module 2 (fair value, market vs model, mispricing)
- [ ] `signals/engine.py` v1 (rule-based: drivers + probability + mispricing) → Module 9
- [ ] `daily_brief` populated; Daily Brief header shows all 8 final outputs
- **Exit:** dashboard emits Strong Buy…Strong Sell with explainable components.

## Phase 3 — ML Lab + Forecast Revision Engine (Modules 6, 7) ✅🔬
**Goal: model-driven forecasts and the primary alpha.**
- [ ] `ml/datasets.py`, `ml/train.py` (LinearReg, RandomForest, XGBoost, LightGBM, Prophet)
- [ ] Time-series CV in `ml/evaluate.py`; leaderboard endpoint → Module 6
- [ ] `ml/predict.py` writes versioned `forecasts`; champion promotion in `ml/registry.py`
- [ ] `signals/revision.py` — compute `forecast_revisions`, train revision classifier → Module 7
- [ ] Wire revision probability + model consensus into signal engine v2
- **Exit:** Modules 6 & 7 live; signal now driven by model consensus + revision probability.

## Phase 4 — Deep learning + Drivers + Scenarios (Modules 3, 10, 6 deep) 🔬
- [ ] LSTM + Transformer trainers (PyTorch) added to the leaderboard
- [ ] **Module 3 — Monsoon Intelligence**: ENSO/IOD/MJO panels w/ historical relationships,
      SST anomalies, regime classification (charts; maps where data permits)
- [ ] `signals/scenarios.py` — conditional distributions → Module 10 (7 scenarios)

## Phase 5 — Research Lab depth + Alt data + Copilot (Modules 5 deep, 11, 12) 🔬🎀
- [ ] Module 5 full: correlation matrix, lag/lead analysis, regime/seasonality,
      extreme/drought/flood event analysis
- [ ] `services/news.py` — ingest IMD bulletins / news / reports + AI summarize → Module 11
- [ ] `services/copilot.py` — Claude-API assistant grounded on feature store + signals → Module 12

## Phase 6 — Satellite + Maps + Automation + Deploy (Module 4, ops) 🎀🧱
- [ ] **Module 4 — Satellite Intelligence**: NASA/NOAA imagery tiles, cloud/storm/rain scores
- [ ] Wind/humidity/pressure maps in Module 3
- [ ] `services/scheduler.py` — daily ingest/forecast, weekly retrain (APScheduler)
- [ ] Vercel deploy (frontend) + container host (API) + Neon/Supabase Postgres + Cron

---

## Effort & dependency notes (honest)
- **Free data covers** Modules 1, 3 (indices), 5, 6, 8 fully. Open-Meteo + NASA POWER + NOAA + BoM.
- **Needs your input/keys:** NCDEX contract history (CSV/manual), ECMWF (paid) for Module 4 depth,
  Anthropic API key for Module 12, news API for Module 11.
- **Heaviest:** LSTM/Transformer (Phase 4) and satellite imagery (Phase 6). Deliberately last —
  they add the least marginal signal per hour of work and depend on the data backbone being solid.
- **Recommended MVP = Phases 0–3.** That alone is a real research terminal with a daily signal.

## Suggested first cut
If you want to see value quickly, I'd build **Phase 0 → Phase 1 → Module 1** first, so you have a
live weather command center on 30 years of real Mumbai data, then layer probability + fair value +
signal (Phase 2).
