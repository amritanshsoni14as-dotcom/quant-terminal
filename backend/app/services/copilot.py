"""Module 12 — AI Research Copilot.

Answers questions about the terminal's CURRENT state, grounded on a live data
snapshot (signal, probability, drivers, revision, fair value, factors). The LLM
is told to use only the provided data, so answers are explainable, not generic.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import (
    DailyBrief,
    FeaturesDaily,
    Location,
    ProbabilitySnapshot,
    RawClimateDriver,
    RevisionPrediction,
    TradingSignal,
)
from app.services import llm

SYSTEM = (
    "You are the lead research analyst for RAINMUMBAI Terminal, a weather-derivatives "
    "research system that forecasts Mumbai (Santacruz) monsoon rainfall and produces a "
    "trading signal for the NCDEX RAINMUMBAI rainfall contract. Answer the user's question "
    "USING ONLY the DATA SNAPSHOT provided. Be concise and specific, cite the actual numbers, "
    "and explain the 'why'. If the snapshot doesn't contain the answer, say so plainly. "
    "Bullish = more rainfall expected; bearish = less. Do not invent data."
)

SUGGESTED = [
    "Why is the model bearish today?",
    "What are the biggest risks right now?",
    "What factors are contributing most to the signal?",
    "What does the forecast revision engine expect?",
    "How does the current ENSO/IOD state affect the outlook?",
]


def _latest_driver(db: Session, name: str):
    r = db.execute(
        select(RawClimateDriver).where(RawClimateDriver.driver == name, RawClimateDriver.value.isnot(None))
        .order_by(RawClimateDriver.obs_date.desc()).limit(1)
    ).scalar_one_or_none()
    return r.value if r else None


def build_context(db: Session) -> dict:
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if not loc:
        return {}
    brief = db.execute(select(DailyBrief).order_by(DailyBrief.as_of.desc()).limit(1)).scalar_one_or_none()
    sig = db.execute(select(TradingSignal).order_by(TradingSignal.as_of.desc()).limit(1)).scalar_one_or_none()
    prob = db.execute(select(ProbabilitySnapshot).order_by(ProbabilitySnapshot.as_of.desc()).limit(1)).scalar_one_or_none()
    rev = db.execute(select(RevisionPrediction).order_by(RevisionPrediction.as_of.desc()).limit(1)).scalar_one_or_none()
    feat = db.execute(
        select(FeaturesDaily).where(FeaturesDaily.location_id == loc.id, FeaturesDaily.rainfall_mm.isnot(None))
        .order_by(FeaturesDaily.obs_date.desc()).limit(1)
    ).scalar_one_or_none()

    ctx = {
        "as_of": brief.as_of.isoformat() if brief else None,
        "weather": {
            "today_rainfall_mm": feat.rainfall_mm if feat else None,
            "season_to_date_mm": feat.rain_season_cum if feat else None,
            "deviation_vs_normal_pct": feat.rain_anomaly_pct if feat else None,
            "monsoon_progress_pct": round((feat.monsoon_progress or 0) * 100, 1) if feat else None,
        },
        "drivers": {
            "ENSO_ONI": _latest_driver(db, "ONI"),
            "IOD_DMI": _latest_driver(db, "IOD_DMI"),
            "MJO_phase": _latest_driver(db, "MJO_PHASE"),
            "MJO_amplitude": _latest_driver(db, "MJO_AMP"),
        },
        "probability": {
            "expected_season_mm": prob.posterior_params.get("mu") if prob and prob.posterior_params else None,
            "normal_mm": prob.posterior_params.get("normal") if prob and prob.posterior_params else None,
            "p_above_normal": prob.p_above_norm if prob else None,
            "p_below_normal": prob.p_below_norm if prob else None,
        } if prob else None,
        "forecast_revision": {
            "prob_revise_up": rev.prob_revise_up if rev else None,
            "expected_revision_mm": rev.expected_revision_mm if rev else None,
            "confidence": rev.confidence if rev else None,
        } if rev else None,
        "signal": {
            "signal": sig.signal if sig else None,
            "score": sig.score if sig else None,
            "confidence": sig.confidence if sig else None,
            "components": sig.components if sig else None,
        } if sig else None,
        "fair_value": brief.fair_value if brief else None,
        "bullish_factors": brief.bullish_factors if brief else None,
        "bearish_factors": brief.bearish_factors if brief else None,
    }
    return ctx


def _render_compact(ctx: dict) -> str:
    """Compact text snapshot — far fewer tokens than raw JSON, so CPU inference
    is much faster."""
    d = ctx.get("drivers", {})
    p = ctx.get("probability") or {}
    r = ctx.get("forecast_revision") or {}
    s = ctx.get("signal") or {}
    w = ctx.get("weather", {})
    comps = ""
    if s.get("components"):
        comps = "; ".join(f"{c['label']} {c['contribution']:+.2f} ({c['detail']})"
                          for c in s["components"])
    bull = "; ".join(f.get("label", "") for f in (ctx.get("bullish_factors") or []))
    bear = "; ".join(f.get("label", "") for f in (ctx.get("bearish_factors") or []))
    return (
        f"Date: {ctx.get('as_of')}. Location: Mumbai (Santacruz).\n"
        f"SIGNAL: {s.get('signal')} (score {s.get('score')}, confidence {s.get('confidence')}).\n"
        f"Signal components: {comps}\n"
        f"PROBABILITY: expected season {p.get('expected_season_mm')}mm vs normal {p.get('normal_mm')}mm; "
        f"P(above-normal)={p.get('p_above_normal')}, P(below)={p.get('p_below_normal')}.\n"
        f"FORECAST REVISION: P(revise up)={r.get('prob_revise_up')}, expected {r.get('expected_revision_mm')}mm, "
        f"confidence {r.get('confidence')}.\n"
        f"DRIVERS: ENSO/ONI={d.get('ENSO_ONI')}, IOD/DMI={d.get('IOD_DMI')}, "
        f"MJO phase={d.get('MJO_phase')} amp={d.get('MJO_amplitude')}.\n"
        f"WEATHER: season-to-date {w.get('season_to_date_mm')}mm, deviation {w.get('deviation_vs_normal_pct')}% vs normal, "
        f"monsoon {w.get('monsoon_progress_pct')}% complete.\n"
        f"FAIR VALUE: {ctx.get('fair_value')}. Top bullish: {bull or 'none'}. Top bearish: {bear or 'none'}."
    )


def answer(db: Session, question: str) -> dict:
    ctx = build_context(db)
    if not ctx:
        return {"answer": "No data available yet — run the daily refresh first.", "available": False}

    prompt = (
        f"DATA SNAPSHOT:\n{_render_compact(ctx)}\n\n"
        f"QUESTION: {question}\n\nAnswer in 3-5 sentences using only the snapshot. Cite the numbers."
    )
    try:
        text = llm.generate(prompt, system=SYSTEM, temperature=0.2, max_tokens=320)
    except Exception as exc:  # noqa: BLE001
        return {"answer": f"The local AI model is not reachable ({exc}). "
                          f"Check that Ollama is running.", "available": False, "error": str(exc)}
    return {"answer": text, "available": True, "as_of": ctx.get("as_of"),
            "engine": llm.status().get("model")}
