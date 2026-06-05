"""Module 8 — Probability Engine API."""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.orm import Location, ProbabilitySnapshot

router = APIRouter(prefix="/probability", tags=["Module 8 — Probability Engine"])


@router.get("")
def probability(db: Session = Depends(get_db)):
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return {"available": False}
    snap = db.execute(
        select(ProbabilitySnapshot)
        .where(ProbabilitySnapshot.location_id == loc.id, ProbabilitySnapshot.scope == "seasonal")
        .order_by(ProbabilitySnapshot.as_of.desc())
        .limit(1)
    ).scalar_one_or_none()
    if snap is None:
        return {"available": False, "reason": "run `python -m app.signals.run`"}

    pp = snap.posterior_params or {}
    mu, sd, normal = pp.get("mu"), pp.get("sd"), pp.get("normal")

    # Posterior density curve + threshold markers for the chart.
    curve = []
    if mu is not None and sd and sd > 0:
        lo, hi = mu - 4 * sd, mu + 4 * sd
        steps = 80
        for i in range(steps + 1):
            x = lo + (hi - lo) * i / steps
            pdf = math.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))
            curve.append({"x": round(x, 1), "pdf": pdf})

    return {
        "available": True,
        "as_of": snap.as_of.isoformat(),
        "normal_mm": normal,
        "expected_mm": mu,
        "posterior_sd_mm": sd,
        "probabilities": {
            "above_normal": snap.p_above_norm,
            "below_normal": snap.p_below_norm,
            "above_10pct": snap.p_above_10,
            "above_20pct": snap.p_above_20,
            "below_10pct": snap.p_below_10,
            "below_20pct": snap.p_below_20,
        },
        "method": pp.get("method"),
        "n_years": pp.get("n_years"),
        "curve": curve,
        "thresholds": {
            "normal": normal,
            "above_10": round(normal * 1.1, 1) if normal else None,
            "above_20": round(normal * 1.2, 1) if normal else None,
            "below_10": round(normal * 0.9, 1) if normal else None,
            "below_20": round(normal * 0.8, 1) if normal else None,
        },
    }
