"""Meta/health + data-coverage endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.orm import FeaturesDaily, Location, RawWeather

router = APIRouter(tags=["Meta"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "rainmumbai-terminal", "version": "0.1.0"}


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    loc = db.execute(
        select(Location).where(Location.code == settings.PRIMARY_CODE)
    ).scalar_one_or_none()
    if not loc:
        return {"location": None, "coverage": None}

    cov = db.execute(
        select(
            func.min(FeaturesDaily.obs_date),
            func.max(FeaturesDaily.obs_date),
            func.count(),
        ).where(FeaturesDaily.location_id == loc.id)
    ).one()
    raw_sources = db.execute(
        select(RawWeather.source, func.count())
        .where(RawWeather.location_id == loc.id)
        .group_by(RawWeather.source)
    ).all()
    return {
        "location": {"code": loc.code, "name": loc.name, "lat": loc.latitude, "lon": loc.longitude},
        "coverage": {
            "start": cov[0].isoformat() if cov[0] else None,
            "end": cov[1].isoformat() if cov[1] else None,
            "days": cov[2],
            "years": round(cov[2] / 365.25, 1) if cov[2] else 0,
        },
        "raw_sources": {s: n for s, n in raw_sources},
    }
