"""Module 2 — Rainfall Derivative Monitor API.

Model-derived fair value now; market price + mispricing populate automatically
once contract prices are ingested (CSV via app/ingest/ncdex.py, or POST below).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.ingest.base import upsert
from app.models.orm import ContractFairValue, ContractPrice, ContractSpec
from app.signals.fairvalue import payoff

router = APIRouter(prefix="/derivative", tags=["Module 2 — Derivative Monitor"])
SYMBOL = "RAINMUMBAI"


@router.get("/spec")
def spec(db: Session = Depends(get_db)):
    s = db.execute(select(ContractSpec).where(ContractSpec.symbol == SYMBOL)).scalar_one_or_none()
    if s is None:
        return {"available": False}
    return {
        "available": True, "symbol": s.symbol, "description": s.description,
        "accrual_start": s.accrual_start.isoformat() if s.accrual_start else None,
        "accrual_end": s.accrual_end.isoformat() if s.accrual_end else None,
        "payoff_type": s.payoff_type, "payoff_params": s.payoff_params, "lot_size": s.lot_size,
    }


@router.get("/fair-value")
def fair_value(db: Session = Depends(get_db)):
    fv = db.execute(
        select(ContractFairValue)
        .where(ContractFairValue.symbol == SYMBOL)
        .order_by(ContractFairValue.as_of.desc())
        .limit(1)
    ).scalar_one_or_none()
    if fv is None:
        return {"available": False, "reason": "run `python -m app.signals.run`"}

    s = db.execute(select(ContractSpec).where(ContractSpec.symbol == SYMBOL)).scalar_one_or_none()
    # Payoff curve for charting.
    curve = []
    if s:
        mu = (fv.inputs or {}).get("mu", fv.expected_settle or 0)
        lo, hi = max(0, mu * 0.4), mu * 1.6 if mu else 3000
        for i in range(61):
            idx = lo + (hi - lo) * i / 60
            curve.append({"index": round(idx, 1), "payoff": round(payoff(idx, s.payoff_type or "index_linear", s.payoff_params or {}), 2)})

    return {
        "available": True, "as_of": fv.as_of.isoformat(),
        "fair_value": fv.fair_value, "expected_settle": fv.expected_settle,
        "market_price": fv.market_price, "mispricing": fv.mispricing,
        "has_market_data": fv.market_price is not None,
        "inputs": fv.inputs, "payoff_curve": curve,
    }


@router.get("/prices")
def prices(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ContractPrice).where(ContractPrice.symbol == SYMBOL).order_by(ContractPrice.trade_date)
    ).scalars().all()
    return {
        "count": len(rows),
        "series": [
            {"date": r.trade_date.isoformat(), "close": r.close_price, "settle": r.settle_price,
             "oi": r.open_interest, "volume": r.volume}
            for r in rows
        ],
    }


class PriceRow(BaseModel):
    trade_date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    settle: float | None = None
    open_interest: float | None = None
    volume: float | None = None


@router.post("/prices")
def add_prices(rows: list[PriceRow], db: Session = Depends(get_db)):
    """Plug-in seam: ingest RAINMUMBAI prices as JSON (mirrors the CSV importer)."""
    payload = [{
        "symbol": SYMBOL, "trade_date": r.trade_date, "open_price": r.open, "high_price": r.high,
        "low_price": r.low, "close_price": r.close, "settle_price": r.settle,
        "open_interest": r.open_interest, "volume": r.volume, "source": "api",
    } for r in rows]
    n = upsert(db, ContractPrice, payload, ["symbol", "trade_date"])
    return {"ingested": n, "note": "re-run signals to refresh mispricing"}
