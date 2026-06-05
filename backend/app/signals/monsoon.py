"""Module 3 — Monsoon Intelligence: ENSO / IOD / MJO relationships with
Mumbai monsoon rainfall, current regime, and historical impact.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import FeaturesDaily, Location, RawClimateDriver
from app.signals import seasonstats


def _latest(db: Session, driver: str):
    r = db.execute(
        select(RawClimateDriver).where(RawClimateDriver.driver == driver, RawClimateDriver.value.isnot(None))
        .order_by(RawClimateDriver.obs_date.desc()).limit(1)
    ).scalar_one_or_none()
    return (r.value, r.obs_date.isoformat()) if r else (None, None)


def _impact(rows, normal, key, order):
    groups = defaultdict(list)
    for r in rows:
        st = getattr(r, key)
        if st is not None:
            groups[st].append(r.season_mm)
    out = []
    for st in order:
        vals = groups.get(st, [])
        if vals:
            mean = sum(vals) / len(vals)
            out.append({
                "state": st, "n_years": len(vals), "mean_season_mm": round(mean, 0),
                "deviation_pct": round((mean - normal) / normal * 100, 1) if normal else None,
            })
    return out


def compute(db: Session) -> dict:
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return {"available": False}
    rows, normal, _ = seasonstats.build(db)
    if not rows:
        return {"available": False}

    years = [r.year for r in rows]
    season = [r.season_mm for r in rows]

    oni_now, oni_dt = _latest(db, "ONI")
    dmi_now, dmi_dt = _latest(db, "IOD_DMI")
    phase_now, phase_dt = _latest(db, "MJO_PHASE")
    amp_now, _ = _latest(db, "MJO_AMP")

    # MJO: mean daily monsoon rainfall by phase (1..8).
    by_phase = defaultdict(list)
    for fp, rain in db.execute(
        select(FeaturesDaily.mjo_phase, FeaturesDaily.rainfall_mm)
        .where(FeaturesDaily.location_id == loc.id, FeaturesDaily.mjo_phase.isnot(None),
               FeaturesDaily.rainfall_mm.isnot(None))
    ).all():
        # monsoon months only handled via separate query would be ideal; approximate w/ all-year
        by_phase[int(fp)].append(rain)
    mjo_phase_rain = [
        {"phase": p, "mean_daily_mm": round(sum(by_phase[p]) / len(by_phase[p]), 2), "n": len(by_phase[p])}
        for p in range(1, 9) if by_phase.get(p)
    ]
    overall_daily = (sum(season) / len(season)) / 122 if season else 0  # rough daily monsoon mean

    return {
        "available": True,
        "normal_season_mm": round(normal, 0),
        "enso": {
            "current": oni_now, "as_of": oni_dt, "state": seasonstats.enso_state(oni_now),
            "correlation": seasonstats.pearson([r.jja_oni for r in rows], season),
            "impact": _impact(rows, normal, "enso_state", ["La Niña", "Neutral", "El Niño"]),
            "note": "La Niña typically wet, El Niño dry for the Indian monsoon.",
        },
        "iod": {
            "current": dmi_now, "as_of": dmi_dt, "state": seasonstats.iod_state(dmi_now),
            "correlation": seasonstats.pearson([r.season_dmi for r in rows], season),
            "impact": _impact(rows, normal, "iod_state", ["Negative", "Neutral", "Positive"]),
            "note": "Positive IOD enhances monsoon rainfall.",
        },
        "mjo": {
            "current_phase": int(phase_now) if phase_now is not None else None,
            "current_amp": amp_now, "as_of": phase_dt,
            "phase_rainfall": mjo_phase_rain,
            "baseline_daily_mm": round(overall_daily, 2),
            "note": "Phases 1–4 (convection over Indian Ocean) tend to enhance regional rainfall.",
        },
        "coverage_years": [min(years), max(years)],
    }
