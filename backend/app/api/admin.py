"""Admin endpoints — trigger backfill / refresh on cloud deploys."""
from __future__ import annotations

import threading

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.orm import FeaturesDaily

router = APIRouter(tags=["Admin"])

_running = False


@router.get("/admin/status")
def admin_status():
    db = SessionLocal()
    try:
        count = db.execute(select(func.count()).select_from(FeaturesDaily)).scalar() or 0
    finally:
        db.close()
    return {"features_rows": count, "seed_running": _running}


@router.post("/admin/seed")
def admin_seed(full: bool = Query(False)):
    """Trigger the data backfill. Use full=true for historical, false for recent only."""
    global _running
    if _running:
        return {"status": "already_running"}

    def _do():
        global _running
        _running = True
        try:
            from app.ingest.backfill import run as run_backfill
            run_backfill(full=full)
        except Exception as exc:
            print(f"[admin/seed] failed: {exc}")
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
        global _running
        _running = True
        try:
            from app.services.refresh import light_refresh
            light_refresh()
        except Exception as exc:
            print(f"[admin/refresh] failed: {exc}")
        finally:
            _running = False

    threading.Thread(target=_do, daemon=True).start()
    return {"status": "started"}
