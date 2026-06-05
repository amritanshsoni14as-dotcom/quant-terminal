"""Module 11 (Alt-Data) + Module 12 (AI Copilot) API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import copilot as copilot_svc
from app.services import llm
from app.services import news as news_svc

router = APIRouter(tags=["Module 11 / 12 — Alt-Data & AI Copilot"])


@router.get("/ai/status")
def ai_status():
    return llm.status()


class Question(BaseModel):
    question: str


@router.get("/copilot/suggested")
def suggested():
    return {"suggested": copilot_svc.SUGGESTED, "engine": llm.status()}


@router.post("/copilot")
def copilot(q: Question, db: Session = Depends(get_db)):
    return copilot_svc.answer(db, q.question.strip())


@router.get("/altdata")
def altdata(db: Session = Depends(get_db)):
    return news_svc.latest(db)


@router.post("/altdata/refresh")
def altdata_refresh(db: Session = Depends(get_db)):
    return news_svc.refresh(db)
