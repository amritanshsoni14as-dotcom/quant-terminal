"""ML Lab orchestrator — train leaderboard + write champion forecasts.

    python -m app.ml.run
"""
from __future__ import annotations

from app.core.db import SessionLocal, init_db
from app.ml import predict, train


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        train.train(db)
        predict.predict(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
