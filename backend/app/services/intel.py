"""Commodity Intelligence service — resolves a config's indicators from available
data and runs the generic scoring engine into a Health-Score scorecard.

Phase 1 resolvers (free data): price-derived (trend, momentum, valuation) +
macro assets (DXY, US10Y). Fundamental sources (eia/usda/cftc/usgs/comtrade…)
resolve to None until their connectors land (Phase 2) — and the engine simply
renormalizes over what's available.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config_registry
from app.models.orm import FundamentalSeries
from app.scoring import engine
from app.services import markets


def _closes(db: Session, symbol: str) -> np.ndarray | None:
    a = markets._asset(db, symbol)
    if not a:
        return None
    rows = markets._series(db, a.id)
    if len(rows) < 60:
        return None
    return np.array([r.close for r in rows], dtype=float)


def _zscore_latest(arr: np.ndarray, window: int = 252) -> float | None:
    a = arr[-window:]
    if len(a) < 30 or a.std() == 0:
        return None
    return float((a[-1] - a.mean()) / a.std())


def _fundamental(db: Session, symbol: str, key: str):
    rows = db.execute(
        select(FundamentalSeries.obs_date, FundamentalSeries.value)
        .where(FundamentalSeries.symbol == symbol, FundamentalSeries.key == key,
               FundamentalSeries.value.isnot(None))
        .order_by(FundamentalSeries.obs_date)
    ).all()
    if len(rows) < 8:
        return None, None
    dates = [r[0] for r in rows]
    vals = np.array([r[1] for r in rows], dtype=float)
    return dates, vals


def _normalize(dates, vals, transform: str) -> float | None:
    if transform == "percentile":
        pct = float((vals < vals[-1]).mean())
        return (pct - 0.5) * 2
    if transform == "yoy":
        from datetime import timedelta
        target = dates[-1] - timedelta(days=365)
        prior = next((vals[i] for i in range(len(dates) - 1, -1, -1) if dates[i] <= target), None)
        if prior in (None, 0):
            return None
        return float(max(-1, min(1, (vals[-1] / prior - 1) / 0.25)))
    # default: zscore over history
    if vals.std() == 0:
        return None
    return float(max(-1, min(1, (vals[-1] - vals.mean()) / vals.std() / 2.5)))


def _resolve(db: Session, symbol: str, ind: dict, closes: np.ndarray) -> float | None:
    """Return a normalized value in ~[-1,1], or None if unavailable."""
    source = ind.get("source", {})
    if "derived" in source:
        kind = source["derived"]
        if kind == "trend":
            if len(closes) < 200:
                return None
            sma50, sma200 = closes[-50:].mean(), closes[-200:].mean()
            return float(0.5 * np.sign(closes[-1] - sma50) + 0.5 * np.sign(sma50 - sma200))
        if kind == "momentum":
            rets = closes[21:] / closes[:-21] - 1
            z = _zscore_latest(rets, len(rets))
            return None if z is None else float(max(-1, min(1, z / 2.5)))
        if kind == "price_percentile":
            win = closes[-1260:]
            pct = float((win < win[-1]).mean())
            return (pct - 0.5) * 2  # high price → +1 (engine applies direction)
        return None
    if "macro_asset" in source:
        marr = _closes(db, source["macro_asset"])
        if marr is None:
            return None
        z = _zscore_latest(marr)
        return None if z is None else float(max(-1, min(1, z / 2.5)))
    # Fundamental series (CFTC/EIA/FRED/USDA…) stored under (symbol, indicator key).
    dates, vals = _fundamental(db, symbol, ind["key"])
    if vals is None:
        return None
    return _normalize(dates, vals, ind.get("transform", "zscore"))


def scorecard(db: Session, symbol: str) -> dict:
    cfg = config_registry.get(symbol)
    if not cfg:
        return {"available": False, "reason": "no config"}
    closes = _closes(db, cfg["symbol"])
    if closes is None:
        return {"available": False, "symbol": cfg["symbol"], "reason": "no price data"}

    resolved, indicator_rows = [], []
    for ind in cfg["indicators"]:
        norm = _resolve(db, cfg["symbol"], ind, closes)
        resolved.append({**ind, "normalized": norm})
        indicator_rows.append({
            "key": ind["key"], "label": ind.get("label", ind["key"]),
            "category": ind["category"], "direction": ind.get("direction", 1),
            "available": norm is not None,
            "sub_score": round(max(-1, min(1, ind.get("direction", 1) * norm)), 3) if norm is not None else None,
        })

    result = engine.compute(resolved, cfg["category_weights"])
    summ = markets.summary(db, cfg["symbol"])

    # Risk score 0-100 from annualised vol percentile-ish (higher vol → higher risk).
    vol = summ.get("volatility_annual_pct") if summ.get("available") else None
    risk = round(min(100, (vol / 60.0) * 100)) if vol else None
    # Trend score 0-100 from the technical category.
    tech = next((c for c in result["categories"] if c["category"] == "technical"), None)
    trend_score = round(50 * (tech["score"] + 1)) if tech else None

    return {
        "available": True,
        "symbol": cfg["symbol"], "name": cfg["name"], "category": cfg["category"],
        "unit": cfg.get("unit"), "currency": cfg.get("currency"),
        "as_of": summ.get("as_of") if summ.get("available") else None,
        "price": summ.get("price") if summ.get("available") else None,
        "change_1d": (summ.get("change") or {}).get("1d") if summ.get("available") else None,
        "health": result["health"],
        "composite": result["composite"],
        "verdict": result["verdict"],
        "trend_score": trend_score,
        "risk_score": risk,
        "categories": result["categories"],
        "covered_categories": result["covered_categories"],
        "indicators": indicator_rows,
        "secular": cfg.get("secular"),
        "substitutes": cfg.get("substitutes", []),
        "pending_phase2": cfg.get("pending_phase2", []),
    }


def list_commodities(db: Session) -> list[dict]:
    out = []
    for sym in config_registry.list_symbols():
        sc = scorecard(db, sym)
        out.append({
            "symbol": sym, "name": sc.get("name"), "category": sc.get("category"),
            "health": sc.get("health"), "verdict": sc.get("verdict"),
            "available": sc.get("available", False),
        })
    return sorted(out, key=lambda x: -(x["health"] or 0))
