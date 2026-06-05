"""Feature store + climatology builder.

Merges multi-source raw weather into one daily series, computes climatological
normals (day-of-year), and engineers the features Module 1 (and later the ML
lab) consume: rolling sums, season-to-date cumulative, deviation vs climatology,
monsoon progress, and aligned climate-driver values.

Pure-Python (no pandas) to stay dependency-light and portable.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingest.base import get_or_create_location, upsert
from app.models.orm import (
    Climatology,
    FeaturesDaily,
    RawClimateDriver,
    RawWeather,
)


def _percentile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _season_start(d: date) -> date:
    """Most recent June 1 on/before d."""
    y = d.year if (d.month, d.day) >= (settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY) else d.year - 1
    return date(y, settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY)


def _monsoon_progress(d: date) -> float:
    start = date(d.year, settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY)
    end = date(d.year, settings.MONSOON_END_MONTH, settings.MONSOON_END_DAY)
    if d < start:
        return 0.0
    if d > end:
        return 1.0
    return round((d - start).days / (end - start).days, 4)


def _merge_raw(db: Session, location_id: int) -> dict[date, dict]:
    """One merged record per date. Prefer Open-Meteo for rain/temp/wind;
    fill humidity/pressure (and gaps) from NASA POWER."""
    rows = db.execute(
        select(RawWeather).where(RawWeather.location_id == location_id)
    ).scalars().all()

    by_date: dict[date, dict[str, RawWeather]] = defaultdict(dict)
    for r in rows:
        by_date[r.obs_date][r.source] = r

    def pick(*vals):
        for v in vals:
            if v is not None:
                return v
        return None

    merged: dict[date, dict] = {}
    for d, srcs in by_date.items():
        om = srcs.get("open_meteo")
        np = srcs.get("nasa_power")
        merged[d] = {
            "rainfall_mm": pick(getattr(om, "rainfall_mm", None), getattr(np, "rainfall_mm", None)),
            "temp_mean_c": pick(getattr(om, "temp_mean_c", None), getattr(np, "temp_mean_c", None)),
            "temp_max_c": pick(getattr(om, "temp_max_c", None), getattr(np, "temp_max_c", None)),
            "temp_min_c": pick(getattr(om, "temp_min_c", None), getattr(np, "temp_min_c", None)),
            "humidity_pct": pick(getattr(np, "humidity_pct", None), getattr(om, "humidity_pct", None)),
            "pressure_hpa": pick(getattr(np, "pressure_hpa", None), getattr(om, "pressure_hpa", None)),
            "wind_kmh": pick(getattr(om, "wind_kmh", None), getattr(np, "wind_kmh", None)),
        }
    return merged


def _build_climatology(db: Session, location_id: int, merged: dict[date, dict]) -> dict[int, dict]:
    by_doy: dict[int, list[float]] = defaultdict(list)
    for d, rec in merged.items():
        if rec["rainfall_mm"] is not None:
            by_doy[d.timetuple().tm_yday].append(rec["rainfall_mm"])

    clim: dict[int, dict] = {}
    rows = []
    for doy, vals in by_doy.items():
        s = sorted(vals)
        clim[doy] = {
            "rain_mean_mm": statistics.fmean(vals),
            "rain_std_mm": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "rain_p10": _percentile(s, 0.10),
            "rain_p90": _percentile(s, 0.90),
        }
        rows.append({"location_id": location_id, "doy": doy, **clim[doy]})

    db.execute(delete(Climatology).where(Climatology.location_id == location_id))
    db.commit()
    upsert(db, Climatology, rows, ["location_id", "doy"])
    return clim


def _driver_lookups(db: Session):
    monthly: dict[str, dict[tuple[int, int], float]] = defaultdict(dict)
    daily: dict[str, dict[date, float]] = defaultdict(dict)
    for r in db.execute(select(RawClimateDriver)).scalars():
        if r.value is None:
            continue
        if r.driver.startswith("MJO_"):
            daily[r.driver][r.obs_date] = r.value
        else:  # ONI, IOD_DMI — monthly
            monthly[r.driver][(r.obs_date.year, r.obs_date.month)] = r.value
    return monthly, daily


def _latest_daily(daily: dict[date, float], d: date, max_lag: int = 10) -> float | None:
    for lag in range(max_lag + 1):
        v = daily.get(d - timedelta(days=lag))
        if v is not None:
            return v
    return None


def build_features(db: Session) -> int:
    """Rebuild features_daily + climatology for the primary location."""
    location_id = get_or_create_location(db)
    merged = _merge_raw(db, location_id)
    if not merged:
        return 0

    clim = _build_climatology(db, location_id, merged)
    monthly, daily = _driver_lookups(db)
    dates = sorted(merged)

    # Prefix sums for rolling windows.
    rain_by_date = {d: (merged[d]["rainfall_mm"] or 0.0) for d in dates}

    def roll_sum(d: date, window: int) -> float:
        return sum(rain_by_date.get(d - timedelta(days=k), 0.0) for k in range(window))

    # Climatological season-to-date cumulative (for anomaly).
    def clim_cum(season_start: date, d: date) -> float:
        total, cur = 0.0, season_start
        while cur <= d:
            c = clim.get(cur.timetuple().tm_yday)
            if c:
                total += c["rain_mean_mm"]
            cur += timedelta(days=1)
        return total

    rows = []
    for d in dates:
        rec = merged[d]
        ss = _season_start(d)
        season_cum = sum(rain_by_date.get(ss + timedelta(days=k), 0.0)
                         for k in range((d - ss).days + 1))
        clim_season = clim_cum(ss, d)
        anomaly_pct = ((season_cum - clim_season) / clim_season * 100.0) if clim_season > 0 else None
        ym = (d.year, d.month)
        rows.append(
            {
                "location_id": location_id,
                "obs_date": d,
                "rainfall_mm": rec["rainfall_mm"],
                "rain_roll_7": round(roll_sum(d, 7), 2),
                "rain_roll_30": round(roll_sum(d, 30), 2),
                "rain_season_cum": round(season_cum, 2),
                "rain_anomaly_pct": round(anomaly_pct, 2) if anomaly_pct is not None else None,
                "temp_mean_c": rec["temp_mean_c"],
                "humidity_pct": rec["humidity_pct"],
                "pressure_hpa": rec["pressure_hpa"],
                "wind_kmh": rec["wind_kmh"],
                "oni": monthly.get("ONI", {}).get(ym),
                "iod_dmi": monthly.get("IOD_DMI", {}).get(ym),
                "mjo_phase": int(_latest_daily(daily.get("MJO_PHASE", {}), d))
                if _latest_daily(daily.get("MJO_PHASE", {}), d) is not None else None,
                "mjo_amp": _latest_daily(daily.get("MJO_AMP", {}), d),
                "sst_anom": None,  # Phase 1: populated from OISST in a later phase
                "monsoon_progress": _monsoon_progress(d),
                "extra": None,
            }
        )

    db.execute(delete(FeaturesDaily).where(FeaturesDaily.location_id == location_id))
    db.commit()
    upsert(db, FeaturesDaily, rows, ["location_id", "obs_date"])
    return len(rows)
