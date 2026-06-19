"""Generate current forecasts from the champion model per horizon and write
them (versioned) to the forecasts table.

    python -m app.ml.predict
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, init_db
from app.ingest.base import upsert
from app.ml import datasets, dl, models
from app.ml.datasets import HORIZONS
from app.models.orm import Forecast, ModelRun

Z10 = 1.2816  # 10th/90th percentile of N(0,1)


def _champion(db: Session, horizon: str) -> str:
    r = db.execute(
        select(ModelRun).where(ModelRun.horizon == horizon, ModelRun.is_champion.is_(True))
        .order_by(ModelRun.trained_at.desc()).limit(1)
    ).scalar_one_or_none()
    return r.model_name if r else "xgboost"


def predict(db: Session) -> list[dict]:
    ds = datasets.build(db)
    # Release the implicit transaction from the dataset SELECT before the
    # per-horizon model fits (Neon idle-in-transaction safety).
    db.rollback()
    if ds is None:
        return []
    issued = ds.dates[-1]
    last_X = ds.X[-1:]  # features for the most recent day → forecast the future
    out_rows = []

    for h in HORIZONS:
        horizon = f"{h}d"
        champ = _champion(db, horizon)
        y_all = ds.targets[h]
        mask = ~np.isnan(y_all)
        X, y = ds.X[mask], y_all[mask]

        if champ in dl.DL_MODELS:
            pt = dl.predict_latest(champ, ds.X, y_all)
            point = float(pt) if pt is not None else float(np.median(y))
            sd = float(np.std(y)) * 0.5
        elif champ == "prophet":
            point = float(models.prophet_predict(list(ds.dates[mask]), ds.rain[mask], [issued], h)[0])
            # residual band from a simple in-sample proxy
            sd = float(np.std(y)) * 0.5
        else:
            model = models.build_tabular(champ)
            model.fit(X, y)
            point = float(np.clip(model.predict(last_X)[0], 0, None))
            resid = y - np.clip(model.predict(X), 0, None)
            sd = float(np.std(resid))

        p10 = max(0.0, point - Z10 * sd)
        p90 = point + Z10 * sd
        conf = round(1.0 / (1.0 + sd / max(point, 1.0)), 3)
        out_rows.append({
            "location_id": ds.location_id, "issued_date": issued, "horizon": horizon,
            "target_date": None, "model_name": champ,
            "point_mm": round(point, 1), "p10_mm": round(p10, 1), "p90_mm": round(p90, 1),
            "prob_above_norm": None, "confidence": conf,
        })
        print(f"[ml-predict] {horizon}: {champ} -> {point:.1f}mm [{p10:.0f},{p90:.0f}] conf={conf}")

    upsert(db, Forecast, out_rows,
           ["location_id", "issued_date", "horizon", "target_date", "model_name"])
    return out_rows


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        predict(db)
    finally:
        db.close()
