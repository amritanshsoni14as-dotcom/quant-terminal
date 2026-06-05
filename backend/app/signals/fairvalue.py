"""Module 2 — Contract fair value (model-derived, market-price-agnostic).

Maps the seasonal rainfall posterior (from the Probability Engine) through the
contract's payoff function to an expected settlement and discounted fair value.
The payoff is a pluggable config on `contract_specs.payoff_params`, so the real
NCDEX RAINMUMBAI spec — or any contract — drops in without code changes.

Market price + mispricing are filled in automatically once contract prices are
ingested (see app/ingest/ncdex.py); until then they are null by design.
"""
from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import ContractPrice, ContractSpec

_N_SAMPLES = 40000


def payoff(index: float, payoff_type: str, params: dict) -> float:
    """Settlement value of the contract for a realised rainfall `index` (mm)."""
    if payoff_type == "binary":
        strike = params.get("strike", 0.0)
        payout = params.get("payout", 1.0)
        return payout if index >= strike else 0.0
    # index_linear / capped
    tick = params.get("tick", 1.0)
    strike = params.get("strike", 0.0)
    val = tick * (index - strike)
    floor = params.get("floor")
    cap = params.get("cap")
    if floor is not None:
        val = max(val, floor)
    if cap is not None:
        val = min(val, cap)
    return val


def compute(db: Session, symbol: str, mu: float, sd: float) -> dict | None:
    spec = db.execute(
        select(ContractSpec).where(ContractSpec.symbol == symbol)
    ).scalar_one_or_none()
    if spec is None:
        return None

    ptype = spec.payoff_type or "index_linear"
    params = spec.payoff_params or {}

    # Monte-Carlo expectation under the rainfall posterior (seeded → reproducible).
    rng = random.Random(42)
    sd_eff = max(sd, 1e-6)
    payoffs = [payoff(rng.gauss(mu, sd_eff), ptype, params) for _ in range(_N_SAMPLES)]
    fair_value = sum(payoffs) / len(payoffs)
    expected_settle = mu  # index is the rainfall total itself

    # Optional market price (latest available) → mispricing.
    last_price = db.execute(
        select(ContractPrice)
        .where(ContractPrice.symbol == symbol)
        .order_by(ContractPrice.trade_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    market_price = None
    if last_price is not None:
        market_price = last_price.settle_price if last_price.settle_price is not None else last_price.close_price
    mispricing = (fair_value - market_price) if market_price is not None else None

    return {
        "symbol": symbol,
        "fair_value": round(fair_value, 2),
        "expected_settle": round(expected_settle, 2),
        "market_price": round(market_price, 2) if market_price is not None else None,
        "mispricing": round(mispricing, 2) if mispricing is not None else None,
        "inputs": {
            "mu": round(mu, 2), "sd": round(sd, 2),
            "payoff_type": ptype, "payoff_params": params,
            "n_samples": _N_SAMPLES,
        },
    }
