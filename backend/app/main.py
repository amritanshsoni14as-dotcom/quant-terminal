"""FastAPI application factory for the RAINMUMBAI Terminal backend."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    ai,
    commodities,
    derivative,
    intel,
    meta,
    ml,
    monsoon,
    probability,
    revision,
    signal,
    weather,
)
from app.core.config import settings
from app.core.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAINMUMBAI Terminal API",
        version="0.1.0",
        description="Weather-derivatives research & trading backend (Phase 1: Weather Command Center).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_v1 = "/api/v1"
    app.include_router(meta.router, prefix=api_v1)
    app.include_router(weather.router, prefix=api_v1)
    app.include_router(probability.router, prefix=api_v1)
    app.include_router(derivative.router, prefix=api_v1)
    app.include_router(signal.router, prefix=api_v1)
    app.include_router(ml.router, prefix=api_v1)
    app.include_router(revision.router, prefix=api_v1)
    app.include_router(monsoon.router, prefix=api_v1)
    app.include_router(commodities.router, prefix=api_v1)
    app.include_router(intel.router, prefix=api_v1)
    app.include_router(ai.router, prefix=api_v1)
    app.include_router(admin.router, prefix=api_v1)

    @app.on_event("startup")
    def _startup() -> None:
        # Ensure tables exist (SQLite local dev + first cloud boot on empty Postgres).
        init_db()
        # First cloud boot: empty DB → backfill from the free APIs in the background
        # (non-blocking so the web service binds to $PORT immediately).
        _maybe_seed_in_background()
        # Self-updating: hourly weather/signal refresh + daily ML retrain.
        try:
            from app.services.scheduler import start_scheduler
            start_scheduler()
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] scheduler not started: {exc}")

    @app.get("/")
    def root():
        return {"service": "rainmumbai-terminal", "docs": "/docs", "api": api_v1}

    return app


def _maybe_seed_in_background() -> None:
    """If the database has no weather data yet (fresh cloud deploy), run the full
    backfill once in a daemon thread so the server can start serving immediately."""
    import threading

    def _seed():
        try:
            from sqlalchemy import func, select

            from app.core.db import SessionLocal
            from app.models.orm import FeaturesDaily

            db = SessionLocal()
            try:
                count = db.execute(select(func.count()).select_from(FeaturesDaily)).scalar() or 0
            finally:
                db.close()
            if count > 0:
                return
            print("[startup] empty database detected — running first-time backfill…")
            from app.ingest.backfill import run as run_backfill
            run_backfill(full=True)
            print("[startup] first-time backfill complete.")
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] seed skipped/failed: {exc}")

    threading.Thread(target=_seed, daemon=True).start()


app = create_app()
