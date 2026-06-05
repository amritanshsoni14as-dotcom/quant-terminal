"""One-shot backfill + daily refresh orchestrator.

Usage:
    python -m app.ingest.backfill            # full 25y backfill + features
    python -m app.ingest.backfill --daily    # incremental (last 45 days) + features
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.features.builder import build_features
from app.ingest import drivers, nasa_power, noaa_oni, open_meteo
from app.ingest.base import get_or_create_location


def run(full: bool = True) -> None:
    init_db()
    db = SessionLocal()
    try:
        location_id = get_or_create_location(db)
        today = date.today()
        if full:
            start = date(today.year - settings.BACKFILL_YEARS, 1, 1)
        else:
            start = today - timedelta(days=45)
        # Open-Meteo archive lags a few days; cap the end conservatively.
        end = today - timedelta(days=2)

        print(f"[backfill] weather {start} -> {end}")
        n = open_meteo.fetch_history(db, location_id, start, end)
        print(f"[backfill]   open-meteo rows: {n}")
        n = nasa_power.fetch_history(db, location_id, start, end)
        print(f"[backfill]   nasa-power rows: {n}")

        # Near-real-time recent days (incl. today) to close the archive lag.
        try:
            n = open_meteo.fetch_recent(db, location_id, past_days=21)
            print(f"[backfill]   open-meteo recent rows: {n}")
        except Exception as exc:  # noqa: BLE001
            print(f"[backfill]   recent skipped: {exc}")

        print("[backfill] forward forecast")
        try:
            n = open_meteo.fetch_forecast(db, location_id)
            print(f"[backfill]   forecast rows: {n}")
        except Exception as exc:  # noqa: BLE001
            print(f"[backfill]   forecast skipped: {exc}")

        print("[backfill] climate drivers")
        print(f"[backfill]   ONI rows: {noaa_oni.fetch_history(db)}")
        print(f"[backfill]   IOD rows: {drivers.fetch_iod(db)}")
        print(f"[backfill]   MJO rows: {drivers.fetch_mjo(db)}")

        print("[backfill] building features + climatology")
        n = build_features(db)
        print(f"[backfill]   features_daily rows: {n}")

        print("[backfill] training ML lab + writing forecasts (Module 6)")
        try:
            from app.ml.run import run as run_ml
            run_ml()
        except Exception as exc:  # noqa: BLE001
            print(f"[backfill]   ML lab skipped: {exc}")

        print("[backfill] computing signals (probability / revision / fair value / signal / brief)")
        try:
            from app.signals.run import run as run_signals
            run_signals()
        except Exception as exc:  # noqa: BLE001
            print(f"[backfill]   signals skipped: {exc}")
        print("[backfill] done.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily", action="store_true", help="incremental refresh")
    args = parser.parse_args()
    run(full=not args.daily)
