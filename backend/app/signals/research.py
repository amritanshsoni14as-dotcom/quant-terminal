"""Module 5 — Historical Research Lab.

Pure analytics over the 25-year feature store: correlation matrix, driver
lead/lag cross-correlation, seasonality, and extreme/drought/flood events.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import FeaturesDaily, Location
from app.signals import seasonstats

CORR_VARS = [
    ("rainfall_mm", "Rain"), ("temp_mean_c", "Temp"), ("humidity_pct", "Humidity"),
    ("pressure_hpa", "Pressure"), ("wind_kmh", "Wind"),
    ("oni", "ONI"), ("iod_dmi", "IOD"), ("mjo_amp", "MJO"),
]
LAG_DRIVERS = [("oni", "ONI"), ("iod_dmi", "IOD"), ("mjo_amp", "MJO amp")]
MAX_LAG = 6


def compute(db: Session) -> dict:
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return {"available": False}
    rows = db.execute(
        select(FeaturesDaily).where(FeaturesDaily.location_id == loc.id)
        .order_by(FeaturesDaily.obs_date)
    ).scalars().all()
    if len(rows) < 400:
        return {"available": False}

    # ---- Correlation matrix (daily, complete cases) ----
    cols = [c for c, _ in CORR_VARS]
    data = []
    for r in rows:
        vals = [getattr(r, c) for c in cols]
        if all(v is not None for v in vals):
            data.append(vals)
    arr = np.array(data, dtype=float)
    corr = np.corrcoef(arr, rowvar=False)
    matrix = [[round(float(corr[i][j]), 2) for j in range(len(cols))] for i in range(len(cols))]

    # ---- Monthly series for lead/lag ----
    mrain: dict[tuple[int, int], float] = defaultdict(float)
    mdrv: dict[str, dict[tuple[int, int], list]] = {c: defaultdict(list) for c, _ in LAG_DRIVERS}
    for r in rows:
        key = (r.obs_date.year, r.obs_date.month)
        mrain[key] += r.rainfall_mm or 0.0
        for c, _ in LAG_DRIVERS:
            v = getattr(r, c)
            if v is not None:
                mdrv[c][key].append(v)
    months = sorted(mrain)
    idx = {m: i for i, m in enumerate(months)}
    rain_series = [mrain[m] for m in months]
    leadlag = []
    for c, label in LAG_DRIVERS:
        drv_series = [float(np.mean(mdrv[c][m])) if mdrv[c][m] else None for m in months]
        pts = []
        for lag in range(-MAX_LAG, MAX_LAG + 1):
            xs, ys = [], []
            for i, m in enumerate(months):
                j = i - lag
                if 0 <= j < len(months) and drv_series[j] is not None:
                    xs.append(rain_series[i]); ys.append(drv_series[j])
            corr_l = seasonstats.pearson(xs, ys)
            pts.append({"lag": lag, "corr": corr_l})
        leadlag.append({"driver": label, "series": pts})

    # ---- Seasonality (calendar-month mean total) ----
    by_month_year: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        by_month_year[r.obs_date.month][r.obs_date.year] += r.rainfall_mm or 0.0
    seasonality = []
    for mo in range(1, 13):
        totals = list(by_month_year[mo].values())
        if totals:
            seasonality.append({"month": mo, "mean_mm": round(float(np.mean(totals)), 0),
                                "std_mm": round(float(np.std(totals)), 0)})

    # ---- Extremes / drought / flood ----
    wettest_days = sorted(
        [{"date": r.obs_date.isoformat(), "mm": round(r.rainfall_mm, 1)}
         for r in rows if r.rainfall_mm is not None],
        key=lambda x: -x["mm"])[:10]

    srows, normal, _ = seasonstats.build(db)
    last_avail = rows[-1].obs_date
    complete = [s for s in srows if date(s.year, 9, 30) <= last_avail]  # exclude in-progress season
    seasons = sorted(
        [{"year": s.year, "mm": round(s.season_mm, 0),
          "deviation_pct": round((s.season_mm - normal) / normal * 100, 1) if normal else None}
         for s in complete], key=lambda x: x["mm"])
    driest = seasons[:5]
    wettest = list(reversed(seasons[-5:]))

    return {
        "available": True,
        "coverage": {"start": rows[0].obs_date.isoformat(), "end": rows[-1].obs_date.isoformat(),
                     "n_days": len(rows), "n_seasons": len(srows)},
        "normal_season_mm": round(normal, 0),
        "correlation": {"labels": [lab for _, lab in CORR_VARS], "matrix": matrix},
        "leadlag": leadlag,
        "seasonality": seasonality,
        "extremes": {
            "wettest_days": wettest_days,
            "wettest_seasons": wettest,
            "driest_seasons": driest,
        },
    }
