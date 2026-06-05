"""Module 1 — Weather Command Center API.

Read-only endpoints over the precomputed feature store. The dashboard never
triggers compute; it reads what the ingest/feature jobs have written.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.orm import Climatology, FeaturesDaily, Location, RawClimateDriver

router = APIRouter(prefix="/weather", tags=["Module 1 — Weather Command Center"])


def _location_id(db: Session) -> int | None:
    loc = db.execute(
        select(Location).where(Location.code == settings.PRIMARY_CODE)
    ).scalar_one_or_none()
    return loc.id if loc else None


def _season_start(d: date) -> date:
    y = d.year if (d.month, d.day) >= (settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY) else d.year - 1
    return date(y, settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY)


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Headline KPIs: today / weekly / monthly / seasonal rainfall, deviation %,
    historical average, monsoon progress."""
    loc_id = _location_id(db)
    if loc_id is None:
        return {"available": False, "reason": "no location; run backfill"}

    latest = db.execute(
        select(FeaturesDaily)
        .where(FeaturesDaily.location_id == loc_id, FeaturesDaily.rainfall_mm.isnot(None))
        .order_by(FeaturesDaily.obs_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return {"available": False, "reason": "no features; run backfill"}

    d = latest.obs_date
    ss = _season_start(d)

    # Climatological seasonal-to-date average from the climatology table.
    clim = {c.doy: c.rain_mean_mm for c in db.execute(
        select(Climatology).where(Climatology.location_id == loc_id)
    ).scalars()}
    hist_avg, cur = 0.0, ss
    while cur <= d:
        hist_avg += clim.get(cur.timetuple().tm_yday, 0.0) or 0.0
        cur += timedelta(days=1)

    return {
        "available": True,
        "as_of": d.isoformat(),
        "today_rainfall_mm": round(latest.rainfall_mm or 0.0, 2),
        "weekly_rainfall_mm": round(latest.rain_roll_7 or 0.0, 2),
        "monthly_rainfall_mm": round(latest.rain_roll_30 or 0.0, 2),
        "seasonal_rainfall_mm": round(latest.rain_season_cum or 0.0, 2),
        "historical_avg_seasonal_mm": round(hist_avg, 2),
        "deviation_pct": latest.rain_anomaly_pct,
        "monsoon_progress": latest.monsoon_progress,
        "season_start": ss.isoformat(),
        "temp_mean_c": latest.temp_mean_c,
        "humidity_pct": latest.humidity_pct,
        "pressure_hpa": latest.pressure_hpa,
        "wind_kmh": latest.wind_kmh,
    }


@router.get("/daily")
def daily(days: int = Query(120, ge=1, le=2000), db: Session = Depends(get_db)):
    """Daily rainfall series for the most recent `days`."""
    loc_id = _location_id(db)
    if loc_id is None:
        return {"series": []}
    rows = db.execute(
        select(FeaturesDaily)
        .where(FeaturesDaily.location_id == loc_id)
        .order_by(FeaturesDaily.obs_date.desc())
        .limit(days)
    ).scalars().all()
    rows = list(reversed(rows))
    return {
        "series": [
            {
                "date": r.obs_date.isoformat(),
                "rainfall_mm": round(r.rainfall_mm, 2) if r.rainfall_mm is not None else None,
                "roll7": r.rain_roll_7,
                "roll30": r.rain_roll_30,
            }
            for r in rows
        ]
    }


@router.get("/weekly")
def weekly(weeks: int = Query(52, ge=1, le=520), db: Session = Depends(get_db)):
    """Rainfall aggregated by ISO week."""
    loc_id = _location_id(db)
    if loc_id is None:
        return {"series": []}
    cutoff = date.today() - timedelta(weeks=weeks)
    rows = db.execute(
        select(FeaturesDaily.obs_date, FeaturesDaily.rainfall_mm)
        .where(FeaturesDaily.location_id == loc_id, FeaturesDaily.obs_date >= cutoff)
        .order_by(FeaturesDaily.obs_date)
    ).all()
    buckets: dict[str, float] = defaultdict(float)
    for d, rain in rows:
        iso = d.isocalendar()
        buckets[f"{iso.year}-W{iso.week:02d}"] += rain or 0.0
    return {"series": [{"week": k, "rainfall_mm": round(v, 2)} for k, v in sorted(buckets.items())]}


@router.get("/monthly")
def monthly(months: int = Query(60, ge=1, le=600), db: Session = Depends(get_db)):
    """Rainfall aggregated by calendar month."""
    loc_id = _location_id(db)
    if loc_id is None:
        return {"series": []}
    rows = db.execute(
        select(FeaturesDaily.obs_date, FeaturesDaily.rainfall_mm)
        .where(FeaturesDaily.location_id == loc_id)
        .order_by(FeaturesDaily.obs_date)
    ).all()
    buckets: dict[str, float] = defaultdict(float)
    for d, rain in rows:
        buckets[f"{d.year}-{d.month:02d}"] += rain or 0.0
    items = [{"month": k, "rainfall_mm": round(v, 2)} for k, v in sorted(buckets.items())]
    return {"series": items[-months:]}


@router.get("/cumulative")
def cumulative(db: Session = Depends(get_db)):
    """Current-season cumulative rainfall vs the climatological band (mean/p10/p90)."""
    loc_id = _location_id(db)
    if loc_id is None:
        return {"series": []}
    latest = db.execute(
        select(FeaturesDaily.obs_date)
        .where(FeaturesDaily.location_id == loc_id, FeaturesDaily.rainfall_mm.isnot(None))
        .order_by(FeaturesDaily.obs_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return {"series": []}
    ss = _season_start(latest)

    rows = db.execute(
        select(FeaturesDaily.obs_date, FeaturesDaily.rainfall_mm)
        .where(FeaturesDaily.location_id == loc_id, FeaturesDaily.obs_date >= ss)
        .order_by(FeaturesDaily.obs_date)
    ).all()
    clim = {c.doy: c for c in db.execute(
        select(Climatology).where(Climatology.location_id == loc_id)
    ).scalars()}

    series = []
    actual = clim_mean = clim_p10 = clim_p90 = 0.0
    for d, rain in rows:
        c = clim.get(d.timetuple().tm_yday)
        actual += rain or 0.0
        clim_mean += (c.rain_mean_mm if c else 0.0) or 0.0
        clim_p10 += (c.rain_p10 if c else 0.0) or 0.0
        clim_p90 += (c.rain_p90 if c else 0.0) or 0.0
        series.append(
            {
                "date": d.isoformat(),
                "actual": round(actual, 1),
                "climatology": round(clim_mean, 1),
                "p10": round(clim_p10, 1),
                "p90": round(clim_p90, 1),
            }
        )
    return {"season_start": ss.isoformat(), "series": series}


@router.get("/drivers")
def drivers(db: Session = Depends(get_db)):
    """Latest climate-driver readings (ENSO/ONI, IOD, MJO) for the header strip."""
    out = {}
    for name in ("ONI", "IOD_DMI", "MJO_PHASE", "MJO_AMP"):
        r = db.execute(
            select(RawClimateDriver)
            .where(RawClimateDriver.driver == name, RawClimateDriver.value.isnot(None))
            .order_by(RawClimateDriver.obs_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        out[name] = {"value": r.value, "as_of": r.obs_date.isoformat()} if r else None
    return out
