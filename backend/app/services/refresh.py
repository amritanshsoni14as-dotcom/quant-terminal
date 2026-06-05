"""Incremental refresh jobs used by the scheduler (and the daily backfill).

light_refresh()  — near-real-time weather + drivers + features + signals. Fast
                   (seconds). Runs hourly and on startup so the dashboard stays
                   current to *today*.
ml_refresh()     — retrain the ML lab + champion forecasts. Heavier; runs daily.
"""
from __future__ import annotations

import threading
from datetime import date, timedelta

from app.core.db import SessionLocal
from app.features.builder import build_features
from app.ingest import drivers, noaa_oni, open_meteo
from app.ingest.base import get_or_create_location

_lock = threading.Lock()


def light_refresh() -> str:
    if not _lock.acquire(blocking=False):
        return "skipped (refresh already running)"
    try:
        db = SessionLocal()
        try:
            loc = get_or_create_location(db)
            today = date.today()
            # Near-real-time recent days (incl. today) + the 16-day forward forecast.
            n_recent = open_meteo.fetch_recent(db, loc, past_days=21)
            try:
                open_meteo.fetch_forecast(db, loc)
            except Exception as exc:  # noqa: BLE001
                print(f"[refresh] forecast skip: {exc}")
            # A short archive tail keeps authoritative values as they finalise.
            try:
                open_meteo.fetch_history(db, loc, today - timedelta(days=40), today - timedelta(days=2))
            except Exception as exc:  # noqa: BLE001
                print(f"[refresh] archive tail skip: {exc}")
            # Drivers update slowly but are cheap to re-pull.
            for fn in (lambda: noaa_oni.fetch_history(db), lambda: drivers.fetch_iod(db), lambda: drivers.fetch_mjo(db)):
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    print(f"[refresh] driver skip: {exc}")
            build_features(db)
        finally:
            db.close()
        # signals.run manages its own session.
        from app.signals.run import run as run_signals
        run_signals()
        return f"light_refresh ok (recent rows={n_recent})"
    finally:
        _lock.release()


def ml_refresh() -> str:
    if not _lock.acquire(blocking=False):
        return "skipped (refresh already running)"
    try:
        from app.ml.run import run as run_ml
        run_ml()
        return "ml_refresh ok"
    finally:
        _lock.release()


def news_refresh() -> str:
    """Module 11 — regenerate the alt-data news digest (uses the local LLM)."""
    from app.services import news
    db = SessionLocal()
    try:
        res = news.refresh(db)
        return f"news_refresh {res}"
    finally:
        db.close()


def commodity_refresh() -> str:
    """Update recent commodity prices (Yahoo, last ~1mo)."""
    from app.ingest.commodities import backfill_all
    db = SessionLocal()
    try:
        res = backfill_all(db, rng="1mo")
        return f"commodity_refresh {res}"
    finally:
        db.close()


def fundamentals_refresh() -> str:
    """Commodity fundamentals: CFTC COT (free) + EIA/FRED (if keys set)."""
    from app.connectors import cftc, eia
    db = SessionLocal()
    try:
        res = {"cftc": cftc.refresh(db)}
        try:
            res["eia"] = eia.refresh(db)
        except Exception as exc:  # noqa: BLE001
            res["eia"] = f"error: {exc}"
        return f"fundamentals_refresh {res}"
    finally:
        db.close()


def forecast_refresh() -> str:
    """Recompute commodity bull/bear/neutral forecasts (LightGBM)."""
    from app.services import forecast
    db = SessionLocal()
    try:
        return f"forecast_refresh {forecast.refresh_all(db)}"
    finally:
        db.close()
