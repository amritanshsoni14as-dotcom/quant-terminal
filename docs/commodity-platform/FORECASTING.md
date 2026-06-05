# Forecasting Framework + ML Models

## Philosophy
Two complementary engines, both explainable:
1. **Fundamental scoring** (nowcast) — *why is it moving now?* The config-weighted category →
   composite Health Score. Slow-moving, interpretable, driver-attributed.
2. **Probabilistic forecast** (what next?) — ML ensemble predicting forward returns and converting
   them into **bull / bear / neutral probabilities** per horizon.

Final published probabilities **blend** both: the score tilts the prior; ML shapes the distribution.

## Targets
Per horizon `h ∈ {5d, 21d, 63d}` (config-driven): forward log-return `r_h = ln(P_{t+h}/P_t)`.
- Regression head → expected return + prediction interval (p10/p90).
- Classification head → P(up>+threshold), P(down<−threshold), P(neutral) where threshold scales
  with the commodity's volatility (e.g. ±0.5σ_h).

## Features (assembled generically from indicators)
- **Price/technical:** returns, momentum (RSI, MACD), realized vol, distance from SMA50/200,
  curve slope (contango/backwardation), roll yield.
- **Fundamental:** every indicator's normalized value + the 6 category scores.
- **Positioning:** COT net-spec percentile, Δ positioning.
- **Macro:** USD, real yields, PMI (z-scored).
- **Seasonal:** month-of-year sin/cos, days-to-harvest/maintenance.
- **Lead indicators:** top correlations discovered in Section 13 (auto-fed back as features).
All features are lagged to the data's true availability date → **no look-ahead**.

## Validation
Expanding-window time-series CV (no leakage). Metrics: RMSE, MAE, directional accuracy, and a
probability score (Brier / log-loss) for the bull/bear/neutral head. Champion per horizon promoted;
every forecast stored with its `model` + `drivers` for audit.

## Converting to probabilities
- Ensemble members each emit a forward-return draw; pool → empirical distribution.
- P(bull)=P(r>+thr), P(bear)=P(r<−thr), P(neutral)=between. Calibrate with isotonic/Platt on history.
- Blend with the fundamental composite: `final = w·ml_probs + (1−w)·score_prior` (w from backtest).

## ML models<a id="ml-models"></a>
| Tier | Models | Role |
|---|---|---|
| Baselines | Naive/seasonal-naive, Linear/Ridge | sanity floor |
| Trees (workhorse) | **XGBoost, LightGBM, RandomForest** | main return predictors on the feature matrix |
| Time-series | **Prophet**, SARIMAX, ETS | trend/seasonality on price |
| Deep (optional) | **LSTM, Temporal Fusion Transformer (TFT)**, N-BEATS | multi-horizon sequence forecasting once data depth justifies it |
| Probabilistic | Quantile GBM / NGBoost, conformal prediction | calibrated intervals → bull/bear/neutral |
| Meta | Stacked ensemble (weights by CV skill) | the published forecast |
| Causal / explain | SHAP on the champion; Granger tests for lead indicators | "why" attribution feeding Copilot |

All of XGBoost/LightGBM/Prophet/LSTM/Transformer are **already installed and proven** on this
machine from the weather build — reuse the existing ML harness, just swap targets/features.

## Digital Twin (Section 15) forecasting
Separate from ML: an **elasticity model** from config `twin.elasticities`.
`Δprice% ≈ Σ_driver ( elasticity_driver × Δdriver% )`, optionally enriched by a fundamentals-trained
sensitivity (regression of returns on indicator shocks). Returns a waterfall of each driver's impact.

## Backtesting
Walk-forward: at each date use only data then-available, generate signal/probabilities, evaluate
forward returns. Report hit-rate, P&L of a simple score-threshold strategy, calibration curves.
