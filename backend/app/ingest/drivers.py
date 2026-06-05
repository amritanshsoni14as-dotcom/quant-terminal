"""IOD (DMI) and MJO (RMM) connectors — best-effort, free sources.

These enrich the feature store. If a source is unreachable the connector logs
and returns 0 so the pipeline degrades gracefully (Module 1 does not depend on
them).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.ingest.base import http_get_text, upsert
from app.models.orm import RawClimateDriver

# IOD Dipole Mode Index (HadISST) — NOAA PSL long time series.
DMI_URL = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data"
# MJO RMM index (real-time) — Australian BoM.
RMM_URL = "http://www.bom.gov.au/clim_data/IDCKGEM000/rmm.74toRealtime.txt"


def fetch_iod(db: Session) -> int:
    """Parse the 'year + 12 monthly values' PSL format; store at mid-month."""
    try:
        text = http_get_text(DMI_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"[drivers] IOD fetch skipped: {exc}")
        return 0

    rows = []
    missing_tokens = {"-9999", "-9999.0", "-999.0", "NaN"}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 13:
            continue
        try:
            year = int(parts[0])
        except ValueError:
            continue
        if not (1800 <= year <= 2100):
            continue
        for month, token in enumerate(parts[1:], start=1):
            if token in missing_tokens:
                continue
            try:
                val = float(token)
            except ValueError:
                continue
            if val <= -100:  # other sentinel
                continue
            rows.append(
                {"driver": "IOD_DMI", "obs_date": date(year, month, 15),
                 "value": val, "source": "noaa_psl"}
            )
    return upsert(db, RawClimateDriver, rows, ["driver", "obs_date", "source"])


def fetch_mjo(db: Session) -> int:
    """Parse BoM RMM daily file -> RMM1, RMM2, phase, amplitude."""
    try:
        text = http_get_text(RMM_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"[drivers] MJO fetch skipped: {exc}")
        return 0

    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            rmm1, rmm2 = float(parts[3]), float(parts[4])
            phase, amp = int(float(parts[5])), float(parts[6])
        except ValueError:
            continue
        if abs(rmm1) > 100 or abs(amp) > 100:  # 1.E36 missing sentinel
            continue
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        rows.extend(
            [
                {"driver": "MJO_RMM1", "obs_date": d, "value": rmm1, "source": "bom"},
                {"driver": "MJO_RMM2", "obs_date": d, "value": rmm2, "source": "bom"},
                {"driver": "MJO_PHASE", "obs_date": d, "value": float(phase), "source": "bom"},
                {"driver": "MJO_AMP", "obs_date": d, "value": amp, "source": "bom"},
            ]
        )
    return upsert(db, RawClimateDriver, rows, ["driver", "obs_date", "source"])
