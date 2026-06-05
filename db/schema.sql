-- ============================================================================
-- RAINMUMBAI Terminal — PostgreSQL schema
-- Run: psql "$DATABASE_URL" -f db/schema.sql
-- Optional: CREATE EXTENSION IF NOT EXISTS timescaledb;  (then hypertable raw_weather)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- LOCATIONS  (Mumbai = primary; structured so other cities can be added)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id          SERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,          -- 'MUMBAI'
    name        TEXT NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    imd_station TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- RAW LAYER  (one table per source family; idempotent upserts)
-- ============================================================================

-- Daily observed/reanalysis weather (Open-Meteo, NASA POWER, IMD)
CREATE TABLE IF NOT EXISTS raw_weather (
    id            BIGSERIAL PRIMARY KEY,
    location_id   INT NOT NULL REFERENCES locations(id),
    obs_date      DATE NOT NULL,
    source        TEXT NOT NULL,               -- 'open_meteo' | 'nasa_power' | 'imd'
    rainfall_mm   DOUBLE PRECISION,
    temp_max_c    DOUBLE PRECISION,
    temp_min_c    DOUBLE PRECISION,
    temp_mean_c   DOUBLE PRECISION,
    humidity_pct  DOUBLE PRECISION,
    pressure_hpa  DOUBLE PRECISION,
    wind_kmh      DOUBLE PRECISION,
    ingested_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE (location_id, obs_date, source)
);
CREATE INDEX IF NOT EXISTS ix_raw_weather_loc_date ON raw_weather(location_id, obs_date);

-- Weather forecasts as published (kept versioned to measure revisions later)
CREATE TABLE IF NOT EXISTS raw_weather_forecast (
    id            BIGSERIAL PRIMARY KEY,
    location_id   INT NOT NULL REFERENCES locations(id),
    issued_at     TIMESTAMPTZ NOT NULL,        -- when the forecast was published
    target_date   DATE NOT NULL,               -- the day being forecast
    source        TEXT NOT NULL,               -- 'open_meteo' | 'ecmwf' | ...
    rainfall_mm   DOUBLE PRECISION,
    temp_mean_c   DOUBLE PRECISION,
    ingested_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE (location_id, issued_at, target_date, source)
);

-- Climate drivers (one row per index value per date)
CREATE TABLE IF NOT EXISTS raw_climate_drivers (
    id          BIGSERIAL PRIMARY KEY,
    driver      TEXT NOT NULL,                 -- 'ONI' | 'SOI' | 'IOD_DMI' | 'MJO_RMM1'
                                               -- | 'MJO_RMM2' | 'MJO_PHASE' | 'MJO_AMP' | 'SST_ANOM'
    obs_date    DATE NOT NULL,
    value       DOUBLE PRECISION,
    source      TEXT NOT NULL,                 -- 'noaa_cpc' | 'bom' | ...
    ingested_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (driver, obs_date, source)
);
CREATE INDEX IF NOT EXISTS ix_drivers_driver_date ON raw_climate_drivers(driver, obs_date);

