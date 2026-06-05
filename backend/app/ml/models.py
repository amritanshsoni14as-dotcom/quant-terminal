"""Model registry for the ML Lab.

Tabular models share the sklearn fit/predict interface. Prophet is univariate
and handled separately by the trainer. LSTM/Transformer are Phase 4.
"""
from __future__ import annotations

import numpy as np


def build_tabular(name: str):
    if name == "linreg":
        from sklearn.linear_model import LinearRegression
        return LinearRegression()
    if name == "random_forest":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
    if name == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8, n_jobs=-1, random_state=42, verbosity=0,
        )
    if name == "lightgbm":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(
            n_estimators=300, max_depth=-1, num_leaves=31, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42, verbose=-1,
        )
    raise ValueError(f"unknown tabular model: {name}")


TABULAR = ["linreg", "random_forest", "xgboost", "lightgbm"]


def prophet_predict(train_dates, train_rain, query_dates, horizon: int) -> np.ndarray:
    """Fit Prophet on the daily rainfall history, then for each query date d
    return the summed forecast over d+1 .. d+horizon. Negative yhat clamped to 0."""
    import logging
    from datetime import timedelta

    import pandas as pd
    from prophet import Prophet

    logging.getLogger("prophet").setLevel(logging.CRITICAL)
    logging.getLogger("cmdstanpy").setLevel(logging.CRITICAL)

    dft = pd.DataFrame({"ds": pd.to_datetime(train_dates), "y": train_rain})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(dft)

    last = max(train_dates)
    horizon_end = max(query_dates) + timedelta(days=horizon)
    periods = (horizon_end - last).days
    if periods <= 0:
        return np.zeros(len(query_dates))
    future = m.make_future_dataframe(periods=periods, freq="D")
    fc = m.predict(future)
    yhat = dict(zip(fc["ds"].dt.date, np.clip(fc["yhat"].to_numpy(), 0, None)))

    out = np.zeros(len(query_dates))
    for i, d in enumerate(query_dates):
        out[i] = sum(yhat.get(d + timedelta(days=k), 0.0) for k in range(1, horizon + 1))
    return out
