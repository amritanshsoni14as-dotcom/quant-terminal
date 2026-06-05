"""Commodity AI Copilot — answers "why is X moving / what next / what's the risk"
grounded on the live scorecard + forecast, with Jim Rogers' supply-cycle lens.
Runs on the local Ollama model (or Claude if a key is set)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import config_registry
from app.services import forecast, intel, llm, markets

SYSTEM = (
    "You are a senior commodities research analyst (trader + economist + supply-chain analyst). "
    "Answer the user's question USING ONLY the DATA SNAPSHOT provided. Reason like Jim Rogers in "
    "'Hot Commodities': commodities move in supply-led cycles — weigh inventories, productive capacity, "
    "valuation vs history, positioning extremes, and the macro/currency backdrop, not just price momentum. "
    "Be concise (3-5 sentences), cite the actual numbers, and explain the 'why'. If a category is missing "
    "from the snapshot, say the data isn't wired yet rather than guessing. Bullish = price likely up."
)


def suggested(symbol: str) -> list[str]:
    cfg = config_registry.get(symbol)
    name = cfg["name"] if cfg else symbol
    return [
        f"Why is {name} scored the way it is right now?",
        f"What is the biggest risk for {name}?",
        f"What does the forecast say for the next month?",
        f"Is {name} cheap or expensive versus history?",
        f"What would flip the outlook for {name}?",
    ]


def _context(db: Session, symbol: str) -> dict | None:
    sc = intel.scorecard(db, symbol)
    if not sc.get("available"):
        return None
    fc = forecast.read_latest(db, symbol)
    summ = markets.summary(db, symbol)
    cats = "; ".join(
        f"{c['category']} {c['score']:+.2f} ("
        + ", ".join(f"{k['label']} {k['sub_score']:+.2f}" for k in c["contributors"][:2]) + ")"
        for c in sc.get("categories", [])
    )
    fcs = "; ".join(
        f"{h['horizon']}: {h['point_return_pct']:+.1f}% (bull {int(h['p_bull']*100)}% / bear {int(h['p_bear']*100)}%)"
        for h in (fc.get("horizons") or [])
    )
    chg = summ.get("change", {}) if summ.get("available") else {}
    return {
        "name": sc["name"], "as_of": sc.get("as_of"),
        "price": sc.get("price"), "unit": sc.get("unit"),
        "perf": f"1M {chg.get('1m')}%, 1Y {chg.get('1y')}%",
        "health": sc.get("health"), "verdict": sc.get("verdict"),
        "trend_score": sc.get("trend_score"), "risk_score": sc.get("risk_score"),
        "category_scores": cats,
        "forecast": fcs,
        "covered": sc.get("covered_categories"),
        "pending": sc.get("pending_phase2"),
        "substitutes": sc.get("substitutes"),
        "secular_lead_months": (sc.get("secular") or {}).get("supply_lead_time_months"),
    }


def answer(db: Session, symbol: str, question: str) -> dict:
    ctx = _context(db, symbol)
    if not ctx:
        return {"available": False, "answer": "No data for this commodity yet."}
    lines = "\n".join(f"{k}: {v}" for k, v in ctx.items())
    prompt = (
        f"DATA SNAPSHOT for {ctx['name']} (as of {ctx['as_of']}):\n{lines}\n\n"
        f"QUESTION: {question}\n\nAnswer in 3-5 sentences using only the snapshot; cite the numbers."
    )
    try:
        text = llm.generate(prompt, system=SYSTEM, temperature=0.2, max_tokens=320)
    except Exception:  # noqa: BLE001
        return {"available": False, "answer": (
            "The AI model is offline. This Copilot runs on a local Ollama model (or Claude if "
            "ANTHROPIC_API_KEY is set). Start Ollama and pull the model (`ollama pull llama3.2:3b`), "
            "or add an Anthropic API key in backend/.env — then ask again.")}
    return {"available": True, "answer": text, "engine": llm.status().get("model"), "as_of": ctx["as_of"]}
