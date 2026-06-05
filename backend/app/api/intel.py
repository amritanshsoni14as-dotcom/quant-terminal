"""Commodity Intelligence Platform API (Phase 0+1: config-driven scorecard)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors import eia
from app.core import config_registry
from app.core.config import settings
from app.core.db import get_db
from app.services import intel

router = APIRouter(prefix="/intel", tags=["Commodity Intelligence Platform"])


class Question(BaseModel):
    question: str


@router.get("/{symbol}/copilot/suggested")
def copilot_suggested(symbol: str):
    from app.services import intel_copilot
    return {"suggested": intel_copilot.suggested(symbol)}


@router.post("/{symbol}/copilot")
def copilot(symbol: str, q: Question, db: Session = Depends(get_db)):
    from app.services import intel_copilot
    return intel_copilot.answer(db, symbol, q.question.strip())


@router.get("/sources")
def sources():
    """Which fundamental connectors are active (key present) vs dormant."""
    return {
        "cftc_cot": {"active": True, "key_required": False},
        "eia": {"active": bool(settings.EIA_API_KEY), "key_required": True,
                "register": "https://www.eia.gov/opendata/register.php"},
        "fred": {"active": bool(settings.FRED_API_KEY), "key_required": True,
                 "register": "https://fredaccount.stlouisfed.org/apikeys"},
        "usda": {"active": bool(settings.USDA_API_KEY), "key_required": True,
                 "register": "https://quickstats.nass.usda.gov/api"},
    }


@router.post("/refresh-fundamentals")
def refresh_fundamentals(db: Session = Depends(get_db)):
    """Re-pull fundamentals on demand (e.g. right after adding an EIA key)."""
    from app.connectors import cftc
    out = {"cftc": cftc.refresh(db)}
    out["eia"] = eia.refresh(db) if eia.available() else "skipped (no EIA_API_KEY)"
    return out


@router.get("/commodities")
def commodities(db: Session = Depends(get_db)):
    return {"commodities": intel.list_commodities(db)}


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    from app.services import portfolio as pf
    return pf.build(db)


@router.get("/{symbol}/scorecard")
def scorecard(symbol: str, db: Session = Depends(get_db)):
    return intel.scorecard(db, symbol)


@router.get("/{symbol}/forecast")
def forecast(symbol: str, db: Session = Depends(get_db)):
    from app.services import forecast as fc
    return fc.read_latest(db, symbol)


@router.get("/{symbol}/config")
def config(symbol: str):
    cfg = config_registry.get(symbol)
    return cfg or {"available": False}


@router.post("/reload")
def reload_configs():
    cfgs = config_registry.reload()
    return {"reloaded": list(cfgs.keys())}
