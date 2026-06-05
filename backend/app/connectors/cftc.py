"""CFTC Commitments of Traders (COT) connector — FREE, no key.

For every config indicator whose source is {"cftc": {"code": "<contract code>"}},
fetch the disaggregated futures-only report and store net managed-money positioning
(long − short) into fundamental_series under (symbol, indicator.key).
"""
from __future__ import annotations

from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.core import config_registry
from app.ingest.base import upsert
from app.models.orm import FundamentalSeries

URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
_UA = "Mozilla/5.0 (commodity-intel research)"


def _fetch_code(code: str, limit: int = 800) -> list[dict]:
    with httpx.Client(timeout=40, headers={"User-Agent": _UA}, follow_redirects=True) as c:
        r = c.get(URL, params={
            "cftc_contract_market_code": code,
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": limit,
        })
        r.raise_for_status()
        return r.json()


def refresh(db: Session) -> dict:
    out = {}
    for cfg in config_registry.load_all().values():
        sym = cfg["symbol"]
        for ind in cfg.get("indicators", []):
            src = ind.get("source", {})
            code = src.get("cftc", {}).get("code") if isinstance(src.get("cftc"), dict) else None
            if not code:
                continue
            try:
                rows = _fetch_code(code)
            except Exception as exc:  # noqa: BLE001
                out[f"{sym}:{ind['key']}"] = f"error: {exc}"
                continue
            recs = []
            for r in rows:
                try:
                    d = datetime.fromisoformat(r["report_date_as_yyyy_mm_dd"].replace("Z", "")).date()
                    net = float(r["m_money_positions_long_all"]) - float(r["m_money_positions_short_all"])
                except (KeyError, ValueError, TypeError):
                    continue
                recs.append({"symbol": sym, "key": ind["key"], "obs_date": d,
                             "value": net, "source": "cftc"})
            n = upsert(db, FundamentalSeries, recs, ["symbol", "key", "obs_date"])
            out[f"{sym}:{ind['key']}"] = n
    return out
