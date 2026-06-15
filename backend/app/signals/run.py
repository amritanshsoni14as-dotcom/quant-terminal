"""Phase 2 orchestrator — compute & persist probability, fair value, signal,
and the Daily Brief. Run after features are built.

    python -m app.signals.run
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.ingest.base import get_or_create_location, upsert
from app.models.orm import (
    ContractFairValue,
    ContractSpec,
    DailyBrief,
    FeaturesDaily,
    ProbabilitySnapshot,
    RawWeatherForecast,
    SignalLog,
    TradingSignal,
)
from app.signals import engine, fairvalue, probability, revision

SYMBOL = "RAINMUMBAI"


def ensure_contract_spec(db: Session, location_id: int, normal_mm: float) -> None:
    """Seed a placeholder RAINMUMBAI spec if none exists.

    NOTE: payoff is a stand-in 'rainfall deviation swap' (1 unit per mm vs the
    climatological normal, ±2000 collar) until the real NCDEX spec is supplied.
    Editing `payoff_params` is all that's needed to match the live contract.
    """
    existing = db.execute(
        select(ContractSpec).where(ContractSpec.symbol == SYMBOL)
    ).scalar_one_or_none()
    today = date.today()
    if existing is None:
        db.add(ContractSpec(
            symbol=SYMBOL,
            location_id=location_id,
            description="Mumbai monsoon (Jun–Sep) cumulative rainfall index. PLACEHOLDER payoff "
                        "until real NCDEX spec is provided.",
            accrual_start=date(today.year, settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY),
            accrual_end=date(today.year, settings.MONSOON_END_MONTH, settings.MONSOON_END_DAY),
            payoff_type="index_linear",
            payoff_params={
                "index": "seasonal_cum_mm", "tick": 1.0,
                "strike": round(normal_mm, 1), "floor": -2000.0, "cap": 2000.0,
            },
            lot_size=1.0,
        ))
        db.commit()


def _near_term_forecast(db: Session, location_id: int) -> dict:
    """Sum the latest published Open-Meteo forecast over 1/3/7/15-day windows."""
    latest_issue = db.execute(
        select(RawWeatherForecast.issued_at)
        .where(RawWeatherForecast.location_id == location_id)
        .order_by(RawWeatherForecast.issued_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_issue is None:
        return {}
    rows = db.execute(
        select(RawWeatherForecast.target_date, RawWeatherForecast.rainfall_mm)
        .where(RawWeatherForecast.location_id == location_id,
               RawWeatherForecast.issued_at == latest_issue)
        .order_by(RawWeatherForecast.target_date)
    ).all()
    rains = [(r or 0.0) for _, r in rows]
    out = {}
    for h in (1, 3, 7, 15):
        if len(rains) >= 1:
            out[f"{h}d"] = round(sum(rains[:h]), 1)
    return out


def run() -> dict:
    init_db()
    db = SessionLocal()
    try:
        location_id = get_or_create_location(db)

        prob = probability.compute(db, location_id)
        if prob is None:
            print("[signals] not enough data for probability; aborting.")
            return {}

        ensure_contract_spec(db, location_id, prob["normal_mm"])

        # Probability snapshot
        upsert(db, ProbabilitySnapshot, [{
            "location_id": location_id, "as_of": prob["as_of"], "scope": "seasonal",
            "p_above_norm": prob["p_above_norm"], "p_below_norm": prob["p_below_norm"],
            "p_above_10": prob["p_above_10"], "p_above_20": prob["p_above_20"],
            "p_below_10": prob["p_below_10"], "p_below_20": prob["p_below_20"],
            "posterior_params": prob["posterior_params"],
        }], ["location_id", "as_of", "scope"])

        # Forecast Revision Engine (Module 7 — primary alpha)
        try:
            rev = revision.compute(db)
        except Exception as exc:  # noqa: BLE001
            print(f"[signals] revision engine skipped: {exc}")
            rev = None

        # Fair value
        fair = fairvalue.compute(db, SYMBOL, prob["expected_season_mm"], prob["posterior_sd_mm"])
        if fair:
            upsert(db, ContractFairValue, [{
                "symbol": SYMBOL, "as_of": prob["as_of"],
                "fair_value": fair["fair_value"], "market_price": fair["market_price"],
                "mispricing": fair["mispricing"], "expected_settle": fair["expected_settle"],
                "inputs": fair["inputs"],
            }], ["symbol", "as_of"])

        # Monsoon progress (from latest feature row)
        latest_feat = db.execute(
            select(FeaturesDaily).where(
                FeaturesDaily.location_id == location_id,
                FeaturesDaily.obs_date == prob["as_of"],
            )
        ).scalar_one_or_none()
        progress = latest_feat.monsoon_progress if latest_feat else None

        # Signal (v2 — includes the forecast-revision component)
        sig = engine.compute(db, prob, fair, progress, rev)
        upsert(db, TradingSignal, [{
            "symbol": SYMBOL, "as_of": prob["as_of"], "signal": sig["signal"],
            "score": sig["score"], "confidence": sig["confidence"], "components": sig["components"],
        }], ["symbol", "as_of"])

        # Signal journal — append only when the call changes (or first ever).
        last_log = db.execute(
            select(SignalLog).where(SignalLog.symbol == SYMBOL)
            .order_by(SignalLog.logged_at.desc()).limit(1)
        ).scalar_one_or_none()
        if last_log is None or last_log.signal != sig["signal"]:
            db.add(SignalLog(
                symbol=SYMBOL,
                as_of=prob["as_of"],
                signal=sig["signal"],
                score=round(sig["score"], 3) if sig.get("score") is not None else None,
                confidence=round(sig["confidence"], 3) if sig.get("confidence") is not None else None,
                prev_signal=last_log.signal if last_log else None,
                event_type="first" if last_log is None else "change",
            ))
            db.commit()
            print(f"[signal-log] {prob['as_of']} {sig['signal']} "
                  f"(was {last_log.signal if last_log else 'n/a'})")

        # Daily Brief (final output)
        forecast = {"seasonal": prob["expected_season_mm"], **_near_term_forecast(db, location_id)}
        rev_prob = rev["prediction"]["p_up"] if rev else None
        upsert(db, DailyBrief, [{
            "symbol": SYMBOL, "as_of": prob["as_of"],
            "rainfall_forecast": forecast,
            "confidence_score": sig["confidence"],
            "revision_probability": round(rev_prob, 4) if rev_prob is not None else None,
            "expected_season_mm": prob["expected_season_mm"],
            "fair_value": fair["fair_value"] if fair else None,
            "signal": sig["signal"],
            "bullish_factors": sig["bullish_factors"],
            "bearish_factors": sig["bearish_factors"],
        }], ["symbol", "as_of"])

        print(f"[signals] {prob['as_of']} signal={sig['signal']} score={sig['score']} "
              f"conf={sig['confidence']} E[season]={prob['expected_season_mm']}mm "
              f"P(above)={prob['p_above_norm']} fair={fair['fair_value'] if fair else None}")
        return {"prob": prob, "fair": fair, "signal": sig}
    finally:
        db.close()


if __name__ == "__main__":
    run()
