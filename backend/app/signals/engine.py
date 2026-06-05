"""Module 9 — Trading Signal Engine (v1, rule-based & explainable).

Blends the probability tilt, the established monsoon drivers (ENSO, IOD, MJO),
season-to-date momentum, and model-vs-market mispricing into one composite
score in [-1, +1], mapped to Strong Sell … Strong Buy. Every component keeps its
own contribution so the signal is fully explainable (and feeds the bull/bear
factor lists). The mispricing component is wired in but contributes 0 until
contract prices are ingested.

"Bullish" = the model expects above-normal seasonal rainfall (higher rainfall
index → higher RAINMUMBAI settlement under a long-rainfall payoff).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import RawClimateDriver


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _latest_driver(db: Session, name: str) -> float | None:
    r = db.execute(
        select(RawClimateDriver)
        .where(RawClimateDriver.driver == name, RawClimateDriver.value.isnot(None))
        .order_by(RawClimateDriver.obs_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    return r.value if r else None


# MJO phases roughly favourable / unfavourable for the Indian summer monsoon.
_MJO_FAVOURABLE = {1, 2, 3, 4}


def compute(db: Session, prob: dict, fair: dict | None, monsoon_progress: float | None,
            revision: dict | None = None) -> dict:
    oni = _latest_driver(db, "ONI")
    iod = _latest_driver(db, "IOD_DMI")
    mjo_phase = _latest_driver(db, "MJO_PHASE")
    mjo_amp = _latest_driver(db, "MJO_AMP")

    comps: list[dict] = []

    # 1) Probability tilt (model's own seasonal view).
    tilt = _clamp((prob["p_above_norm"] - 0.5) * 2.0)
    comps.append({
        "key": "probability", "weight": 0.25, "score": round(tilt, 3),
        "label": "Seasonal probability",
        "detail": f"{prob['p_above_norm']*100:.0f}% chance of above-normal rainfall "
                  f"(E[season]={prob['expected_season_mm']:.0f}mm vs {prob['normal_mm']:.0f}mm normal)",
    })

    # 1b) Forecast revision (PRIMARY alpha — Module 7). Only when in-season.
    if revision is not None and revision.get("prediction", {}).get("in_season"):
        p_up = revision["prediction"]["p_up"]
        rev_s = _clamp((p_up - 0.5) * 2.0)
        comps.append({
            "key": "revision", "weight": 0.25, "score": round(rev_s, 3),
            "label": "Forecast revision",
            "detail": f"{p_up*100:.0f}% chance the seasonal forecast is revised UP "
                      f"(E[revision]={revision['prediction']['exp_size']:+.0f}mm)",
        })

    # 2) ENSO: La Niña wet (+), El Niño dry (-) for the Indian monsoon.
    if oni is not None:
        enso = _clamp(-oni / 1.5)
        regime = "La Niña" if oni <= -0.5 else "El Niño" if oni >= 0.5 else "ENSO-neutral"
        comps.append({
            "key": "enso", "weight": 0.20, "score": round(enso, 3),
            "label": "ENSO / ONI",
            "detail": f"{regime} (ONI {oni:+.2f}) — {'supports' if enso>0 else 'suppresses' if enso<0 else 'neutral for'} monsoon rainfall",
        })

    # 3) IOD: positive dipole enhances monsoon.
    if iod is not None:
        iod_s = _clamp(iod / 1.0)
        sign = "Positive" if iod > 0.4 else "Negative" if iod < -0.4 else "Neutral"
        comps.append({
            "key": "iod", "weight": 0.15, "score": round(iod_s, 3),
            "label": "Indian Ocean Dipole",
            "detail": f"{sign} IOD (DMI {iod:+.2f}) — {'enhances' if iod_s>0 else 'dampens' if iod_s<0 else 'neutral for'} rainfall",
        })

    # 4) MJO: favourable phase + amplitude.
    if mjo_phase is not None and mjo_amp is not None:
        direction = 1.0 if int(mjo_phase) in _MJO_FAVOURABLE else -1.0
        mjo_s = _clamp(direction * min(mjo_amp, 2.0) / 2.0 * 0.7)
        comps.append({
            "key": "mjo", "weight": 0.10, "score": round(mjo_s, 3),
            "label": "Madden–Julian Oscillation",
            "detail": f"Phase {int(mjo_phase)} (amp {mjo_amp:.1f}) — "
                      f"{'convectively favourable' if direction>0 else 'unfavourable'} for the region",
        })

    # 5) Season-to-date momentum (weighted by how far into the season we are).
    if monsoon_progress and monsoon_progress > 0.02:
        # posterior-vs-normal trajectory as a momentum proxy, scaled by season progress
        mom = _clamp((prob["expected_season_mm"] - prob["normal_mm"]) / max(prob["normal_mm"], 1) / 0.3) * monsoon_progress
        comps.append({
            "key": "momentum", "weight": 0.10, "score": round(mom, 3),
            "label": "Season momentum",
            "detail": f"{monsoon_progress*100:.0f}% through season; "
                      f"trajectory {'above' if mom>0 else 'below' if mom<0 else 'at'} normal",
        })

    # 6) Mispricing (0 until market prices exist).
    mispricing = fair.get("mispricing") if fair else None
    if mispricing is not None and fair and fair.get("market_price"):
        mp = _clamp(mispricing / max(abs(fair["market_price"]), 1.0))
        comps.append({
            "key": "mispricing", "weight": 0.20, "score": round(mp, 3),
            "label": "Model vs market",
            "detail": f"Fair {fair['fair_value']:.0f} vs market {fair['market_price']:.0f} "
                      f"→ {'under' if mp>0 else 'over'}priced",
        })

    # Weighted composite (renormalise over present components).
    tw = sum(c["weight"] for c in comps) or 1.0
    score = sum(c["weight"] * c["score"] for c in comps) / tw
    for c in comps:
        c["contribution"] = round(c["weight"] / tw * c["score"], 4)

    signal = (
        "STRONG_BUY" if score >= 0.5 else
        "BUY" if score >= 0.15 else
        "NEUTRAL" if score > -0.15 else
        "SELL" if score > -0.5 else
        "STRONG_SELL"
    )

    # Confidence: agreement among weighted components + signal strength.
    same = sum(c["weight"] for c in comps if (c["score"] > 0) == (score > 0) and c["score"] != 0)
    agreement = same / tw
    confidence = _clamp(0.25 + 0.45 * agreement + 0.30 * min(abs(score), 1.0), 0.0, 1.0)

    bullish = sorted([c for c in comps if c["contribution"] > 0], key=lambda c: -c["contribution"])[:5]
    bearish = sorted([c for c in comps if c["contribution"] < 0], key=lambda c: c["contribution"])[:5]

    return {
        "signal": signal,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
        "components": comps,
        "bullish_factors": [{"label": c["label"], "detail": c["detail"], "contribution": c["contribution"]} for c in bullish],
        "bearish_factors": [{"label": c["label"], "detail": c["detail"], "contribution": c["contribution"]} for c in bearish],
    }
