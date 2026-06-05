"""Train + evaluate all models across all horizons with time-series CV,
write the leaderboard (model_runs), and promote a champion per horizon.

    python -m app.ml.train
"""
from __future__ import annotations

from datetime import date

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, init_db
from app.ingest.base import upsert
from app.ml import datasets, dl, models
from app.ml.datasets import HORIZONS, Dataset
from app.models.orm import ModelRun

VERSION = "v1"
N_SPLITS = 4


def _metrics(actual: np.ndarray, pred: np.ndarray, ref: float) -> dict:
    pred = np.clip(pred, 0, None)
    rmse = float(np.sqrt(mean_squared_error(actual, pred)))
    mae = float(mean_absolute_error(actual, pred))
    thr = 1.0
    hit = float(np.mean((pred > thr) == (actual > thr)))
    da = float(np.mean(np.sign(pred - ref) == np.sign(actual - ref)))
    return {"rmse": rmse, "mae": mae, "hit_rate": hit, "directional_acc": da}


def _eval_tabular(name: str, X: np.ndarray, y: np.ndarray, ref: float) -> dict:
    preds, actuals = [], []
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    for tr, te in tscv.split(X):
        model = models.build_tabular(name)
        model.fit(X[tr], y[tr])
        preds.append(model.predict(X[te]))
        actuals.append(y[te])
    return _metrics(np.concatenate(actuals), np.concatenate(preds), ref)


def _eval_prophet(ds: Dataset, valid_idx: np.ndarray, h: int, y: np.ndarray, ref: float) -> dict:
    preds, actuals = [], []
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    idx = valid_idx
    for tr, te in tscv.split(idx):
        tr_idx, te_idx = idx[tr], idx[te]
        train_dates = [ds.dates[i] for i in tr_idx]
        train_rain = ds.rain[tr_idx]
        query_dates = [ds.dates[i] for i in te_idx]
        p = models.prophet_predict(train_dates, train_rain, query_dates, h)
        preds.append(p)
        actuals.append(y[te])
    return _metrics(np.concatenate(actuals), np.concatenate(preds), ref)


def train(db: Session) -> list[dict]:
    ds = datasets.build(db)
    if ds is None:
        print("[ml] not enough data.")
        return []

    rows: list[dict] = []
    for h in HORIZONS:
        y_all = ds.targets[h]
        mask = ~np.isnan(y_all)
        valid_idx = np.where(mask)[0]
        X = ds.X[valid_idx]
        y = y_all[valid_idx]
        ref = float(np.median(y))
        horizon = f"{h}d"
        print(f"[ml] horizon {horizon}: {len(y)} samples")

        results = []
        for name in models.TABULAR:
            m = _eval_tabular(name, X, y, ref)
            results.append((name, m))
            print(f"[ml]   {name:14s} rmse={m['rmse']:.1f} mae={m['mae']:.1f} "
                  f"hit={m['hit_rate']:.2f} dir={m['directional_acc']:.2f}")
        try:
            m = _eval_prophet(ds, valid_idx, h, y, ref)
            results.append(("prophet", m))
            print(f"[ml]   {'prophet':14s} rmse={m['rmse']:.1f} mae={m['mae']:.1f} "
                  f"hit={m['hit_rate']:.2f} dir={m['directional_acc']:.2f}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ml]   prophet skipped: {exc}")

        # Deep-learning sequence models (LSTM, Transformer) — holdout eval.
        if dl.torch_available():
            for name in dl.DL_MODELS:
                try:
                    m = dl.eval_holdout(name, ds.X, ds.targets[h], _metrics, ref)
                    if m:
                        results.append((name, m))
                        print(f"[ml]   {name:14s} rmse={m['rmse']:.1f} mae={m['mae']:.1f} "
                              f"hit={m['hit_rate']:.2f} dir={m['directional_acc']:.2f} (holdout)")
                except Exception as exc:  # noqa: BLE001
                    print(f"[ml]   {name} skipped: {exc}")

        champ = min(results, key=lambda r: r[1]["rmse"])[0]
        for name, m in results:
            rows.append({
                "model_name": name, "model_version": VERSION, "horizon": horizon,
                "target_kind": "regression", "rmse": round(m["rmse"], 3), "mae": round(m["mae"], 3),
                "hit_rate": round(m["hit_rate"], 4), "directional_acc": round(m["directional_acc"], 4),
                "cv_folds": N_SPLITS, "params": None, "is_champion": (name == champ),
            })

    # Replace this version's leaderboard atomically.
    db.execute(delete(ModelRun).where(ModelRun.model_version == VERSION))
    db.commit()
    upsert(db, ModelRun, rows, ["model_name", "model_version", "horizon", "target_kind"])
    print(f"[ml] leaderboard written: {len(rows)} rows")
    return rows


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        train(db)
    finally:
        db.close()
