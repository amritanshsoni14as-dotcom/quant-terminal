"""Module 4 — Satellite Intelligence.

Two parts, both from free/no-key sources:
  1. Live satellite imagery via NASA GIBS snapshots (true-colour clouds over the
     Arabian Sea / Bay of Bengal, and precipitation over Mumbai). Images are
     validated against GIBS before use and the last-known-good set is persisted
     so the panel survives a NASA outage.
  2. Three operational scores (0-100) derived transparently from the Open-Meteo
     hourly forecast: cloud intensity, rain probability, storm risk.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from app.core.config import settings
from app.ingest.base import http_get_json

GIBS = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
LAT, LON = settings.PRIMARY_LAT, settings.PRIMARY_LON

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data"
_CACHE_FILE = _CACHE_DIR / "satellite_cache.json"
_log = logging.getLogger(__name__)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _gibs_url(layers: str, bbox: tuple[float, float, float, float], day: str, w=640, h=512) -> str:
    s, west, n, e = bbox
    return (f"{GIBS}?REQUEST=GetSnapshot&LAYERS={layers}&CRS=EPSG:4326"
            f"&TIME={day}&BBOX={s},{west},{n},{e}&FORMAT=image/jpeg&WIDTH={w}&HEIGHT={h}")


def _read_cache() -> dict | None:
    try:
        if _CACHE_FILE.exists():
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _log.warning("satellite cache read failed: %s", exc)
    return None


def _write_cache(payload: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _log.warning("satellite cache write failed: %s", exc)


def _verify_url(url: str, timeout: int = 8) -> bool:
    """Confirm GIBS will actually serve image bytes for this URL.

    HEAD is unreliable for GIBS, so we issue a GET with a Range header to fetch
    just the first 256 bytes — enough to confirm a 200 + image content-type.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"Range": "bytes=0-255"})
            if resp.status_code not in (200, 206):
                return False
            ct = resp.headers.get("content-type", "").lower()
            return "image" in ct
    except Exception:
        return False


def _build_layer_image(title: str, subtitle: str, layers: str,
                       bbox: tuple[float, float, float, float],
                       preferred_day: str, w: int, h: int,
                       max_lookback_days: int = 6) -> tuple[dict, bool]:
    """Build one image dict, walking back day-by-day if GIBS refuses today's tile.

    Returns (image_dict, verified). `verified=True` means we confirmed the URL
    serves valid imagery; `False` means we couldn't reach GIBS at all and the
    URL is best-effort.
    """
    day_dt = datetime.strptime(preferred_day, "%Y-%m-%d")
    for offset in range(max_lookback_days + 1):
        day = (day_dt - timedelta(days=offset)).strftime("%Y-%m-%d")
        url = _gibs_url(layers, bbox, day, w, h)
        if _verify_url(url):
            return ({
                "title": title,
                "subtitle": subtitle + (f" · {day} (t-{offset}d)" if offset else f" · {day}"),
                "url": url,
            }, True)
    # All attempts failed — return best-effort today URL, caller may swap to cache.
    return ({
        "title": title,
        "subtitle": subtitle + f" · {preferred_day} (unverified)",
        "url": _gibs_url(layers, bbox, preferred_day, w, h),
    }, False)


_LAYER_SPECS = [
    {
        "key": "viirs_cloud",
        "title": "Cloud cover — Arabian Sea & Bay of Bengal (true colour)",
        "subtitle": "VIIRS, monsoon systems & rain bands",
        "layers": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        "bbox": (5, 60, 26, 95),
        "w": 720, "h": 512,
        "preferred_offset": 1,
    },
    {
        "key": "imerg_precip",
        "title": "Precipitation over Mumbai region",
        "subtitle": "GPM IMERG rain rate over true colour (gap-filled VIIRS base)",
        # VIIRS_SNPP is a gap-free daily composite at Indian latitudes — replaces
        # MODIS_Terra which left a polar-orbit swath gap on the right side.
        "layers": "VIIRS_SNPP_CorrectedReflectance_TrueColor,IMERG_Precipitation_Rate",
        "bbox": (13, 67, 23, 77),
        "w": 640, "h": 512,
        "preferred_offset": 2,
    },
]


