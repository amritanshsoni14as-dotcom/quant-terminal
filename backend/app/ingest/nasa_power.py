"""NASA POWER connector: daily reanalysis (1981→present, no key).

Provides the variables Open-Meteo's daily archive lacks — humidity & surface
pressure — plus an independent rainfall/temp/wind cross-check.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingest.base import http_get_json, upsert
from app.models.orm import RawWeather

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
SOURCE = "nasa_power"

# POWER parameter -> our column + transform
_PARAMS = {
    "PRECTOTCORR": ("rainfall_mm", lambda v: v),          # mm/day
    "T2M": ("temp_mean_c", lambda v: v),                   # C
    "T2M_MAX": ("temp_max_c", lambda v: v),
    "T2M_MIN": ("temp_min_c", lambda v: v),
    "RH2M": ("humidity_pct", lambda v: v),                 # %
    "PS": ("pressure_hpa", lambda v: v * 10.0),            # kPa -> hPa
    "WS10M": ("wind_kmh", lambda v: v * 3.6),              # m/s -> km/h
}
FILL = -999.0


def fetch_history(db: Session, location_id: int, start: date, end: date) -> int:
    """Backfill in <=10-year chunks (POWER limits very long ranges)."""
    total = 0
    chunk_start = max(start, date(1981, 1, 1))
    while chunk_start <= end:
        chunk_end = min(date(chunk_start.year + 9, 12, 31), end)
        total += _fetch_chunk(db, location_id, chunk_start, chunk_end)
        chunk_start = date(chunk_end.year + 1, 1, 1)
    return total


def _fetch_chunk(db: Session, location_id: int, start: date, end: date) -> int:
    data = http_get_json(
        URL,
        params={
            "parameters": ",".join(_PARAMS.keys()),
            "community": "AG",
            "latitude": settings.PRIMARY_LAT,
            "longitude": settings.PRIMARY_LON,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        },
    )
    param_block = data.get("properties", {}).get("parameter", {})
    # Collect the union of date keys across parameters.
    all_dates: set[str] = set()
    for p in _PARAMS:
        all_dates.update(param_block.get(p, {}).keys())

    rows = []
    for d in sorted(all_dates):
        row = {
            "location_id": location_id,
            "obs_date": date(int(d[0:4]), int(d[4:6]), int(d[6:8])),
            "source": SOURCE,
        }
        for p, (col, transform) in _PARAMS.items():
            raw = param_block.get(p, {}).get(d)
            row[col] = transform(raw) if raw is not None and raw != FILL else None
        rows.append(row)
    return upsert(db, RawWeather, rows, ["location_id", "obs_date", "source"])
