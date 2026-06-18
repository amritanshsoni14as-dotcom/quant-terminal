"""Commodity price ingester — Yahoo Finance daily OHLCV (free, no key).

Covers gold, silver, crude (WTI), natural gas, copper via the v8 chart API.
Electricity has no clean free feed → seeded but left for CSV/API plug-in (the
same seam pattern as the NCDEX contract importer).
"""
from __future__ import annotations

from datetime import date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.base import upsert
from app.models.orm import Asset, AssetPrice

YF_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# symbol, name, yahoo_ticker, class, currency, unit, exchange
SEED = [
    ("GOLD", "Gold", "GC=F", "metal", "USD", "per troy oz", "COMEX"),
    ("SILVER", "Silver", "SI=F", "metal", "USD", "per troy oz", "COMEX"),
    ("COPPER", "Copper", "HG=F", "metal", "USD", "per lb", "COMEX"),
    ("CRUDE", "Crude Oil (WTI)", "CL=F", "energy", "USD", "per barrel", "NYMEX"),
    ("NATGAS", "Natural Gas", "NG=F", "energy", "USD", "per MMBtu", "NYMEX"),
    ("WHEAT", "Wheat (CBOT SRW)", "ZW=F", "agriculture", "USD", "cents/bu", "CBOT"),
    ("SOYBEAN", "Soybeans (CBOT)", "ZS=F", "agriculture", "USD", "cents/bu", "CBOT"),
    ("ELECTRICITY", "Electricity", None, "energy", "INR", "per MWh", "IEX/MCX"),
]

# Macro series (drive the cross-asset / macro scoring). asset_class='macro' →
# hidden from the commodity dropdown but available to the scoring engine.
MACRO_SEED = [
    ("DXY", "US Dollar Index", "DX-Y.NYB", "macro", "Index", "DXY", "ICE"),
    ("US10Y", "US 10Y Treasury Yield", "^TNX", "macro", "%", "yield", "CBOE"),
    ("SP500", "S&P 500", "^GSPC", "macro", "Index", "index", "—"),
]


def seed_assets(db: Session) -> None:
    existing = {a.symbol for a in db.execute(select(Asset)).scalars()}
    for i, (sym, name, tkr, cls, ccy, unit, exch) in enumerate(SEED + MACRO_SEED):
        if sym in existing:
            continue
        db.add(Asset(symbol=sym, name=name, yahoo_ticker=tkr, asset_class=cls,
                     currency=ccy, unit=unit, exchange=exch, active=True, sort_order=i))
    db.commit()


def fetch_history(db: Session, asset: Asset, rng: str = "10y") -> int:
    if not asset.yahoo_ticker:
        return 0
    with httpx.Client(timeout=40, headers={"User-Agent": _UA}, follow_redirects=True) as client:
        resp = client.get(YF_URL.format(ticker=asset.yahoo_ticker),
                          params={"range": rng, "interval": "1d"})
        resp.raise_for_status()
        data = resp.json()

    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return 0
    ts = result.get("timestamp", []) or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])
    adjclose = adj[0].get("adjclose", []) if adj else []

    rows = []
    for i, t in enumerate(ts):
        c = _at(quote.get("close"), i)
        if c is None:
            continue
        rows.append({
            "asset_id": asset.id,
            "obs_date": datetime.utcfromtimestamp(t).date(),
            "open": _at(quote.get("open"), i),
            "high": _at(quote.get("high"), i),
            "low": _at(quote.get("low"), i),
            "close": c,
            "adj_close": _at(adjclose, i),
            "volume": _at(quote.get("volume"), i),
            "source": "yahoo",
        })
    return upsert(db, AssetPrice, rows, ["asset_id", "obs_date"])


def backfill_all(db: Session, rng: str = "10y") -> dict:
    seed_assets(db)
    out = {}
    for a in db.execute(select(Asset).where(Asset.active.is_(True)).order_by(Asset.sort_order)).scalars():
        try:
            n = fetch_history(db, a, rng)
            out[a.symbol] = n
        except Exception as exc:  # noqa: BLE001
            out[a.symbol] = f"error: {exc}"
        print(f"[commodities] {a.symbol}: {out[a.symbol]}")
    return out


def _at(arr, i):
    if not arr or i >= len(arr):
        return None
    return arr[i]


if __name__ == "__main__":
    from app.core.db import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        backfill_all(db)
    finally:
        db.close()
