"""Module 7 — Forecast Revision Engine (the primary trading alpha).

Rainfall derivatives reprice on how the *seasonal forecast changes*, not on
today's rain. So we:

  1. Reconstruct, with no look-ahead, the seasonal-rainfall expectation
     E[season] as it would have been known on each date of each past monsoon
     (analog regression using only prior years).
  2. Difference consecutive estimates → the realised forecast *revisions*.
  3. Train a model to predict whether the NEXT revision is up or down (and its
     size) from the climate drivers, season progress, and revision momentum.
  4. Emit P(revise up), expected revision (mm) and expected market impact for
     the current date — the dominant input to the trading signal.

Cadence is weekly to keep the reconstruction tractable.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingest.base import upsert
from app.models.orm import (
    ContractSpec,
    FeaturesDaily,
    Forecast,
    ForecastRevision,
    Location,
    ModelRun,
    RevisionPrediction,
)
from app.signals.probability import _rain_by_year, _season_sum  # reuse helpers

SEASON = (settings.MONSOON_START_MONTH, settings.MONSOON_START_DAY,
          settings.MONSOON_END_MONTH, settings.MONSOON_END_DAY)
STEP = 7
DRIVER_FEATS = ["oni", "iod_dmi", "mjo_phase", "mjo_amp", "monsoon_progress", "rain_anomaly_pct"]


def _reconstruct_mu(by_year: dict, year: int, upto_md: tuple[int, int]) -> tuple[float, float] | None:
    """E[full season] on (year, upto_md) using only seasons strictly before `year`."""
    full_totals, pairs = [], []
    for y, days in by_year.items():
        if y >= year:
            continue
        full = _season_sum(days, y, None)
        if full <= 0:
            continue
        full_totals.append(full)
        pairs.append((_season_sum(days, y, upto_md), full))
    if len(full_totals) < 5:
        return None
    normal = statistics.fmean(full_totals)
    to_date_now = _season_sum(by_year.get(year, {}), year, upto_md)
    if len(pairs) >= 8:
        xs = np.array([p[0] for p in pairs]); ys = np.array([p[1] for p in pairs])
        sxx = float(np.sum((xs - xs.mean()) ** 2))
        if sxx > 0:
            slope = float(np.sum((xs - xs.mean()) * (ys - ys.mean())) / sxx)
            intercept = float(ys.mean() - slope * xs.mean())
            return intercept + slope * to_date_now, normal
    return normal, normal


def _season_dates(year: int, last_avail: date) -> list[date]:
    sm, sd, em, ed = SEASON
    start, end = date(year, sm, sd), min(date(year, em, ed), last_avail)
    out, d = [], start
    while d <= end:
        out.append(d)
        d += timedelta(days=STEP)
    return out


def compute(db: Session) -> dict | None:
    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc is None:
        return None
    feats = {r.obs_date: r for r in db.execute(
        select(FeaturesDaily).where(FeaturesDaily.location_id == loc.id)
    ).scalars()}
    if not feats:
        return None
    last_avail = max(feats)
    by_year = _rain_by_year(db, loc.id)

    sm, sd_, em, ed = SEASON
    cur_year = last_avail.year if (last_avail.month, last_avail.day) >= (sm, sd_) else last_avail.year - 1

    def feat_at(d: date):
        r = feats.get(d)
        if r is None:  # nearest earlier
            cand = [x for x in feats if x <= d]
            if not cand:
                return None
            r = feats[max(cand)]
        return [float(getattr(r, c) if getattr(r, c) is not None else 0.0) for c in DRIVER_FEATS]

    # Build mu series per season + the training table.
    Xrows, y_dir, y_size, season_series = [], [], [], {}
    for year in sorted(by_year):
        dates = _season_dates(year, last_avail)
        if len(dates) < 2:
            continue
        mus = []
        for d in dates:
            r = _reconstruct_mu(by_year, year, (d.month, d.day))
            mus.append(r[0] if r else None)
        season_series[year] = list(zip(dates, mus))
        for i in range(1, len(dates) - 1):
            if mus[i] is None or mus[i - 1] is None or mus[i + 1] is None:
                continue
            fv = feat_at(dates[i])
            if fv is None:
                continue
            momentum = mus[i] - mus[i - 1]
            nxt = mus[i + 1] - mus[i]
            Xrows.append(fv + [momentum])
            y_dir.append(1 if nxt > 0 else 0)
            y_size.append(nxt)

    if len(Xrows) < 60:
        print("[revision] insufficient reconstructed history.")
        return None

    X = np.array(Xrows); yd = np.array(y_dir); ys = np.array(y_size)
    # Time-ordered split (last 20% as test).
    cut = int(len(X) * 0.8)
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    clf = RandomForestClassifier(n_estimators=250, max_depth=8, n_jobs=-1, random_state=42)
    reg = RandomForestRegressor(n_estimators=250, max_depth=8, n_jobs=-1, random_state=42)
    clf.fit(X[:cut], yd[:cut]); reg.fit(X[:cut], ys[:cut])
    test_acc = float(np.mean(clf.predict(X[cut:]) == yd[cut:])) if len(X) - cut > 0 else float("nan")
    base_rate = float(np.mean(yd))
    # Refit on all for live prediction.
    clf.fit(X, yd); reg.fit(X, ys)

    # ---- Current prediction ----
    upto_md = (last_avail.month, last_avail.day)
    in_season = date(cur_year, sm, sd_) <= last_avail <= date(cur_year, em, ed)
    pred = None
    if in_season:
        cur = _reconstruct_mu(by_year, cur_year, upto_md)
        prev = _reconstruct_mu(by_year, cur_year, ((last_avail - timedelta(days=STEP)).month,
                                                   (last_avail - timedelta(days=STEP)).day))
        fv = feat_at(last_avail)
        if cur and fv:
            momentum = (cur[0] - prev[0]) if prev else 0.0
            xrow = np.array([fv + [momentum]])
            p_up = float(clf.predict_proba(xrow)[0][list(clf.classes_).index(1)]) if 1 in clf.classes_ else 0.5
            exp_size = float(reg.predict(xrow)[0])
            pred = {"p_up": p_up, "exp_size": exp_size, "in_season": True}
    if pred is None:
        pred = {"p_up": 0.5, "exp_size": 0.0, "in_season": False}

    # Contract tick for market-impact scaling.
    spec = db.execute(select(ContractSpec).where(ContractSpec.symbol == "RAINMUMBAI")).scalar_one_or_none()
    tick = (spec.payoff_params or {}).get("tick", 1.0) if spec else 1.0

    margin = abs(pred["p_up"] - 0.5) * 2
    confidence = round(max(0.0, min(1.0, (test_acc if test_acc == test_acc else base_rate) * (0.5 + 0.5 * margin))), 3)

    # ---- Persist ----
    # Show the current season if it already has a few points, else the most recent
    # complete season so the chart illustrates how the forecast evolves & revises.
    def _valid_points(series):
        return [s for s in series if s[1] is not None]

    display_year = cur_year
    if len(_valid_points(season_series.get(cur_year, []))) < 4:
        past = [y for y in season_series if y < cur_year and len(_valid_points(season_series[y])) >= 4]
        if past:
            display_year = max(past)
    display_series = season_series.get(display_year, [])
    _persist_forecast_series(db, loc.id, display_series)
    _persist_revisions(db, loc.id, display_series)

    upsert(db, RevisionPrediction, [{
        "location_id": loc.id, "as_of": last_avail, "horizon": "seasonal",
        "prob_revise_up": round(pred["p_up"], 4), "prob_revise_down": round(1 - pred["p_up"], 4),
        "expected_revision_mm": round(pred["exp_size"], 2),
        "expected_market_impact": round(pred["exp_size"] * tick, 2),
        "confidence": confidence,
    }], ["location_id", "as_of", "horizon"])

    db.execute(delete(ModelRun).where(ModelRun.model_name == "revision_rf"))
    db.commit()
    upsert(db, ModelRun, [{
        "model_name": "revision_rf", "model_version": "v1", "horizon": "seasonal",
        "target_kind": "classification", "rmse": round(float(np.sqrt(np.mean((reg.predict(X[cut:]) - ys[cut:]) ** 2))), 2) if len(X) - cut > 0 else None,
        "mae": None, "hit_rate": round(test_acc, 4) if test_acc == test_acc else None,
        "directional_acc": round(test_acc, 4) if test_acc == test_acc else None,
        "cv_folds": 1, "params": {"n_samples": len(X), "base_rate_up": round(base_rate, 3)},
        "is_champion": True,
    }], ["model_name", "model_version", "horizon", "target_kind"])

    print(f"[revision] as_of={last_avail} P(up)={pred['p_up']:.2f} exp={pred['exp_size']:.1f}mm "
          f"test_acc={test_acc:.2f} n={len(X)}")
    return {"prediction": pred, "test_acc": test_acc, "n_samples": len(X),
            "confidence": confidence, "tick": tick}


def _persist_forecast_series(db: Session, loc_id: int, series: list) -> None:
    rows = [{
        "location_id": loc_id, "issued_date": d, "horizon": "seasonal", "target_date": None,
        "model_name": "revision_recon", "point_mm": round(mu, 1) if mu is not None else None,
        "p10_mm": None, "p90_mm": None, "prob_above_norm": None, "confidence": None,
    } for d, mu in series if mu is not None]
    if rows:
        upsert(db, Forecast, rows, ["location_id", "issued_date", "horizon", "target_date", "model_name"])


def _persist_revisions(db: Session, loc_id: int, series: list) -> None:
    rows = []
    for i in range(1, len(series)):
        (pd, pmu), (cd, cmu) = series[i - 1], series[i]
        if pmu is None or cmu is None:
            continue
        rev = cmu - pmu
        rows.append({
            "location_id": loc_id, "horizon": "seasonal", "target_label": "seasonal",
            "prev_issued_date": pd, "curr_issued_date": cd,
            "prev_point_mm": round(pmu, 1), "curr_point_mm": round(cmu, 1),
            "revision_mm": round(rev, 1), "revision_pct": round(rev / pmu * 100, 2) if pmu else None,
            "direction": "up" if rev > 1 else "down" if rev < -1 else "flat",
        })
    if rows:
        upsert(db, ForecastRevision, rows,
               ["location_id", "horizon", "curr_issued_date", "target_label"])
