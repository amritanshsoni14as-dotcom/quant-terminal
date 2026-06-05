"""Commodity markets analytics — Command Center stats + core technicals.

Pure read over asset_prices. One service, parameterised by symbol, so the
frontend dropdown switches commodity and everything recomputes.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import Asset, AssetPrice


def list_assets(db: Session) -> list[dict]:
    out = []
    for a in db.execute(
        select(Asset).where(Asset.active.is_(True), Asset.asset_class != "macro")
        .order_by(Asset.sort_order)
    ).scalars():
        n = db.execute(select(AssetPrice).where(AssetPrice.asset_id == a.id).limit(1)).first()
        out.append({"symbol": a.symbol, "name": a.name, "asset_class": a.asset_class,
                    "currency": a.currency, "unit": a.unit, "exchange": a.exchange,
                    "has_data": n is not None})
    return out


def _asset(db: Session, symbol: str) -> Asset | None:
    return db.execute(select(Asset).where(Asset.symbol == symbol.upper())).scalar_one_or_none()


def _series(db: Session, asset_id: int):
    rows = db.execute(
        select(AssetPrice).where(AssetPrice.asset_id == asset_id).order_by(AssetPrice.obs_date)
    ).scalars().all()
    return rows


def _rsi(closes: np.ndarray, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    diff = np.diff(closes)
    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)
    ag = gains[-period:].mean()
    al = losses[-period:].mean()
    if al == 0:
        return 100.0
    rs = ag / al
    return float(100 - 100 / (1 + rs))


def _ema(arr: np.ndarray, span: int) -> np.ndarray:
    alpha = 2 / (span + 1)
    out = np.empty_like(arr, dtype=float)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def _pct(cur: float, past: float | None) -> float | None:
    if past is None or past == 0:
        return None
    return round((cur / past - 1) * 100, 2)


def summary(db: Session, symbol: str) -> dict:
    a = _asset(db, symbol)
    if not a:
        return {"available": False}
    rows = _series(db, a.id)
    if not rows:
        return {"available": False, "symbol": a.symbol, "name": a.name, "reason": "no price data"}

    dates = [r.obs_date for r in rows]
    close = np.array([r.close for r in rows], dtype=float)
    high = np.array([(r.high if r.high is not None else r.close) for r in rows], dtype=float)
    low = np.array([(r.low if r.low is not None else r.close) for r in rows], dtype=float)
    cur = float(close[-1])

    def ago(n):
        return float(close[-1 - n]) if len(close) > n else None

    # YTD: first close of current year.
    yr = dates[-1].year
    ytd_base = next((float(close[i]) for i, d in enumerate(dates) if d.year == yr), None)

    last252 = close[-252:] if len(close) >= 1 else close
    logret = np.diff(np.log(close[-31:])) if len(close) > 31 else np.diff(np.log(close))
    vol = float(np.std(logret) * np.sqrt(252) * 100) if len(logret) > 1 else None

    # ATR14
    atr = None
    if len(rows) > 15:
        prev_close = close[-15:-1]
        tr = np.maximum.reduce([high[-14:] - low[-14:],
                                np.abs(high[-14:] - prev_close),
                                np.abs(low[-14:] - prev_close)])
        atr = float(tr.mean())

    sma50 = float(close[-50:].mean()) if len(close) >= 50 else None
    sma200 = float(close[-200:].mean()) if len(close) >= 200 else None
    rsi = _rsi(close)

    # Simple technical trend label.
    trend = "Neutral"
    if sma50 and sma200:
        if cur > sma50 > sma200:
            trend = "Uptrend"
        elif cur < sma50 < sma200:
            trend = "Downtrend"

    return {
        "available": True,
        "symbol": a.symbol, "name": a.name, "asset_class": a.asset_class,
        "currency": a.currency, "unit": a.unit, "exchange": a.exchange,
        "as_of": dates[-1].isoformat(),
        "price": round(cur, 2),
        "change": {
            "1d": _pct(cur, ago(1)), "1w": _pct(cur, ago(5)), "1m": _pct(cur, ago(21)),
            "3m": _pct(cur, ago(63)), "ytd": _pct(cur, ytd_base), "1y": _pct(cur, ago(252)),
        },
        "high_52w": round(float(last252.max()), 2),
        "low_52w": round(float(last252.min()), 2),
        "volatility_annual_pct": round(vol, 1) if vol is not None else None,
        "atr_14": round(atr, 2) if atr is not None else None,
        "rsi_14": round(rsi, 1) if rsi is not None else None,
        "sma_50": round(sma50, 2) if sma50 else None,
        "sma_200": round(sma200, 2) if sma200 else None,
        "trend": trend,
        "n_days": len(rows),
    }


def prices(db: Session, symbol: str, days: int = 260) -> dict:
    a = _asset(db, symbol)
    if not a:
        return {"series": []}
    rows = _series(db, a.id)[-days:]
    close = np.array([r.close for r in rows], dtype=float)

    def sma(arr, w):
        out = [None] * len(arr)
        for i in range(w - 1, len(arr)):
            out[i] = round(float(arr[i - w + 1:i + 1].mean()), 2)
        return out

    s50 = sma(close, 50) if len(close) >= 50 else [None] * len(close)
    s200 = sma(close, 200) if len(close) >= 200 else [None] * len(close)
    return {
        "symbol": a.symbol,
        "series": [
            {"date": r.obs_date.isoformat(), "open": r.open, "high": r.high, "low": r.low,
             "close": r.close, "sma50": s50[i], "sma200": s200[i]}
            for i, r in enumerate(rows)
        ],
    }


def technicals(db: Session, symbol: str) -> dict:
    a = _asset(db, symbol)
    if not a:
        return {"available": False}
    rows = _series(db, a.id)
    if len(rows) < 60:
        return {"available": False}
    close = np.array([r.close for r in rows], dtype=float)
    dates = [r.obs_date for r in rows]

    ema12, ema26 = _ema(close, 12), _ema(close, 26)
    macd = ema12 - ema26
    signal_line = _ema(macd, 9)
    hist = macd - signal_line

    sma20 = close[-20:].mean()
    std20 = close[-20:].std()
    boll_up = sma20 + 2 * std20
    boll_dn = sma20 - 2 * std20

    n = min(180, len(rows))
    series = [{"date": dates[-n + i].isoformat(),
               "macd": round(float(macd[-n + i]), 3),
               "signal": round(float(signal_line[-n + i]), 3),
               "hist": round(float(hist[-n + i]), 3)} for i in range(n)]

    return {
        "available": True, "symbol": a.symbol,
        "rsi_14": _rsi(close),
        "macd": {"macd": round(float(macd[-1]), 3), "signal": round(float(signal_line[-1]), 3),
                 "hist": round(float(hist[-1]), 3)},
        "bollinger": {"upper": round(float(boll_up), 2), "mid": round(float(sma20), 2),
                      "lower": round(float(boll_dn), 2), "price": round(float(close[-1]), 2)},
        "macd_series": series,
    }
