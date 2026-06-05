"""Module 6 — ML Lab API (leaderboard + champion forecasts)."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.ml.datasets import HORIZONS
from app.models.orm import Forecast, Location, ModelRun

router = APIRouter(prefix="/ml", tags=["Module 6 — ML Lab"])
_ORDER = [f"{h}d" for h in HORIZONS]


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ModelRun).where(ModelRun.target_kind == "regression")
    ).scalars().all()
    by_h: dict[str, list] = defaultdict(list)
    for r in rows:
        by_h[r.horizon].append({
            "model": r.model_name, "rmse": r.rmse, "mae": r.mae,
            "hit_rate": r.hit_rate, "directional_acc": r.directional_acc,
            "is_champion": r.is_champion,
        })
    out = []
    for h in _ORDER:
        models = sorted(by_h.get(h, []), key=lambda m: (m["rmse"] is None, m["rmse"]))
        if models:
            out.append({"horizon": h, "cv_folds": rows[0].cv_folds if rows else None, "models": models})
    return {"available": bool(out), "horizons": out}


@router.get("/forecasts")
def forecasts(db: Session = Depends(get_db)):
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return {"available": False}
    latest = db.execute(
        select(Forecast.issued_date)
        .where(Forecast.location_id == loc.id, Forecast.horizon.in_(_ORDER))
        .order_by(Forecast.issued_date.desc()).limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return {"available": False}
    rows = db.execute(
        select(Forecast).where(
            Forecast.location_id == loc.id, Forecast.issued_date == latest,
            Forecast.horizon.in_(_ORDER),
        )
    ).scalars().all()
    order = {h: i for i, h in enumerate(_ORDER)}
    rows = sorted(rows, key=lambda r: order.get(r.horizon, 99))
    return {
        "available": True, "issued_date": latest.isoformat(),
        "forecasts": [{
            "horizon": r.horizon, "model": r.model_name, "point_mm": r.point_mm,
            "p10_mm": r.p10_mm, "p90_mm": r.p90_mm, "confidence": r.confidence,
        } for r in rows],
    }
