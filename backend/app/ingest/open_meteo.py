"""Open-Meteo connector: historical daily weather + forward forecast.

Archive API → observed daily rainfall/temp/wind (1940→present, no key).
Forecast API → next 16 days (used later by the revision engine).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingest.base import http_get_json, upsert
from app.models.orm import RawWeather, RawWeatherForecast

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = "open_meteo"

_DAILY_VARS = [
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "wind_speed_10m_max",
]


def fetch_history(db: Session, location_id: int, start: date, end: date) -> int:
    """Backfill observed daily weather for [start, end]."""
    data = http_get_json(
        ARCHIVE_URL,
        params={
            "latitude": settings.PRIMARY_LAT,
            "longitude": settings.PRIMARY_LON,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": ",".join(_DAILY_VARS),
            "timezone": "auto",
        },
    )
    daily = data.get("daily", {})
    times = daily.get("time", [])
    rows = []
    for i, t in enumerate(times):
        rows.append(
            {
                "location_id": location_id,
                "obs_date": date.fromisoformat(t),
                "source": SOURCE,
                "rainfall_mm": _at(daily, "precipitation_sum", i),
                "temp_max_c": _at(daily, "temperature_2m_max", i),
                "temp_min_c": _at(daily, "temperature_2m_min", i),
                "temp_mean_c": _at(daily, "temperature_2m_mean", i),
                "wind_kmh": _at(daily, "wind_speed_10m_max", i),
            }
        )
    return upsert(db, RawWeather, rows, ["location_id", "obs_date", "source"])


def fetch_recent(db: Session, location_id: int, past_days: int = 14) -> int:
    """Near-real-time recent observations (incl. today) via the forecast endpoint's
    `past_days`. The archive API lags ~2-5 days; this fills the gap so the dashboard
    shows the current day. The latest day is provisional until the archive catches up."""
    data = http_get_json(
        FORECAST_URL,
        params={
            "latitude": settings.PRIMARY_LAT,
            "longitude": settings.PRIMARY_LON,
            "daily": ",".join(_DAILY_VARS),
            "past_days": past_days,
            "forecast_days": 1,
            "timezone": "auto",
        },
    )
    daily = data.get("daily", {})
    times = daily.get("time", [])
    rows = [
        {
            "location_id": location_id,
            "obs_date": date.fromisoformat(t),
            "source": SOURCE,
            "rainfall_mm": _at(daily, "precipitation_sum", i),
            "temp_max_c": _at(daily, "temperature_2m_max", i),
            "temp_min_c": _at(daily, "temperature_2m_min", i),
            "temp_mean_c": _at(daily, "temperature_2m_mean", i),
            "wind_kmh": _at(daily, "wind_speed_10m_max", i),
        }
        for i, t in enumerate(times)
    ]
    return upsert(db, RawWeather, rows, ["location_id", "obs_date", "source"])


def fetch_forecast(db: Session, location_id: int, days: int = 16) -> int:
    """Pull the current forward forecast (versioned by issued_at)."""
    data = http_get_json(
        FORECAST_URL,
        params={
            "latitude": settings.PRIMARY_LAT,
            "longitude": settings.PRIMARY_LON,
            "daily": "precipitation_sum,temperature_2m_mean",
            "forecast_days": days,
            "timezone": "auto",
        },
    )
    issued_at = datetime.utcnow()
    daily = data.get("daily", {})
    times = daily.get("time", [])
    rows = [
        {
            "location_id": location_id,
            "issued_at": issued_at,
            "target_date": date.fromisoformat(t),
            "source": SOURCE,
            "rainfall_mm": _at(daily, "precipitation_sum", i),
            "temp_mean_c": _at(daily, "temperature_2m_mean", i),
        }
        for i, t in enumerate(times)
    ]
    return upsert(
        db, RawWeatherForecast, rows, ["location_id", "issued_at", "target_date", "source"]
    )


def _at(daily: dict, key: str, i: int):
    arr = daily.get(key)
    if not arr or i >= len(arr):
        return None
    return arr[i]
