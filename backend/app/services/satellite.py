"""Module 4 — Satellite Intelligence.

Two parts, both from free/no-key sources:
  1. Live satellite imagery via NASA GIBS snapshots (true-colour clouds over the
     Arabian Sea / Bay of Bengal, and precipitation over Mumbai).
  2. Three operational scores (0-100) derived transparently from the Open-Meteo
     hourly forecast: cloud intensity, rain probability, storm risk.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import settings
from app.ingest.base import http_get_json

GIBS = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
LAT, LON = settings.PRIMARY_LAT, settings.PRIMARY_LON


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _gibs_url(layers: str, bbox: tuple[float, float, float, float], day: str, w=640, h=512) -> str:
    s, west, n, e = bbox
    return (f"{GIBS}?REQUEST=GetSnapshot&LAYERS={layers}&CRS=EPSG:4326"
            f"&TIME={day}&BBOX={s},{west},{n},{e}&FORMAT=image/jpeg&WIDTH={w}&HEIGHT={h}")


def compute() -> dict:
    # Hourly forecast for the scores.
    try:
        data = http_get_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LAT, "longitude": LON,
                "hourly": "cloud_cover,precipitation_probability,precipitation,wind_speed_10m,pressure_msl",
                "forecast_days": 2, "timezone": "auto",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": str(exc)}

    h = data.get("hourly", {})
    times = h.get("time", [])
    # Index of "now" within the hourly series.
    now = datetime.now()
    start = 0
    for i, t in enumerate(times):
        try:
            if datetime.fromisoformat(t) >= now:
                start = i
                break
        except ValueError:
            continue

    def window(key, n):
        arr = h.get(key, [])
        return [v for v in arr[start:start + n] if v is not None]

    cloud24 = window("cloud_cover", 24)
    prob24 = window("precipitation_probability", 24)
    precip24 = window("precipitation", 24)
    wind24 = window("wind_speed_10m", 24)
    press24 = window("pressure_msl", 24)

    cloud_score = _clamp(sum(cloud24) / len(cloud24)) if cloud24 else 0
    rain_score = _clamp(0.6 * max(prob24, default=0) + 0.4 * (sum(prob24) / len(prob24) if prob24 else 0))
    # Storm risk: heavy precip + strong wind + low pressure.
    f_precip = _clamp(max(precip24, default=0) / 15.0 * 100)
    f_wind = _clamp(max(wind24, default=0) / 60.0 * 100)
    f_press = _clamp((1008.0 - (min(press24, default=1008))) / 15.0 * 100)
    storm_score = _clamp(0.45 * f_precip + 0.35 * f_wind + 0.20 * f_press)

    # Imagery date: yesterday (true-colour is reliably processed by then).
    img_day = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    images = [
        {
            "title": "Cloud cover — Arabian Sea & Bay of Bengal (true colour)",
            "subtitle": "VIIRS, monsoon systems & rain bands",
            "url": _gibs_url("VIIRS_SNPP_CorrectedReflectance_TrueColor", (5, 60, 26, 95), img_day, 720, 512),
        },
        {
            "title": "Precipitation over Mumbai region",
            "subtitle": "GPM IMERG rain rate over true colour",
            "url": _gibs_url("MODIS_Terra_CorrectedReflectance_TrueColor,IMERG_Precipitation_Rate",
                             (13, 67, 23, 77), img_day, 640, 512),
        },
    ]

    # Compact hourly series (next 48h) for the chart.
    series = []
    for i in range(start, min(start + 48, len(times))):
        series.append({
            "time": times[i][11:16] if len(times[i]) >= 16 else times[i],
            "date": times[i][:10],
            "cloud": h.get("cloud_cover", [None] * len(times))[i],
            "rain_prob": h.get("precipitation_probability", [None] * len(times))[i],
            "precip": h.get("precipitation", [None] * len(times))[i],
        })

    return {
        "available": True,
        "imagery_date": img_day,
        "location": {"name": settings.PRIMARY_NAME, "lat": LAT, "lon": LON},
        "scores": {
            "cloud_intensity": round(cloud_score, 0),
            "rain_probability": round(rain_score, 0),
            "storm_risk": round(storm_score, 0),
        },
        "score_inputs": {
            "max_rain_prob_24h": max(prob24, default=0),
            "max_precip_mm_24h": round(max(precip24, default=0), 1),
            "max_wind_kmh_24h": round(max(wind24, default=0), 0),
            "min_pressure_hpa_24h": round(min(press24, default=0), 0),
        },
        "images": images,
        "hourly": series,
    }
