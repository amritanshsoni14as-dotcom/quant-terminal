"""In-process scheduler (APScheduler) so the dashboard self-updates while the
backend runs — no OS-level cron/Task Scheduler (and no admin) required.

- light_refresh: every 60 min + once shortly after startup.
- ml_refresh: every 24 h.
"""
from __future__ import annotations

import datetime as _dt

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.refresh import (
    commodity_refresh,
    forecast_refresh,
    fundamentals_refresh,
    light_refresh,
    ml_refresh,
)

_scheduler: BackgroundScheduler | None = None


def _run(job, name):
    try:
        msg = job()
        print(f"[scheduler] {name}: {msg}")
    except Exception as exc:  # noqa: BLE001
        print(f"[scheduler] {name} failed: {exc}")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    sched = BackgroundScheduler(daemon=True, timezone="UTC")
    # Refresh weather + signals hourly; first run ~20s after startup.
    sched.add_job(lambda: _run(light_refresh, "light_refresh"), "interval",
                  minutes=60, coalesce=True, max_instances=1, id="light",
                  next_run_time=_dt.datetime.now() + _dt.timedelta(seconds=20))
    # Retrain ML lab daily.
    sched.add_job(lambda: _run(ml_refresh, "ml_refresh"), "interval",
                  hours=24, coalesce=True, max_instances=1, id="ml")
    # Update commodity prices every 6h (Yahoo daily bars); first run ~40s after boot.
    sched.add_job(lambda: _run(commodity_refresh, "commodity_refresh"), "interval",
                  hours=6, coalesce=True, max_instances=1, id="commodities",
                  next_run_time=_dt.datetime.now() + _dt.timedelta(seconds=40))
    # Commodity fundamentals (CFTC COT free + EIA/FRED if keyed); first run ~60s after boot.
    sched.add_job(lambda: _run(fundamentals_refresh, "fundamentals_refresh"), "interval",
                  hours=12, coalesce=True, max_instances=1, id="fundamentals",
                  next_run_time=_dt.datetime.now() + _dt.timedelta(seconds=60))
    # Commodity forecasts (LightGBM); daily, first run ~90s after boot.
    sched.add_job(lambda: _run(forecast_refresh, "forecast_refresh"), "interval",
                  hours=24, coalesce=True, max_instances=1, id="cmdty_forecast",
                  next_run_time=_dt.datetime.now() + _dt.timedelta(seconds=90))
    sched.start()
    _scheduler = sched
    print("[scheduler] started (light=60min, ml=24h, commodities=6h, fundamentals=12h, forecast=24h)")
