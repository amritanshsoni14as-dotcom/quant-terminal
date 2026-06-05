"""Multi-commodity API — Command Center (Phase C1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import markets

router = APIRouter(prefix="/commodities", tags=["Commodities — Markets"])


@router.get("")
def list_commodities(db: Session = Depends(get_db)):
    return {"commodities": markets.list_assets(db)}


@router.get("/{symbol}/summary")
def summary(symbol: str, db: Session = Depends(get_db)):
    return markets.summary(db, symbol)


@router.get("/{symbol}/prices")
def prices(symbol: str, days: int = Query(260, ge=20, le=3000), db: Session = Depends(get_db)):
    return markets.prices(db, symbol, days)


@router.get("/{symbol}/technicals")
def technicals(symbol: str, db: Session = Depends(get_db)):
    return markets.technicals(db, symbol)
