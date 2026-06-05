"""Module 8 — Probability Engine (seasonal cumulative rainfall).

Method (empirical-analog, updates as the season progresses):
  For every past year we have a pair (rainfall accumulated up to today's
  day-of-year, full Jun–Sep total). Regressing full-season total on the
  season-to-date amount gives a predictive distribution for *this* year's
  total conditioned on what has fallen so far — a data-driven Bayesian update.
  Before the season starts (no in-season signal) we fall back to the
  climatological full-season distribution (the prior).

Probabilities are read off the resulting Normal(mu, sd) against the
climatological "normal" (historical mean full-season total).
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import FeaturesDaily, Location

SEASON = (settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY,
          settings.MONSOON_END_MONTH, settings.MONSOON_END_DAY)


def _normal_cdf(x: float, mu: float, sd: float) -> float:
    if sd <= 0:
        return 0.0 if x < mu else 1.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sd * math.sqrt(2.0))))


def _rain_by_year(db: Session, location_id: int) -> dict[int, dict[date, float]]:
    rows = db.execute(
        select(FeaturesDaily.obs_date, FeaturesDaily.rainfall_mm)
        .where(FeaturesDaily.location_id == location_id)
        .order_by(FeaturesDaily.obs_date)
    ).all()
    by_year: dict[int, dict[date, float]] = defaultdict(dict)
    for d, rain in rows:
        by_year[d.year][d] = rain or 0.0
    return by_year


def _season_sum(days: dict[date, float], year: int, upto_md: tuple[int, int] | None) -> float:
    """Sum rainfall from Jun 1 to Sep 30 (or to upto_md month/day) of `year`."""
    sm, sd, em, ed = SEASON
    start = date(year, sm, sd)
    end = date(year, em, ed)
    if upto_md is not None:
        cap = date(year, upto_md[0], min(upto_md[1], 28 if upto_md[0] == 2 else 31))
        if cap < end:
            end = cap
    total = 0.0
    for d, r in days.items():
        if start <= d <= end:
            total += r
    return total


def compute(db: Session, location_id: int | None = None) -> dict | None:
    loc = db.execute(
        select(Location).where(Location.code == settings.PRIMARY_CODE)
    ).scalar_one_or_none()
    if loc is None:
        return None
    location_id = loc.id

    latest = db.execute(
        select(FeaturesDaily.obs_date)
        .where(FeaturesDaily.location_id == location_id, FeaturesDaily.rainfall_mm.isnot(None))
        .order_by(FeaturesDaily.obs_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return None

    sm, sd_, em, ed = SEASON
    cur_year = latest.year if (latest.month, latest.day) >= (sm, sd_) else latest.year - 1
    in_season = date(cur_year, sm, sd_) <= latest <= date(cur_year, em, ed)
    upto_md = (latest.month, latest.day) if in_season else None

    by_year = _rain_by_year(db, location_id)

    # Historical full-season totals + to-date totals at the same progress point.
    full_totals: list[float] = []
    pairs: list[tuple[float, float]] = []
    for y, days in by_year.items():
        if y >= cur_year:
            continue
        # require a reasonably complete season
        full = _season_sum(days, y, None)
        if full <= 0:
            continue
        full_totals.append(full)
        if upto_md is not None:
            to_date = _season_sum(days, y, upto_md)
            pairs.append((to_date, full))

    if len(full_totals) < 5:
        return None

    normal = statistics.fmean(full_totals)
    prior_sd = statistics.pstdev(full_totals) if len(full_totals) > 1 else normal * 0.2

    to_date_now = _season_sum(by_year.get(cur_year, {}), cur_year, upto_md) if in_season else 0.0

    method = "climatology_prior"
    mu, sd = normal, prior_sd
    slope = None

    if in_season and len(pairs) >= 8:
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        xbar, ybar = statistics.fmean(xs), statistics.fmean(ys)
        sxx = sum((x - xbar) ** 2 for x in xs)
        if sxx > 0:
            slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
            intercept = ybar - slope * xbar
            resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
            n = len(pairs)
            resid_sd = math.sqrt(sum(r * r for r in resid) / max(n - 2, 1))
            mu = intercept + slope * to_date_now
            sd = max(resid_sd, normal * 0.03)  # floor to avoid overconfidence
            method = "analog_regression"

    def p_gt(thresh: float) -> float:
        return round(1.0 - _normal_cdf(thresh, mu, sd), 4)

    def p_lt(thresh: float) -> float:
        return round(_normal_cdf(thresh, mu, sd), 4)

    return {
        "as_of": latest,
        "location_id": location_id,
        "scope": "seasonal",
        "season_year": cur_year,
        "in_season": in_season,
        "normal_mm": round(normal, 1),
        "expected_season_mm": round(mu, 1),
        "posterior_sd_mm": round(sd, 1),
        "season_to_date_mm": round(to_date_now, 1),
        "p_above_norm": p_gt(normal),
        "p_below_norm": p_lt(normal),
        "p_above_10": p_gt(1.10 * normal),
        "p_above_20": p_gt(1.20 * normal),
        "p_below_10": p_lt(0.90 * normal),
        "p_below_20": p_lt(0.80 * normal),
        "posterior_params": {
            "mu": round(mu, 2), "sd": round(sd, 2), "normal": round(normal, 2),
            "method": method, "n_years": len(full_totals), "n_pairs": len(pairs),
            "slope": round(slope, 4) if slope is not None else None,
            "prior_sd": round(prior_sd, 2),
        },
    }
