"""Generic scoring engine — identical for every commodity.

Input: a list of resolved indicators (each with category, weight, direction and a
normalized value in ~[-1,1], or None if its data isn't available) + category
weights from config.
Output: category scores, composite bullish [-1,1], Health 0-100, with full
per-indicator contribution for explainability. Categories with no available data
are skipped and the composite renormalizes — graceful degradation.
"""
from __future__ import annotations


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def compute(resolved: list[dict], category_weights: dict[str, float]) -> dict:
    # Group indicators by category.
    by_cat: dict[str, list[dict]] = {}
    for ind in resolved:
        if ind.get("normalized") is None:
            continue
        ind = dict(ind)
        ind["sub_score"] = round(_clip(ind.get("direction", 1) * ind["normalized"]), 3)
        by_cat.setdefault(ind["category"], []).append(ind)

    categories = []
    for cat, inds in by_cat.items():
        tw = sum(i.get("weight", 1.0) for i in inds) or 1.0
        score = sum(i.get("weight", 1.0) * i["sub_score"] for i in inds) / tw
        categories.append({
            "category": cat,
            "score": round(score, 3),
            "contributors": [
                {"key": i["key"], "label": i.get("label", i["key"]),
                 "sub_score": i["sub_score"], "weight": i.get("weight", 1.0),
                 "normalized": round(i["normalized"], 3)}
                for i in sorted(inds, key=lambda x: -abs(x["sub_score"]))
            ],
        })

    present = {c["category"]: c["score"] for c in categories}
    tw = sum(category_weights.get(c, 0) for c in present) or 1.0
    composite = sum(category_weights.get(c, 0) * s for c, s in present.items()) / tw
    composite = round(_clip(composite), 3)
    health = round(50 * (composite + 1))

    verdict = (
        "Strongly Bullish" if composite >= 0.4 else
        "Bullish" if composite >= 0.12 else
        "Neutral" if composite > -0.12 else
        "Bearish" if composite > -0.4 else
        "Strongly Bearish"
    )
    return {
        "composite": composite,
        "health": health,
        "verdict": verdict,
        "categories": sorted(categories, key=lambda c: -abs(c["score"])),
        "covered_categories": list(present.keys()),
    }
