"""Module 3 (Monsoon Intelligence) + Module 10 (Scenario Analysis) API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import satellite as satellite_svc
from app.signals import monsoon as monsoon_svc
from app.signals import research as research_svc
from app.signals import scenarios as scenarios_svc

router = APIRouter(tags=["Module 3 / 5 / 10 — Intelligence, Research & Scenarios"])


@router.get("/monsoon")
def monsoon(db: Session = Depends(get_db)):
    return monsoon_svc.compute(db)


@router.get("/scenarios")
def scenarios(db: Session = Depends(get_db)):
    return scenarios_svc.compute(db)


@router.get("/research")
def research(db: Session = Depends(get_db)):
    return research_svc.compute(db)


@router.get("/satellite")
def satellite():
    return satellite_svc.compute()
