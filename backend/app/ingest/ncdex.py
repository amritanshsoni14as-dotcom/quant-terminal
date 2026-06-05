"""NCDEX RAINMUMBAI contract price importer (the plug-in seam for Module 2).

There is no clean public history API, so prices come via CSV (or the POST
endpoint in api/derivative.py). The moment any prices exist, the fair-value
engine starts reporting market price + mispricing — no other code changes.

CSV columns (header, case-insensitive; extras ignored):
    trade_date, open, high, low, close, settle, open_interest, volume
`trade_date` accepts YYYY-MM-DD or DD-MM-YYYY.

Usage:
    python -m app.ingest.ncdex path\to\rainmumbai.csv [SYMBOL]
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime

from sqlalchemy.orm import Session

from app.ingest.base import upsert
from app.models.orm import ContractPrice


def _parse_date(s: str):
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {s}")


def _num(v):
    v = (v or "").strip().replace(",", "")
    return float(v) if v else None


def import_csv(db: Session, path: str, symbol: str = "RAINMUMBAI") -> int:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        norm = {k: (k or "").strip().lower() for k in (reader.fieldnames or [])}
        for raw in reader:
            r = { norm[k]: v for k, v in raw.items() if k in norm }
            if not r.get("trade_date"):
                continue
            rows.append({
                "symbol": symbol,
                "trade_date": _parse_date(r["trade_date"]),
                "open_price": _num(r.get("open")),
                "high_price": _num(r.get("high")),
                "low_price": _num(r.get("low")),
                "close_price": _num(r.get("close")),
                "settle_price": _num(r.get("settle")),
                "open_interest": _num(r.get("open_interest")),
                "volume": _num(r.get("volume")),
                "source": "csv",
            })
    return upsert(db, ContractPrice, rows, ["symbol", "trade_date"])


if __name__ == "__main__":
    from app.core.db import SessionLocal, init_db

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    init_db()
    db = SessionLocal()
    try:
        n = import_csv(db, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "RAINMUMBAI")
        print(f"imported {n} price rows")
    finally:
        db.close()
