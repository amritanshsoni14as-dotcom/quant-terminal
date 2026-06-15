"""SQLAlchemy ORM models (Phase 1 subset of db/schema.sql).

DB-agnostic: uses generic types so the same models run on SQLite (local dev)
and PostgreSQL (production). The canonical Postgres DDL lives in db/schema.sql.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    imd_station: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawWeather(Base):
    __tablename__ = "raw_weather"
    __table_args__ = (UniqueConstraint("location_id", "obs_date", "source", name="uq_raw_weather"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    temp_max_c: Mapped[float | None] = mapped_column(Float)
    temp_min_c: Mapped[float | None] = mapped_column(Float)
    temp_mean_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    wind_kmh: Mapped[float | None] = mapped_column(Float)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawWeatherForecast(Base):
    __tablename__ = "raw_weather_forecast"
    __table_args__ = (
        UniqueConstraint("location_id", "issued_at", "target_date", "source", name="uq_raw_fc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    temp_mean_c: Mapped[float | None] = mapped_column(Float)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawClimateDriver(Base):
    __tablename__ = "raw_climate_drivers"
    __table_args__ = (UniqueConstraint("driver", "obs_date", "source", name="uq_driver"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver: Mapped[str] = mapped_column(String, nullable=False, index=True)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FeaturesDaily(Base):
    __tablename__ = "features_daily"

    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    rain_roll_7: Mapped[float | None] = mapped_column(Float)
    rain_roll_30: Mapped[float | None] = mapped_column(Float)
    rain_season_cum: Mapped[float | None] = mapped_column(Float)
    rain_anomaly_pct: Mapped[float | None] = mapped_column(Float)
    temp_mean_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    wind_kmh: Mapped[float | None] = mapped_column(Float)
    oni: Mapped[float | None] = mapped_column(Float)
    iod_dmi: Mapped[float | None] = mapped_column(Float)
    mjo_phase: Mapped[int | None] = mapped_column(Integer)
    mjo_amp: Mapped[float | None] = mapped_column(Float)
    sst_anom: Mapped[float | None] = mapped_column(Float)
    monsoon_progress: Mapped[float | None] = mapped_column(Float)
    extra: Mapped[dict | None] = mapped_column(JSON)
    built_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Climatology(Base):
    __tablename__ = "climatology"

    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), primary_key=True)
    doy: Mapped[int] = mapped_column(Integer, primary_key=True)
    rain_mean_mm: Mapped[float | None] = mapped_column(Float)
    rain_std_mm: Mapped[float | None] = mapped_column(Float)
    rain_p10: Mapped[float | None] = mapped_column(Float)
    rain_p90: Mapped[float | None] = mapped_column(Float)


# ---------------------------------------------------------------------------
# Phase 2 — Derivative (Module 2), Probability (Module 8), Signal (Module 9)
# ---------------------------------------------------------------------------
class ContractSpec(Base):
    __tablename__ = "contract_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    description: Mapped[str | None] = mapped_column(String)
    accrual_start: Mapped[date | None] = mapped_column(Date)
    accrual_end: Mapped[date | None] = mapped_column(Date)
    payoff_type: Mapped[str | None] = mapped_column(String)   # index_linear | capped | binary
    payoff_params: Mapped[dict | None] = mapped_column(JSON)
    lot_size: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ContractPrice(Base):
    __tablename__ = "contract_prices"
    __table_args__ = (UniqueConstraint("symbol", "trade_date", name="uq_contract_price"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("contract_specs.symbol"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[float | None] = mapped_column(Float)
    high_price: Mapped[float | None] = mapped_column(Float)
    low_price: Mapped[float | None] = mapped_column(Float)
    close_price: Mapped[float | None] = mapped_column(Float)
    settle_price: Mapped[float | None] = mapped_column(Float)
    open_interest: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, default="manual")


class ContractFairValue(Base):
    __tablename__ = "contract_fair_value"
    __table_args__ = (UniqueConstraint("symbol", "as_of", name="uq_fair_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("contract_specs.symbol"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    fair_value: Mapped[float | None] = mapped_column(Float)
    market_price: Mapped[float | None] = mapped_column(Float)
    mispricing: Mapped[float | None] = mapped_column(Float)
    expected_settle: Mapped[float | None] = mapped_column(Float)
    inputs: Mapped[dict | None] = mapped_column(JSON)


class ProbabilitySnapshot(Base):
    __tablename__ = "probability_snapshots"
    __table_args__ = (UniqueConstraint("location_id", "as_of", "scope", name="uq_prob_snap"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    scope: Mapped[str] = mapped_column(String, nullable=False)   # 'seasonal'
    p_above_norm: Mapped[float | None] = mapped_column(Float)
    p_below_norm: Mapped[float | None] = mapped_column(Float)
    p_above_10: Mapped[float | None] = mapped_column(Float)
    p_above_20: Mapped[float | None] = mapped_column(Float)
    p_below_10: Mapped[float | None] = mapped_column(Float)
    p_below_20: Mapped[float | None] = mapped_column(Float)
    posterior_params: Mapped[dict | None] = mapped_column(JSON)


class TradingSignal(Base):
    __tablename__ = "trading_signals"
    __table_args__ = (UniqueConstraint("symbol", "as_of", name="uq_signal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("contract_specs.symbol"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    components: Mapped[dict | None] = mapped_column(JSON)


class SignalLog(Base):
    """Append-only journal of the model's signal calls — one row per meaningful change
    (state transition or first entry). Powers the dashboard's signal track record."""
    __tablename__ = "signal_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    prev_signal: Mapped[str | None] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String, default="change")  # 'first' | 'change'
    note: Mapped[str | None] = mapped_column(String)


