"""Shared per-season climate aggregates for Monsoon Intelligence (Module 3)
and Scenario Analysis (Module 10).

For each monsoon year produces: seasonal (Jun–Sep) rainfall, June rainfall,
JJA-mean ONI (ENSO), Jun–Oct-mean IOD (DMI), and derived regime states.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import Location, RawClimateDriver
from app.signals.probability import _rain_by_year, _season_sum


@dataclass
class SeasonRow:
    year: int
    season_mm: float
    june_mm: float
    jja_oni: float | None
    season_dmi: float | None
    enso_state: str | None
    iod_state: str | None


def _monthly(db: Session, driver: str) -> dict[tuple[int, int], float]:
    out: dict[tuple[int, int], float] = {}
    for r in db.execute(
        select(RawClimateDriver).where(RawClimateDriver.driver == driver, RawClimateDriver.value.isnot(None))
    ).scalars():
        out[(r.obs_date.year, r.obs_date.month)] = r.value
    return out


def _mean(vals: list[float]) -> float | None:
    vals = [v for v in vals if v is not None]
    return statistics.fmean(vals) if vals else None


def enso_state(oni: float | None) -> str | None:
    if oni is None:
        return None
    return "El Niño" if oni >= 0.5 else "La Niña" if oni <= -0.5 else "Neutral"


def iod_state(dmi: float | None) -> str | None:
    if dmi is None:
        return None
    return "Positive" if dmi >= 0.4 else "Negative" if dmi <= -0.4 else "Neutral"


def build(db: Session) -> tuple[list[SeasonRow], float, float]:
    """Return (season rows for complete seasons, normal seasonal mm, latest year)."""
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return [], 0.0, 0
    by_year = _rain_by_year(db, loc.id)
    oni = _monthly(db, "ONI")
    dmi = _monthly(db, "IOD_DMI")

    latest_year = max(by_year) if by_year else 0
    rows: list[SeasonRow] = []
    for y in sorted(by_year):
        days = by_year[y]
        season = _season_sum(days, y, None)
        if season <= 0:
            continue
        june = sum(r for d, r in days.items() if d.month == 6 and (d - date(y, 6, 1)).days >= 0 and d <= date(y, 6, 30))
        jja_oni = _mean([oni.get((y, m)) for m in (6, 7, 8)])
        season_dmi = _mean([dmi.get((y, m)) for m in (6, 7, 8, 9, 10)])
        rows.append(SeasonRow(
            year=y, season_mm=season, june_mm=june, jja_oni=jja_oni, season_dmi=season_dmi,
            enso_state=enso_state(jja_oni), iod_state=iod_state(season_dmi),
        ))
    normal = statistics.fmean([r.season_mm for r in rows]) if rows else 0.0
    return rows, normal, latest_year


def pearson(xs: list[float], ys: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xm = statistics.fmean([p[0] for p in pairs])
    ym = statistics.fmean([p[1] for p in pairs])
    num = sum((x - xm) * (y - ym) for x, y in pairs)
    dx = sum((x - xm) ** 2 for x, _ in pairs) ** 0.5
    dy = sum((y - ym) ** 2 for _, y in pairs) ** 0.5
    return round(num / (dx * dy), 3) if dx > 0 and dy > 0 else None
