"""EIA energy-data connector — needs a FREE key (EIA_API_KEY). Dormant until set.

For config indicators with source {"eia": {"series_id": "PET.WCESTUS1.W"}} fetches
the series and stores it in fundamental_series under (symbol, indicator.key).
"""
from __future__ import annotations

from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.core import config_registry
from app.core.config import settings
from app.ingest.base import upsert
from app.models.orm import FundamentalSeries


def available() -> bool:
    return bool(settings.EIA_API_KEY)


def _fetch(series_id: str) -> list[dict]:
    url = f"https://api.eia.gov/v2/seriesid/{series_id}"
    with httpx.Client(timeout=40, follow_redirects=True) as c:
        r = c.get(url, params={"api_key": settings.EIA_API_KEY})
        r.raise_for_status()
        return r.json().get("response", {}).get("data", [])


def _parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def refresh(db: Session) -> dict:
    if not available():
        return {"skipped": "EIA_API_KEY not set"}
    out = {}
    for cfg in config_registry.load_all().values():
        sym = cfg["symbol"]
        for ind in cfg.get("indicators", []):
            sid = (ind.get("source", {}).get("eia") or {}).get("series_id")
            if not sid:
                continue
            try:
                data = _fetch(sid)
            except Exception as exc:  # noqa: BLE001
                out[f"{sym}:{ind['key']}"] = f"error: {exc}"
                continue
            recs = []
            for row in data:
                d = _parse_date(str(row.get("period", "")))
                val = row.get("value")
                if d is None or val is None:
                    continue
                try:
                    recs.append({"symbol": sym, "key": ind["key"], "obs_date": d,
                                 "value": float(val), "source": "eia"})
                except (ValueError, TypeError):
                    continue
            out[f"{sym}:{ind['key']}"] = upsert(db, FundamentalSeries, recs, ["symbol", "key", "obs_date"])
    return out