# ---------------------------------------------------------------------------
# Phase 3 — ML Lab (Module 6) + Forecast Revision Engine (Module 7)
# ---------------------------------------------------------------------------
class ModelRun(Base):
    __tablename__ = "model_runs"
    __table_args__ = (
        UniqueConstraint("model_name", "model_version", "horizon", "target_kind", name="uq_model_run"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    horizon: Mapped[str] = mapped_column(String, nullable=False)        # 1d|3d|7d|15d|30d|seasonal
    target_kind: Mapped[str] = mapped_column(String, nullable=False)    # regression|classification
    trained_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    rmse: Mapped[float | None] = mapped_column(Float)
    mae: Mapped[float | None] = mapped_column(Float)
    hit_rate: Mapped[float | None] = mapped_column(Float)
    directional_acc: Mapped[float | None] = mapped_column(Float)
    cv_folds: Mapped[int | None] = mapped_column(Integer)
    params: Mapped[dict | None] = mapped_column(JSON)
    is_champion: Mapped[bool] = mapped_column(default=False)


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("location_id", "issued_date", "horizon", "target_date", "model_name",
                         name="uq_forecast"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon: Mapped[str] = mapped_column(String, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date)
    model_name: Mapped[str] = mapped_column(String, default="champion")
    point_mm: Mapped[float | None] = mapped_column(Float)
    p10_mm: Mapped[float | None] = mapped_column(Float)
    p90_mm: Mapped[float | None] = mapped_column(Float)
    prob_above_norm: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ForecastRevision(Base):
    __tablename__ = "forecast_revisions"
    __table_args__ = (
        UniqueConstraint("location_id", "horizon", "curr_issued_date", "target_label",
                         name="uq_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    horizon: Mapped[str] = mapped_column(String, nullable=False)
    target_label: Mapped[str] = mapped_column(String, default="seasonal")
    prev_issued_date: Mapped[date | None] = mapped_column(Date)
    curr_issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    prev_point_mm: Mapped[float | None] = mapped_column(Float)
    curr_point_mm: Mapped[float | None] = mapped_column(Float)
    revision_mm: Mapped[float | None] = mapped_column(Float)
    revision_pct: Mapped[float | None] = mapped_column(Float)
    direction: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RevisionPrediction(Base):
    __tablename__ = "revision_predictions"
    __table_args__ = (
        UniqueConstraint("location_id", "as_of", "horizon", name="uq_rev_pred"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    horizon: Mapped[str] = mapped_column(String, nullable=False)
    prob_revise_up: Mapped[float | None] = mapped_column(Float)
    prob_revise_down: Mapped[float | None] = mapped_column(Float)
    expected_revision_mm: Mapped[float | None] = mapped_column(Float)
    expected_market_impact: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)


# ---------------------------------------------------------------------------
# Multi-commodity (price-based markets) — gold, silver, crude, natgas, copper…
# ---------------------------------------------------------------------------
class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)   # GOLD, CRUDE…
    name: Mapped[str] = mapped_column(String, nullable=False)
    yahoo_ticker: Mapped[str | None] = mapped_column(String)                   # GC=F, CL=F…
    asset_class: Mapped[str | None] = mapped_column(String)                    # metal | energy
    currency: Mapped[str | None] = mapped_column(String)
    unit: Mapped[str | None] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AssetPrice(Base):
    __tablename__ = "asset_prices"
    __table_args__ = (UniqueConstraint("asset_id", "obs_date", name="uq_asset_price"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    adj_close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, default="yahoo")
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CommodityForecast(Base):
    """Per-commodity probabilistic forecast (bull/bear/neutral) per horizon."""
    __tablename__ = "commodity_forecasts"
    __table_args__ = (UniqueConstraint("symbol", "as_of", "horizon", name="uq_cmdty_forecast"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    horizon: Mapped[str] = mapped_column(String, nullable=False)   # 5d|21d|63d
    point_return_pct: Mapped[float | None] = mapped_column(Float)
    p_bull: Mapped[float | None] = mapped_column(Float)
    p_bear: Mapped[float | None] = mapped_column(Float)
    p_neutral: Mapped[float | None] = mapped_column(Float)
    expected_price: Mapped[float | None] = mapped_column(Float)
    model: Mapped[str | None] = mapped_column(String)
    drivers: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FundamentalSeries(Base):
    """Generic fundamental time series — all non-price connectors (CFTC COT, EIA,
    FRED, USDA, USGS…) write here under (commodity symbol, indicator key)."""
    __tablename__ = "fundamental_series"
    __table_args__ = (UniqueConstraint("symbol", "key", "obs_date", name="uq_fund_series"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)   # CRUDE, COPPER…
    key: Mapped[str] = mapped_column(String, nullable=False, index=True)      # cot_net_spec, eia_crude_stocks…
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, default="")
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AltDocument(Base):
    __tablename__ = "alt_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    raw_text: Mapped[str | None] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(String)
    sentiment: Mapped[float | None] = mapped_column(Float)
    factors: Mapped[dict | None] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DailyBrief(Base):
    __tablename__ = "daily_brief"
    __table_args__ = (UniqueConstraint("symbol", "as_of", name="uq_brief"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("contract_specs.symbol"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    rainfall_forecast: Mapped[dict | None] = mapped_column(JSON)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    revision_probability: Mapped[float | None] = mapped_column(Float)
    expected_season_mm: Mapped[float | None] = mapped_column(Float)
    fair_value: Mapped[float | None] = mapped_column(Float)
    signal: Mapped[str | None] = mapped_column(String)
    bullish_factors: Mapped[dict | None] = mapped_column(JSON)
    bearish_factors: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
