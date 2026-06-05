"""Database engine/session setup (SQLAlchemy 2.x)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _normalize_url(url: str) -> str:
    # Neon/Supabase hand out 'postgresql://...' — point SQLAlchemy at the psycopg3 driver.
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_url(settings.DATABASE_URL)
_is_sqlite = DATABASE_URL.startswith("sqlite")
# SQLite needs check_same_thread=False for FastAPI's threadpool.
connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}
# Postgres on free tiers drops idle connections; pre-ping keeps the pool healthy.
engine_kwargs = {} if _is_sqlite else {"pool_pre_ping": True, "pool_recycle": 300}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True, **engine_kwargs)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        # WAL lets the API keep reading while the scheduler writes; busy_timeout
        # makes brief write-locks wait instead of erroring.
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables from ORM metadata (used for SQLite local dev)."""
    from app import models  # noqa: F401  (register models on Base)

    Base.metadata.create_all(bind=engine)
