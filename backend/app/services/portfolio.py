"""Portfolio Mode — cross-commodity ranking.

Combines each commodity's Health scorecard + bull/bear forecast + price/risk into
one comparable row, plus an Opportunity score (fundamental health + forecast tilt
− risk). Powers Most-Bullish / Most-Bearish / Highest-Risk / Best-Opportunity views.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import config_registry
from app.services import forecast, intel, markets


def build(db: Session) -> dict:
    rows = []
    for sym in config_registry.list_symbols():
        sc = intel.scorecard(db, sym)
        if not sc.get("available"):
            continue
        summ = markets.summary(db, sym)
        fc = forecast.read_latest(db, sym)
        h21 = next((h for h in (fc.get("horizons") or []) if h["horizon"] == "21d"), None)

        health = sc.get("health") or 50
        risk = sc.get("risk_score") or 0
        p_bull = h21["p_bull"] if h21 else None
        p_bear = h21["p_bear"] if h21 else None
        ret21 = h21["point_return_pct"] if h21 else None

        # Opportunity: fundamentals + forecast tilt − risk, scaled to ~0-100.
        opp = (0.5 * ((health - 50) / 50)
               + 0.3 * ((p_bull or 0) - (p_bear or 0))
               - 0.2 * (risk / 100))
        opportunity = round(50 * (opp + 1))

        topcat = (sc.get("categories") or [None])[0]
        top_driver = None
        if topcat and topcat.get("contributors"):
            c = topcat["contributors"][0]
            top_driver = f"{c['label']} ({'+' if c['sub_score'] >= 0 else ''}{c['sub_score']})"

        rows.append({
            "symbol": sym, "name": sc.get("name"), "category": sc.get("category"),
            "price": summ.get("price") if summ.get("available") else None,
            "unit": sc.get("unit"),
            "health": health, "verdict": sc.get("verdict"), "composite": sc.get("composite"),
            "trend_score": sc.get("trend_score"), "risk_score": risk,
            "change_1m": (summ.get("change") or {}).get("1m") if summ.get("available") else None,
            "change_1y": (summ.get("change") or {}).get("1y") if summ.get("available") else None,
            "p_bull_21d": p_bull, "p_bear_21d": p_bear, "forecast_21d_pct": ret21,
            "opportunity": opportunity,
            "top_driver": top_driver,
            "substitutes": sc.get("substitutes", []),
        })

    bullish = [r for r in rows if (r["composite"] or 0) > 0.12]
    bearish = [r for r in rows if (r["composite"] or 0) < -0.12]
    avg_health = round(sum(r["health"] for r in rows) / len(rows)) if rows else None

    return {
        "available": bool(rows),
        "summary": {"count": len(rows), "bullish": len(bullish), "bearish": len(bearish),
                    "avg_health": avg_health},
        "commodities": sorted(rows, key=lambda r: -r["health"]),
    }
