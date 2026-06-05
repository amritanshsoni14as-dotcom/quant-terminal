"""Feature/target matrix builder for the ML Lab (Module 6).

Targets are h-day-forward cumulative rainfall (sum over d+1..d+h) for
h in {1,3,7,15,30}. Features are the engineered daily fields plus calendar
seasonality. Pure feature-store read → numpy arrays; no leakage (targets only
use *future* days, features only use day d).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import FeaturesDaily, Location

HORIZONS = [1, 3, 7, 15, 30]

FEATURE_COLS = [
    "rainfall_mm", "rain_roll_7", "rain_roll_30", "rain_season_cum", "rain_anomaly_pct",
    "temp_mean_c", "humidity_pct", "pressure_hpa", "wind_kmh",
    "oni", "iod_dmi", "mjo_phase", "mjo_amp", "monsoon_progress",
]


@dataclass
class Dataset:
    dates: list[date]
    X: np.ndarray
    feature_names: list[str]
    rain: np.ndarray
    targets: dict[int, np.ndarray]      # horizon -> (n,) float, nan where unavailable
    medians: dict[str, float]
    location_id: int


def _seasonal(d: date) -> list[float]:
    doy = d.timetuple().tm_yday
    return [
        math.sin(2 * math.pi * doy / 365.25),
        math.cos(2 * math.pi * doy / 365.25),
    ]


def build(db: Session) -> Dataset | None:
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return None
    rows = db.execute(
        select(FeaturesDaily)
        .where(FeaturesDaily.location_id == loc.id)
        .order_by(FeaturesDaily.obs_date)
    ).scalars().all()
    if len(rows) < 400:
        return None

    dates = [r.obs_date for r in rows]
    rain = np.array([(r.rainfall_mm or 0.0) for r in rows], dtype=float)

    # Column medians for imputation.
    medians: dict[str, float] = {}
    for c in FEATURE_COLS:
        vals = [getattr(r, c) for r in rows if getattr(r, c) is not None]
        medians[c] = float(np.median(vals)) if vals else 0.0

    feat_rows = []
    for r in rows:
        vec = [(getattr(r, c) if getattr(r, c) is not None else medians[c]) for c in FEATURE_COLS]
        vec += _seasonal(r.obs_date)
        feat_rows.append(vec)
    X = np.array(feat_rows, dtype=float)
    feature_names = FEATURE_COLS + ["doy_sin", "doy_cos"]

    # h-day-forward cumulative rainfall (assumes daily-contiguous series).
    n = len(rows)
    targets: dict[int, np.ndarray] = {}
    csum = np.concatenate([[0.0], np.cumsum(rain)])  # prefix sums
    for h in HORIZONS:
        y = np.full(n, np.nan)
        for i in range(n):
            j = i + h
            if j < n:
                y[i] = csum[j + 1] - csum[i + 1]   # sum of rain[i+1 .. i+h]
        targets[h] = y

    return Dataset(dates, X, feature_names, rain, targets, medians, loc.id)
