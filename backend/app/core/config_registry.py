"""Commodity config registry — loads & validates JSON configs (the no-hardcode layer).

Each backend/app/commodity_configs/<symbol>.json defines a commodity's indicators,
weights and metadata. The engine reads these; adding a commodity = adding a file.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[1] / "commodity_configs"

_REQUIRED_TOP = {"symbol", "name", "category", "indicators", "category_weights"}
_VALID_CATEGORIES = {
    "price", "technical", "valuation", "supply", "demand", "inventory",
    "weather", "macro", "positioning", "supply_capacity", "regime",
}


def _validate(cfg: dict, fname: str) -> list[str]:
    errs = []
    missing = _REQUIRED_TOP - cfg.keys()
    if missing:
        errs.append(f"{fname}: missing {missing}")
    for ind in cfg.get("indicators", []):
        if "key" not in ind or "category" not in ind or "source" not in ind:
            errs.append(f"{fname}: indicator missing key/category/source: {ind.get('key')}")
        if ind.get("category") not in _VALID_CATEGORIES:
            errs.append(f"{fname}: bad category '{ind.get('category')}' on {ind.get('key')}")
    return errs


@lru_cache(maxsize=1)
def load_all() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not CONFIG_DIR.exists():
        return out
    for f in sorted(CONFIG_DIR.glob("*.json")):
        try:
            cfg = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[config] {f.name} parse error: {exc}")
            continue
        errs = _validate(cfg, f.name)
        if errs:
            print("[config] " + "; ".join(errs))
            continue
        out[cfg["symbol"].upper()] = cfg
    return out


def reload() -> dict[str, dict]:
    load_all.cache_clear()
    return load_all()


def get(symbol: str) -> dict | None:
    return load_all().get(symbol.upper())


def list_symbols() -> list[str]:
    return list(load_all().keys())