def _build_validated_images() -> tuple[list[dict], bool]:
    """Build today's images, verifying each against GIBS.

    Returns (images, all_verified). When `all_verified` is False the caller
    should consider falling back to the persisted last-known-good set.
    """
    today = datetime.utcnow()
    images = []
    all_ok = True
    for spec in _LAYER_SPECS:
        preferred = (today - timedelta(days=spec["preferred_offset"])).strftime("%Y-%m-%d")
        img, ok = _build_layer_image(
            spec["title"], spec["subtitle"], spec["layers"], spec["bbox"],
            preferred, spec["w"], spec["h"],
        )
        img["key"] = spec["key"]
        images.append(img)
        all_ok = all_ok and ok
    return images, all_ok


def _gibs_images() -> tuple[list[dict], str]:
    """Return (images, freshness) — fresh if GIBS verifies, cached otherwise.

    On verified fetch the result is persisted so a later NASA outage falls
    back to the last imagery that actually rendered.
    """
    images, ok = _build_validated_images()
    cache = _read_cache() or {}
    if ok:
        payload = {
            "images": images,
            "saved_at": datetime.utcnow().isoformat() + "Z",
        }
        _write_cache(payload)
        return images, "live"
    cached = cache.get("images")
    if cached:
        # Annotate cached subtitles so the user sees this is the last-known-good set.
        saved = cache.get("saved_at", "earlier")
        for c in cached:
            if "(cached" not in c.get("subtitle", ""):
                c["subtitle"] = f"{c.get('subtitle', '')} · (cached from {saved[:10]})"
        return cached, "cached"
    return images, "unverified"


def compute() -> dict:
    # NASA GIBS imagery is always returned — it's served by a separate API,
    # so the panel still works even if Open-Meteo is rate-limited.
    img_day = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    images, freshness = _gibs_images()
    base = {
        "available": True,
        "imagery_date": img_day,
        "imagery_freshness": freshness,  # "live" | "cached" | "unverified"
        "location": {"name": settings.PRIMARY_NAME, "lat": LAT, "lon": LON},
        "images": images,
    }

    # Hourly forecast for the scores (Open-Meteo) — optional enrichment.
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
        # Imagery still ships; scores/series degrade gracefully.
        base["scores_note"] = f"forecast unavailable ({exc})"
        return base

    h = data.get("hourly", {})
    times = h.get("time", [])
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
    f_precip = _clamp(max(precip24, default=0) / 15.0 * 100)
    f_wind = _clamp(max(wind24, default=0) / 60.0 * 100)
    f_press = _clamp((1008.0 - (min(press24, default=1008))) / 15.0 * 100)
    storm_score = _clamp(0.45 * f_precip + 0.35 * f_wind + 0.20 * f_press)

    series = []
    for i in range(start, min(start + 48, len(times))):
        series.append({
            "time": times[i][11:16] if len(times[i]) >= 16 else times[i],
            "date": times[i][:10],
            "cloud": h.get("cloud_cover", [None] * len(times))[i],
            "rain_prob": h.get("precipitation_probability", [None] * len(times))[i],
            "precip": h.get("precipitation", [None] * len(times))[i],
        })

    base["scores"] = {
        "cloud_intensity": round(cloud_score, 0),
        "rain_probability": round(rain_score, 0),
        "storm_risk": round(storm_score, 0),
    }
    base["score_inputs"] = {
        "max_rain_prob_24h": max(prob24, default=0),
        "max_precip_mm_24h": round(max(precip24, default=0), 1),
        "max_wind_kmh_24h": round(max(wind24, default=0), 0),
        "min_pressure_hpa_24h": round(min(press24, default=0), 0),
    }
    base["hourly"] = series
    return base
