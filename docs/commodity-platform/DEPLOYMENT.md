# Deployment Plan

## Topology
```
Next.js (frontend) ──► FastAPI (backend) ──► PostgreSQL
                              ▲                   ▲
              scheduler/worker (ingest+score+forecast)   local LLM (Ollama) or Claude API
```

## Local (dev / self-host, like the current terminal)
- Postgres via docker-compose (or SQLite for instant dev via the same ORM).
- `uvicorn app.main:app` (in-process APScheduler for ingest/score/forecast).
- `next dev` / `next start`.
- Public access via ngrok reserved domain (already set up) or Cloudflare Tunnel.

## Cloud (your spec: Vercel / Railway / Render)
| Component | Host | Notes |
|---|---|---|
| Frontend (Next.js) | **Vercel** | route handlers proxy interactive POSTs to backend |
| Backend (FastAPI) | **Railway** or **Render** (container) | always-on; exposes `/api/v1` |
| Worker/scheduler | Railway/Render worker **or** Vercel Cron → protected `/admin/{symbol}/refresh` | separates compute from serving |
| Database | **Neon** or **Supabase** Postgres (TimescaleDB optional) | managed |
| LLM | Claude API (cloud-friendly) — set `ANTHROPIC_API_KEY`; Ollama only on self-host | engine is swappable |
| Maps | Mapbox token (`NEXT_PUBLIC_MAPBOX_TOKEN`) | free tier |

## Config & secrets
- Commodity configs ship in the repo (`backend/app/configs/*.json`); `POST /admin/commodities/reload`
  picks up additions without redeploy.
- Secrets via env: `DATABASE_URL`, `EIA_API_KEY`, `USDA_API_KEY`, `FRED_API_KEY`,
  `ANTHROPIC_API_KEY` (optional), `NEXT_PUBLIC_MAPBOX_TOKEN`, `NEXT_PUBLIC_API_BASE`.

## Scaling notes
- Reads are cheap (precomputed). Scale the worker, not the API, as commodities grow.
- Per-commodity job cadence from config; backfill once, incremental after.
- TimescaleDB hypertables on `*_observations`/`prices` if series volume grows large.

## CI/CD
- GitHub → Vercel (frontend) auto-deploy; Railway/Render auto-deploy backend on push.
- Migrations via Alembic; `DATABASE.sql` is the canonical Postgres DDL.
