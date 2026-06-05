"""Module 10 — Scenario Analysis.

Projects seasonal rainfall under climate scenarios by conditioning on the
historical analog years that match each regime (empirical conditioning on the
25-year record). Some scenarios use documented proxies (noted) where a direct
observation isn't in the feature store yet.
"""
from __future__ import annotations

import statistics

from sqlalchemy.orm import Session

from app.signals import seasonstats
from app.signals.seasonstats import SeasonRow


def _pct(sorted_vals, q):
    if not sorted_vals:
        return None
    idx = q * (len(sorted_vals) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def _result(code, label, rows, matches, normal, note=""):
    vals = sorted(r.season_mm for r in matches)
    if not vals:
        return {"code": code, "label": label, "n_years": 0, "note": note,
                "projected_season_mm": None, "deviation_pct": None, "probability": 0.0}
    mean = statistics.fmean(vals)
    return {
        "code": code, "label": label, "n_years": len(vals),
        "projected_season_mm": round(mean, 0),
        "deviation_pct": round((mean - normal) / normal * 100, 1) if normal else None,
        "probability": round(len(vals) / len(rows), 3),
        "distribution": {
            "min": round(vals[0], 0), "p25": round(_pct(vals, 0.25), 0),
            "median": round(_pct(vals, 0.5), 0), "p75": round(_pct(vals, 0.75), 0),
            "max": round(vals[-1], 0),
        },
        "years": [r.year for r in matches],
        "note": note,
    }


def compute(db: Session) -> dict:
    rows, normal, _ = seasonstats.build(db)
    if not rows:
        return {"available": False}

    junes = sorted(r.june_mm for r in rows)
    lo_t, hi_t = _pct(junes, 1 / 3), _pct(junes, 2 / 3)

    def f(pred):
        return [r for r in rows if pred(r)]

    scen = [
        _result("STRONG_ELNINO", "Strong El Niño",
                rows, f(lambda r: r.jja_oni is not None and r.jja_oni >= 1.0), normal,
                "JJA ONI ≥ +1.0 °C"),
        _result("STRONG_LANINA", "Strong La Niña",
                rows, f(lambda r: r.jja_oni is not None and r.jja_oni <= -1.0), normal,
                "JJA ONI ≤ −1.0 °C"),
        _result("POS_IOD", "Positive IOD",
                rows, f(lambda r: r.season_dmi is not None and r.season_dmi >= 0.4), normal,
                "Jun–Oct DMI ≥ +0.4"),
        _result("NEG_IOD", "Negative IOD",
                rows, f(lambda r: r.season_dmi is not None and r.season_dmi <= -0.4), normal,
                "Jun–Oct DMI ≤ −0.4"),
        _result("ARABIAN_WARM", "Extreme Arabian-Sea Warming",
                rows, f(lambda r: r.season_dmi is not None and r.season_dmi >= 0.6), normal,
                "Proxy: strong +IOD (warm western Indian Ocean). Direct Arabian-Sea SST in a later phase."),
        _result("DELAYED_MONSOON", "Delayed Monsoon Onset",
                rows, f(lambda r: r.june_mm <= lo_t), normal,
                "Proxy: June rainfall in lowest tercile"),
        _result("EARLY_MONSOON", "Early / Vigorous Onset",
                rows, f(lambda r: r.june_mm >= hi_t), normal,
                "Proxy: June rainfall in highest tercile"),
    ]
    return {"available": True, "normal_season_mm": round(normal, 0),
            "n_total_years": len(rows), "scenarios": scen}
