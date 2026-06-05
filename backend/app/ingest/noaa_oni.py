"""NOAA CPC connector: ONI (Oceanic Niño Index) — the ENSO driver.

Parses the fixed-width oni.ascii.txt. Each 3-month season's anomaly is stored
at the season's centre month (day 15). Source: free, no key.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.ingest.base import http_get_text, upsert
from app.models.orm import RawClimateDriver

URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SOURCE = "noaa_cpc"

# 12 seasons in file order map to centre months Jan..Dec.
_SEASON_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def fetch_history(db: Session, location_id: int | None = None) -> int:
    text = http_get_text(URL)
    rows = []
    for line in text.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 4:
            continue
        seas, yr, _total, anom = parts[0], parts[1], parts[2], parts[3]
        month = _SEASON_MONTH.get(seas)
        if month is None:
            continue
        try:
            rows.append(
                {
                    "driver": "ONI",
                    "obs_date": date(int(yr), month, 15),
                    "value": float(anom),
                    "source": SOURCE,
                }
            )
        except ValueError:
            continue
    return upsert(db, RawClimateDriver, rows, ["driver", "obs_date", "source"])
