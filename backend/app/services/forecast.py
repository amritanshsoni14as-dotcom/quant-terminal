"""Commodity forecast engine — probabilistic bull/bear/neutral per horizon.

Pipeline: price-derived features → LightGBM forward-return regressor (per horizon,
time-split holdout for residual scale) → point return; blended with the fundamental
Health composite (Rogers/score prior) → Normal(mu, sigma) → P(bull/bear/neutral)
with volatility-scaled thresholds. Results cached in commodity_forecasts.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config_registry
from app.ingest.base import upsert
from app.models.orm import CommodityForecast
from app.services import intel, markets

HORIZONS = [5, 21, 63]
FEATURES = ["ret1", "ret5", "ret21", "rsi14", "vol21", "sma50_dist", "sma200_dist"]


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    diff = np.diff(closes, prepend=closes[0])
    gain = np.where(diff > 0, diff, 0.0)
    loss = np.where(diff < 0, -diff, 0.0)
    out = np.full(len(closes), 50.0)
    for i in range(period, len(closes)):
        ag = gain[i - period + 1:i + 1].mean()
        al = loss[i - period + 1:i + 1].mean()
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def _build(closes: np.ndarray):
    n = len(closes)
    ret1 = np.zeros(n); ret1[1:] = closes[1:] / closes[:-1] - 1
    ret5 = np.zeros(n); ret5[5:] = closes[5:] / closes[:-5] - 1
    ret21 = np.zeros(n); ret21[21:] = closes[21:] / closes[:-21] - 1
    rsi = _rsi(closes) / 100.0
    vol21 = np.zeros(n)
    for i in range(21, n):
        vol21[i] = ret1[i - 20:i + 1].std()
    sma50 = np.array([closes[max(0, i - 49):i + 1].mean() for i in range(n)])
    sma200 = np.array([closes[max(0, i - 199):i + 1].mean() for i in range(n)])
    X = np.column_stack([ret1, ret5, ret21, rsi, vol21, closes / sma50 - 1, closes / sma200 - 1])
    return X, vol21


def compute(db: Session, symbol: str) -> list[dict] | None:
    cfg = config_registry.get(symbol)
    if not cfg:
        return None
    a = markets._asset(db, cfg["symbol"])
    if not a:
        return None
    rows = markets._series(db, a.id)
    if len(rows) < 400:
        return None
    closes = np.array([r.close for r in rows], dtype=float)
    last_close = float(closes[-1])
    as_of = rows[-1].obs_date
    X, vol21 = _build(closes)
    daily_vol = float(vol21[-1]) or float(np.diff(closes[-60:]).std() / last_close)

    composite = (intel.scorecard(db, symbol) or {}).get("composite", 0.0) or 0.0

    from lightgbm import LGBMRegressor

    out_rows = []
    start = 200  # warmup for sma200
    for h in HORIZONS:
        n = len(closes)
        idx = np.arange(start, n - h)
        if len(idx) < 200:
            continue
        Xtr_all = X[idx]
        ytr_all = closes[idx + h] / closes[idx] - 1
        cut = int(len(idx) * 0.8)
        model = LGBMRegressor(n_estimators=200, max_depth=5, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8, n_jobs=-1,
                              random_state=42, verbose=-1)
        model.fit(Xtr_all[:cut], ytr_all[:cut])
        resid = ytr_all[cut:] - model.predict(Xtr_all[cut:])
        sigma_resid = float(np.std(resid)) if len(resid) > 5 else float(np.std(ytr_all))
        # refit on all, predict latest
        model.fit(Xtr_all, ytr_all)
        point_ml = float(model.predict(X[-1:])[0])

        vol_h = daily_vol * math.sqrt(h)
        # Blend ML with the fundamental composite (tilts the mean).
        mu = point_ml + 0.3 * composite * vol_h
        sigma = max(sigma_resid, vol_h, 1e-4)
        thr = 0.5 * vol_h

        p_bull = round(1 - _norm_cdf((thr - mu) / sigma), 3)
        p_bear = round(_norm_cdf((-thr - mu) / sigma), 3)
        p_neutral = round(max(0.0, 1 - p_bull - p_bear), 3)

        imp = model.feature_importances_
        top = sorted(zip(FEATURES, imp), key=lambda x: -x[1])[:3]

        out_rows.append({
            "symbol": cfg["symbol"], "as_of": as_of, "horizon": f"{h}d",
            "point_return_pct": round(mu * 100, 2),
            "p_bull": p_bull, "p_bear": p_bear, "p_neutral": p_neutral,
            "expected_price": round(last_close * (1 + mu), 2),
            "model": "lightgbm+composite",
            "drivers": {"top_features": [t[0] for t in top], "ml_return_pct": round(point_ml * 100, 2),
                        "fundamental_tilt": round(composite, 3)},
        })

    if out_rows:
        upsert(db, CommodityForecast, out_rows, ["symbol", "as_of", "horizon"])
    return out_rows


def read_latest(db: Session, symbol: str) -> dict:
    cfg = config_registry.get(symbol)
    sym = cfg["symbol"] if cfg else symbol.upper()
    latest = db.execute(
        select(CommodityForecast.as_of).where(CommodityForecast.symbol == sym)
        .order_by(CommodityForecast.as_of.desc()).limit(1)
    ).scalar_one_or_none()
    if latest is None:
        rows = compute(db, sym) or []
        return {"available": bool(rows), "symbol": sym,
                "as_of": rows[0]["as_of"].isoformat() if rows else None,
                "horizons": [{k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()} for r in rows]}
    recs = db.execute(
        select(CommodityForecast).where(CommodityForecast.symbol == sym, CommodityForecast.as_of == latest)
    ).scalars().all()
    order = {"5d": 0, "21d": 1, "63d": 2}
    recs = sorted(recs, key=lambda r: order.get(r.horizon, 9))
    return {
        "available": bool(recs), "symbol": sym, "as_of": latest.isoformat(),
        "horizons": [{
            "horizon": r.horizon, "point_return_pct": r.point_return_pct,
            "p_bull": r.p_bull, "p_bear": r.p_bear, "p_neutral": r.p_neutral,
            "expected_price": r.expected_price, "drivers": r.drivers,
        } for r in recs],
    }


def refresh_all(db: Session) -> dict:
    out = {}
    for sym in config_registry.list_symbols():
        try:
            r = compute(db, sym)
            out[sym] = len(r) if r else 0
        except Exception as exc:  # noqa: BLE001
            out[sym] = f"error: {exc}"
    return out
