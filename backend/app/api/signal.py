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
def signal_history(limit: int = Query(2000, ge=1, le=20000), db: Session = Depends(get_db)):
    """Full track record — every daily signal the model has produced from inception.

    Reads the persisted `trading_signals` table (one row per as_of date) so the
    journal stays complete even if the in-process SignalLog is empty after a
    fresh deploy. `prev_signal` and `event_type` are computed on the fly so the
    UI shows every state transition.
    """
    rows = db.execute(
        select(TradingSignal).where(TradingSignal.symbol == SYMBOL)
        .order_by(TradingSignal.as_of.asc())
    ).scalars().all()

    entries = []
    prev = None
    for r in rows:
        event = "first" if prev is None else ("change" if r.signal != prev else "same")
        entries.append({
            "logged_at": r.as_of.isoformat(),
            "as_of": r.as_of.isoformat(),
            "signal": r.signal,
            "prev_signal": prev,
            "score": r.score,
            "confidence": r.confidence,
            "event_type": event,
        })
        prev = r.signal

    entries.reverse()  # newest first for the UI
    if limit < len(entries):
        entries = entries[:limit]
    return {"available": True, "count": len(entries), "entries": entries}


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
