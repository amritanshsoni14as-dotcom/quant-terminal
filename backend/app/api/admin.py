"""Admin endpoints — trigger backfill / refresh on cloud deploys."""
from __future__ import annotations

import threading
import traceback

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.orm import FeaturesDaily, RawWeather

router = APIRouter(tags=["Admin"])

_running = False
_last_error: str | None = None
_last_result: str | None = None


@router.get("/admin/status")
def admin_status():
    db = SessionLocal()
    try:
        feat_count = db.execute(select(func.count()).select_from(FeaturesDaily)).scalar() or 0
        raw_count = db.execute(select(func.count()).select_from(RawWeather)).scalar() or 0
    finally:
        db.close()
    return {
        "features_rows": feat_count,
        "raw_weather_rows": raw_count,
        "seed_running": _running,
        "last_error": _last_error,
        "last_result": _last_result,
    }


@router.post("/admin/seed")
def admin_seed(full: bool = Query(False)):
    """Trigger the data backfill. Use full=true for historical, false for recent only."""
    global _running
    if _running:
        return {"status": "already_running"}

    def _do():
        global _running, _last_error, _last_result
        _running = True
        _last_error = None
        _last_result = None
        try:
            from app.ingest.backfill import run as run_backfill
            run_backfill(full=full)
            _last_result = "seed complete"
        except Exception as exc:
            _last_error = f"{exc}\n{traceback.format_exc()}"
            print(f"[admin/seed] failed: {_last_error}")
        finally:
            _running = False

    threading.Thread(target=_do, daemon=True).start()
    return {"status": "started", "mode": "full" if full else "incremental"}


@router.post("/admin/refresh")
def admin_refresh():
    """Trigger a light refresh (recent weather + drivers + signals)."""
    global _running
    if _running:
        return {"status": "already_running"}

    def _do():
        global _running, _last_error, _last_result
        _running = True
        _last_error = None
        _last_result = None
        try:
            from app.services.refresh import light_refresh
            result = light_refresh()
            _last_result = f"refresh complete: {result}"
        except Exception as exc:
            _last_error = f"{exc}\n{traceback.format_exc()}"
            print(f"[admin/refresh] failed: {_last_error}")
        finally:
            _running = False

    threading.Thread(target=_do, daemon=True).start()
    return {"status": "started"}
