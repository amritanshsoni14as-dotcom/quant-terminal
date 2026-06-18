"""Ingestion framework: HTTP client + portable upsert.

Every connector is a small function that fetches from a source and calls
`upsert()` with rows keyed by a natural unique key. Upserts are idempotent so
backfills and daily incremental pulls can be re-run safely. Adding a new source
(IMD, ECMWF, ...) means writing one connector — no changes elsewhere.
"""
from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.db import engine

USER_AGENT = "RAINMUMBAI-Terminal/0.1 (research)"


def http_get_json(url: str, params: dict | None = None, retries: int = 3, timeout: int = 60) -> Any:
    """GET JSON with simple exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(
                timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_exc}")


def http_get_text(url: str, retries: int = 3, timeout: int = 60) -> str:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(
                timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_exc}")


def upsert(db: Session, model: type, rows: Iterable[dict], index_elements: list[str]) -> int:
    """Dialect-aware bulk upsert (ON CONFLICT ... DO UPDATE).

    Works on both SQLite and PostgreSQL. `index_elements` are the columns of the
    target's unique/primary constraint. Non-key columns are overwritten on conflict.
    """
    rows = [r for r in rows if r]
    if not rows:
        return 0

    dialect = engine.dialect.name
    table = model.__table__
    insert_fn = sqlite_insert if dialect == "sqlite" else pg_insert

    # Columns to update on conflict = all inserted columns except the key columns.
    sample_cols = set(rows[0].keys())
    update_cols = [c for c in sample_cols if c not in index_elements]
    ncols = max(len(sample_cols), 1)

    # Postgres caps at 65535 bound params; SQLite at ~32k. Stay well under both.
    max_params = 20000 if dialect == "sqlite" else 60000
    batch_size = max(1, max_params // ncols)

    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        stmt = insert_fn(table).values(batch)
        if update_cols:
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_={c: excluded[c] for c in update_cols},
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
        db.execute(stmt)
    db.commit()
    return len(rows)


def get_or_create_location(db: Session) -> int:
    """Ensure the primary location row exists; return its id."""
    from app.core.config import settings
    from app.models.orm import Location

    loc = db.execute(select(Location).where(Location.code == settings.PRIMARY_CODE)).scalar_one_or_none()
    if loc:
        return loc.id
    loc = Location(
        code=settings.PRIMARY_CODE,
        name=settings.PRIMARY_NAME,
        latitude=settings.PRIMARY_LAT,
        longitude=settings.PRIMARY_LON,
        imd_station="Santacruz",
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc.id