-- ============================================================================
-- DERIVATIVE / CONTRACT LAYER  (Module 2)
-- ============================================================================
CREATE TABLE IF NOT EXISTS contract_specs (
    id              SERIAL PRIMARY KEY,
    symbol          TEXT UNIQUE NOT NULL,      -- 'RAINMUMBAI'
    location_id     INT REFERENCES locations(id),
    description     TEXT,
    accrual_start   DATE,                      -- rainfall accumulation window
    accrual_end     DATE,
    payoff_type     TEXT,                      -- 'index_linear' | 'capped' | 'binary'
    payoff_params   JSONB,                     -- tick value, strike(s), cap/floor, index def
    lot_size        DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Market quotes / settlement prices (CSV or manual ingest)
CREATE TABLE IF NOT EXISTS contract_prices (
    id            BIGSERIAL PRIMARY KEY,
    symbol        TEXT NOT NULL REFERENCES contract_specs(symbol),
    trade_date    DATE NOT NULL,
    open_price    DOUBLE PRECISION,
    high_price    DOUBLE PRECISION,
    low_price     DOUBLE PRECISION,
    close_price   DOUBLE PRECISION,
    settle_price  DOUBLE PRECISION,
    open_interest DOUBLE PRECISION,
    volume        DOUBLE PRECISION,
    source        TEXT DEFAULT 'manual',
    UNIQUE (symbol, trade_date)
);

-- Model fair value + mispricing snapshots
CREATE TABLE IF NOT EXISTS contract_fair_value (
    id            BIGSERIAL PRIMARY KEY,
    symbol        TEXT NOT NULL REFERENCES contract_specs(symbol),
    as_of         DATE NOT NULL,
    fair_value    DOUBLE PRECISION,
    market_price  DOUBLE PRECISION,
    mispricing    DOUBLE PRECISION,            -- fair_value - market_price
    expected_settle DOUBLE PRECISION,
    inputs        JSONB,                       -- distribution params used
    UNIQUE (symbol, as_of)
);

-- ============================================================================
-- FEATURE STORE  (Module 5/6)  — one wide row per location per day
-- ============================================================================
CREATE TABLE IF NOT EXISTS features_daily (
    location_id        INT NOT NULL REFERENCES locations(id),
    obs_date           DATE NOT NULL,
    rainfall_mm        DOUBLE PRECISION,
    rain_roll_7        DOUBLE PRECISION,
    rain_roll_30       DOUBLE PRECISION,
    rain_season_cum    DOUBLE PRECISION,       -- cumulative since monsoon onset / Jun 1
    rain_anomaly_pct   DOUBLE PRECISION,       -- vs day-of-year climatology
    temp_mean_c        DOUBLE PRECISION,
    humidity_pct       DOUBLE PRECISION,
    pressure_hpa       DOUBLE PRECISION,
    wind_kmh           DOUBLE PRECISION,
    oni                DOUBLE PRECISION,
    iod_dmi            DOUBLE PRECISION,
    mjo_phase          INT,
    mjo_amp            DOUBLE PRECISION,
    sst_anom           DOUBLE PRECISION,
    monsoon_progress   DOUBLE PRECISION,       -- 0..1 through the season
    extra              JSONB,                  -- additional engineered lags/features
    built_at           TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (location_id, obs_date)
);

-- Day-of-year climatology (precomputed normals from 20-30y history)
CREATE TABLE IF NOT EXISTS climatology (
    location_id   INT NOT NULL REFERENCES locations(id),
    doy           INT NOT NULL,                -- 1..366
    rain_mean_mm  DOUBLE PRECISION,
    rain_std_mm   DOUBLE PRECISION,
    rain_p10      DOUBLE PRECISION,
    rain_p90      DOUBLE PRECISION,
    PRIMARY KEY (location_id, doy)
);

-- ============================================================================
-- ML LAYER  (Module 6)
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_runs (
    id              BIGSERIAL PRIMARY KEY,
    model_name      TEXT NOT NULL,             -- 'xgboost' | 'lightgbm' | 'prophet' | 'lstm' ...
    model_version   TEXT NOT NULL,
    horizon         TEXT NOT NULL,             -- '1d'|'3d'|'7d'|'15d'|'30d'|'seasonal'
    target_kind     TEXT NOT NULL,             -- 'regression' | 'classification'
    trained_at      TIMESTAMPTZ DEFAULT now(),
    rmse            DOUBLE PRECISION,
    mae             DOUBLE PRECISION,
    hit_rate        DOUBLE PRECISION,
    directional_acc DOUBLE PRECISION,
    cv_folds        INT,
    params          JSONB,
    is_champion     BOOLEAN DEFAULT FALSE,     -- promoted best model for this horizon
    UNIQUE (model_name, model_version, horizon, target_kind)
);

-- Every forecast we ever made (versioned → enables revision tracking)
CREATE TABLE IF NOT EXISTS forecasts (
    id              BIGSERIAL PRIMARY KEY,
    location_id     INT NOT NULL REFERENCES locations(id),
    issued_date     DATE NOT NULL,             -- run date
    horizon         TEXT NOT NULL,
    target_date     DATE,                      -- null for 'seasonal'
    model_run_id    BIGINT REFERENCES model_runs(id),
    point_mm        DOUBLE PRECISION,          -- expected rainfall
    p10_mm          DOUBLE PRECISION,
    p90_mm          DOUBLE PRECISION,
    prob_above_norm DOUBLE PRECISION,
    confidence      DOUBLE PRECISION,          -- 0..1
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (location_id, issued_date, horizon, target_date, model_run_id)
);
CREATE INDEX IF NOT EXISTS ix_forecasts_loc_target ON forecasts(location_id, target_date, horizon);

-- ============================================================================
-- FORECAST REVISION ENGINE  (Module 7 — primary alpha)
-- ============================================================================
CREATE TABLE IF NOT EXISTS forecast_revisions (
    id                 BIGSERIAL PRIMARY KEY,
    location_id        INT NOT NULL REFERENCES locations(id),
    horizon            TEXT NOT NULL,
    target_date        DATE,
    prev_issued_date   DATE,
    curr_issued_date   DATE NOT NULL,
    prev_point_mm      DOUBLE PRECISION,
    curr_point_mm      DOUBLE PRECISION,
    revision_mm        DOUBLE PRECISION,       -- curr - prev
    revision_pct       DOUBLE PRECISION,
    direction          TEXT,                   -- 'up' | 'down' | 'flat'
    created_at         TIMESTAMPTZ DEFAULT now()
);

-- Predicted future revisions (the trading signal driver)
CREATE TABLE IF NOT EXISTS revision_predictions (
    id                  BIGSERIAL PRIMARY KEY,
    location_id         INT NOT NULL REFERENCES locations(id),
    as_of               DATE NOT NULL,
    horizon             TEXT NOT NULL,
    prob_revise_up      DOUBLE PRECISION,
    prob_revise_down    DOUBLE PRECISION,
    expected_revision_mm DOUBLE PRECISION,
    expected_market_impact DOUBLE PRECISION,
    confidence          DOUBLE PRECISION,
    UNIQUE (location_id, as_of, horizon)
);

-- ============================================================================
-- PROBABILITY ENGINE  (Module 8 — Bayesian)
-- ============================================================================
CREATE TABLE IF NOT EXISTS probability_snapshots (
    id                BIGSERIAL PRIMARY KEY,
    location_id       INT NOT NULL REFERENCES locations(id),
    as_of             DATE NOT NULL,
    scope             TEXT NOT NULL,           -- 'seasonal' | '30d' | ...
    p_above_norm      DOUBLE PRECISION,
    p_below_norm      DOUBLE PRECISION,
    p_above_10        DOUBLE PRECISION,
    p_above_20        DOUBLE PRECISION,
    p_below_10        DOUBLE PRECISION,
    p_below_20        DOUBLE PRECISION,
    posterior_params  JSONB,                   -- Bayesian posterior for audit
    UNIQUE (location_id, as_of, scope)
);

-- ============================================================================
-- SCENARIO ANALYSIS  (Module 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS scenario_results (
    id              BIGSERIAL PRIMARY KEY,
    location_id     INT NOT NULL REFERENCES locations(id),
    as_of           DATE NOT NULL,
    scenario_code   TEXT NOT NULL,             -- 'STRONG_ELNINO' | 'POS_IOD' | 'DELAYED_MONSOON' ...
    scenario_label  TEXT,
    projected_season_mm DOUBLE PRECISION,
    deviation_pct   DOUBLE PRECISION,
    probability     DOUBLE PRECISION,          -- likelihood of this scenario
    distribution    JSONB,
    UNIQUE (location_id, as_of, scenario_code)
);

-- ============================================================================
-- TRADING SIGNAL  (Module 9) + DAILY BRIEF (Final output)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    id              BIGSERIAL PRIMARY KEY,
    symbol          TEXT NOT NULL REFERENCES contract_specs(symbol),
    as_of           DATE NOT NULL,
    signal          TEXT NOT NULL,             -- 'STRONG_BUY'|'BUY'|'NEUTRAL'|'SELL'|'STRONG_SELL'
    score           DOUBLE PRECISION,          -- -1..+1 composite
    confidence      DOUBLE PRECISION,
    components      JSONB,                      -- per-factor contribution (explainability)
    UNIQUE (symbol, as_of)
);

CREATE TABLE IF NOT EXISTS daily_brief (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT NOT NULL REFERENCES contract_specs(symbol),
    as_of               DATE NOT NULL,
    rainfall_forecast   JSONB,                 -- horizon -> value
    confidence_score    DOUBLE PRECISION,
    revision_probability DOUBLE PRECISION,
    expected_season_mm  DOUBLE PRECISION,
    fair_value          DOUBLE PRECISION,
    signal              TEXT,
    bullish_factors     JSONB,                 -- top 5
    bearish_factors     JSONB,                 -- top 5
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (symbol, as_of)
);

-- ============================================================================
-- ALTERNATIVE DATA  (Module 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS alt_documents (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT,                        -- 'IMD' | 'news' | 'research'
    title         TEXT,
    url           TEXT,
    published_at  TIMESTAMPTZ,
    raw_text      TEXT,
    summary       TEXT,
    sentiment     DOUBLE PRECISION,            -- -1..+1
    factors       JSONB,                       -- {bullish:[], bearish:[], risks:[]}
    ingested_at   TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- SEED
-- ============================================================================
INSERT INTO locations (code, name, latitude, longitude, imd_station)
VALUES ('MUMBAI', 'Mumbai (Santacruz)', 19.0896, 72.8656, 'Santacruz')
ON CONFLICT (code) DO NOTHING;
