"""Module 9 — Trading Signal API + Final Daily Brief."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import DailyBrief, TradingSignal

router = APIRouter(tags=["Module 9 — Trading Signal / Brief"])
SYMBOL = "RAINMUMBAI"


@router.get("/signal")
def signal(db: Session = Depends(get_db)):
    s = db.execute(
        select(TradingSignal).where(TradingSignal.symbol == SYMBOL)
        .order_by(TradingSignal.as_of.desc()).limit(1)
    ).scalar_one_or_none()
    if s is None:
        return {"available": False, "reason": "run `python -m app.signals.run`"}
    return {
        "available": True, "as_of": s.as_of.isoformat(), "signal": s.signal,
        "score": s.score, "confidence": s.confidence, "components": s.components,
    }


@router.get("/brief")
def brief(db: Session = Depends(get_db)):
    b = db.execute(
        select(DailyBrief).where(DailyBrief.symbol == SYMBOL)
        .order_by(DailyBrief.as_of.desc()).limit(1)
    ).scalar_one_or_none()
    if b is None:
        return {"available": False, "reason": "run `python -m app.signals.run`"}
    return {
        "available": True, "as_of": b.as_of.isoformat(), "symbol": b.symbol,
        "rainfall_forecast": b.rainfall_forecast, "confidence_score": b.confidence_score,
        "revision_probability": b.revision_probability, "expected_season_mm": b.expected_season_mm,
        "fair_value": b.fair_value, "signal": b.signal,
        "bullish_factors": b.bullish_factors, "bearish_factors": b.bearish_factors,
    }
