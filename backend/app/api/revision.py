"""Module 7 — Forecast Revision Engine API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.orm import (
    Forecast,
    ForecastRevision,
    Location,
    ModelRun,
    RevisionPrediction,
)

router = APIRouter(prefix="/revision", tags=["Module 7 — Forecast Revision Engine"])


@router.get("")
def revision(db: Session = Depends(get_db)):
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return {"available": False}

    pred = db.execute(
        select(RevisionPrediction)
        .where(RevisionPrediction.location_id == loc.id)
        .order_by(RevisionPrediction.as_of.desc()).limit(1)
    ).scalar_one_or_none()
    if pred is None:
        return {"available": False, "reason": "run `python -m app.signals.run`"}

    model = db.execute(
        select(ModelRun).where(ModelRun.model_name == "revision_rf").limit(1)
    ).scalar_one_or_none()

    # Reconstructed seasonal-forecast series + revisions for the current season.
    series = db.execute(
        select(Forecast).where(
            Forecast.location_id == loc.id, Forecast.horizon == "seasonal",
            Forecast.model_name == "revision_recon",
        ).order_by(Forecast.issued_date)
    ).scalars().all()
    revs = db.execute(
        select(ForecastRevision).where(
            ForecastRevision.location_id == loc.id, ForecastRevision.horizon == "seasonal",
        ).order_by(ForecastRevision.curr_issued_date)
    ).scalars().all()

    display_season = series[0].issued_date.year if series else None
    return {
        "available": True,
        "as_of": pred.as_of.isoformat(),
        "display_season": display_season,
        "prob_revise_up": pred.prob_revise_up,
        "prob_revise_down": pred.prob_revise_down,
        "expected_revision_mm": pred.expected_revision_mm,
        "expected_market_impact": pred.expected_market_impact,
        "confidence": pred.confidence,
        "model": {
            "test_accuracy": model.hit_rate if model else None,
            "n_samples": (model.params or {}).get("n_samples") if model else None,
            "base_rate_up": (model.params or {}).get("base_rate_up") if model else None,
            "size_rmse": model.rmse if model else None,
        },
        "forecast_series": [
            {"date": f.issued_date.isoformat(), "expected_season_mm": f.point_mm} for f in series
        ],
        "revisions": [
            {"date": r.curr_issued_date.isoformat(), "revision_mm": r.revision_mm, "direction": r.direction}
            for r in revs
        ],
    }
