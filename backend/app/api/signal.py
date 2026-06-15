"""Module 9 — Trading Signal API + Final Daily Brief."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import DailyBrief, SignalLog, TradingSignal

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


@router.get("/signal/history")
def signal_history(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    """Append-only journal of every signal change the model has made."""
    rows = db.execute(
        select(SignalLog).where(SignalLog.symbol == SYMBOL)
        .order_by(SignalLog.logged_at.desc()).limit(limit)
    ).scalars().all()
    return {
        "available": True,
        "count": len(rows),
        "entries": [{
            "logged_at": r.logged_at.isoformat() if r.logged_at else None,
            "as_of": r.as_of.isoformat(),
            "signal": r.signal,
            "prev_signal": r.prev_signal,
            "score": r.score,
            "confidence": r.confidence,
            "event_type": r.event_type,
        } for r in rows],
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
