-- ============================================================================
-- Commodity Intelligence Platform — PostgreSQL schema (commodity-agnostic)
-- Everything is keyed by commodity_id + indicator; nothing is commodity-specific
-- in DDL. The config JSON defines which indicators exist per commodity.
-- (TimescaleDB optional: convert *_observations / prices to hypertables.)
-- ============================================================================

-- Registry (mirrors each config/<symbol>.json at load) -----------------------
CREATE TABLE commodities (
    id          SERIAL PRIMARY KEY,
    symbol      TEXT UNIQUE NOT NULL,          -- COTTON, CRUDE, COPPER
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,                 -- agriculture | metal | energy
    unit        TEXT, currency TEXT,
    config      JSONB NOT NULL,                -- the full validated config
    active      BOOLEAN DEFAULT TRUE,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE regions (
    id           SERIAL PRIMARY KEY,
    commodity_id INT NOT NULL REFERENCES commodities(id),
    role         TEXT NOT NULL,                -- producing | consuming
    name         TEXT NOT NULL,
    share        DOUBLE PRECISION,
    latitude     DOUBLE PRECISION, longitude DOUBLE PRECISION
);

-- Indicator catalog (one row per indicator per commodity, from config) --------
CREATE TABLE indicators (
    id           SERIAL PRIMARY KEY,
    commodity_id INT NOT NULL REFERENCES commodities(id),
    key          TEXT NOT NULL,                -- us_ending_stocks, rainfall_anom…
    label        TEXT,
    category     TEXT NOT NULL,                -- supply|demand|inventory|weather|macro|positioning|price
    source       JSONB NOT NULL,              -- connector + params
    transform    TEXT, direction INT, weight DOUBLE PRECISION,
    geography    TEXT, frequency TEXT,
    UNIQUE (commodity_id, key)
);

-- Raw + normalized indicator time series -------------------------------------
CREATE TABLE indicator_observations (
    id           BIGSERIAL PRIMARY KEY,
    indicator_id INT NOT NULL REFERENCES indicators(id),
    obs_date     DATE NOT NULL,
    value        DOUBLE PRECISION,
    source       TEXT,
    ingested_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (indicator_id, obs_date)
);
CREATE INDEX ix_ind_obs ON indicator_observations(indicator_id, obs_date);

CREATE TABLE indicator_values (         -- transformed + normalized + sub-score
    indicator_id INT NOT NULL REFERENCES indicators(id),
    obs_date     DATE NOT NULL,
    raw          DOUBLE PRECISION,
    normalized   DOUBLE PRECISION,      -- z / percentile etc.
    sub_score    DOUBLE PRECISION,      -- direction × normalized  (~[-1,1])
    PRIMARY KEY (indicator_id, obs_date)
);

-- Prices, futures curve, positioning -----------------------------------------
CREATE TABLE prices (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    obs_date     DATE NOT NULL,
    open DOUBLE PRECISION, high DOUBLE PRECISION, low DOUBLE PRECISION,
    close DOUBLE PRECISION, volume DOUBLE PRECISION, open_interest DOUBLE PRECISION,
    PRIMARY KEY (commodity_id, obs_date)
);

CREATE TABLE futures_curve (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    as_of        DATE NOT NULL,
    contract_month DATE NOT NULL,       -- expiry month
    price        DOUBLE PRECISION,
    open_interest DOUBLE PRECISION,
    PRIMARY KEY (commodity_id, as_of, contract_month)
);

CREATE TABLE positioning_cot (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    report_date  DATE NOT NULL,
    noncomm_long DOUBLE PRECISION, noncomm_short DOUBLE PRECISION,
    comm_long DOUBLE PRECISION, comm_short DOUBLE PRECISION,
    open_interest DOUBLE PRECISION,
    net_spec DOUBLE PRECISION, net_spec_pctile DOUBLE PRECISION,
    PRIMARY KEY (commodity_id, report_date)
);

-- Scores -----------------------------------------------------------------------
CREATE TABLE category_scores (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    as_of        DATE NOT NULL,
    category     TEXT NOT NULL,         -- supply|demand|inventory|weather|macro|positioning
    score        DOUBLE PRECISION,      -- [-1,1]
    contributors JSONB,                 -- per-indicator contribution (explainability)
    PRIMARY KEY (commodity_id, as_of, category)
);

CREATE TABLE health_scores (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    as_of        DATE NOT NULL,
    composite_bullish DOUBLE PRECISION, -- [-1,1]
    health_0_100 DOUBLE PRECISION,
    trend_score DOUBLE PRECISION, risk_score DOUBLE PRECISION,
    seasonal_strength DOUBLE PRECISION,
    breakdown    JSONB,                 -- category scores snapshot
    PRIMARY KEY (commodity_id, as_of)
);

-- Forecasts (probabilistic) ----------------------------------------------------
CREATE TABLE forecasts (
    id           BIGSERIAL PRIMARY KEY,
    commodity_id INT NOT NULL REFERENCES commodities(id),
    as_of        DATE NOT NULL,
    horizon      TEXT NOT NULL,         -- 5d|21d|63d…
    point_return DOUBLE PRECISION,
    p_bull DOUBLE PRECISION, p_bear DOUBLE PRECISION, p_neutral DOUBLE PRECISION,
    model        TEXT, confidence DOUBLE PRECISION,
    drivers      JSONB,
    UNIQUE (commodity_id, as_of, horizon, model)
);

CREATE TABLE model_runs (              -- ML leaderboard per commodity/horizon
    id BIGSERIAL PRIMARY KEY,
    commodity_id INT REFERENCES commodities(id),
    model_name TEXT, horizon TEXT, trained_at TIMESTAMPTZ DEFAULT now(),
    rmse DOUBLE PRECISION, mae DOUBLE PRECISION, directional_acc DOUBLE PRECISION,
    is_champion BOOLEAN DEFAULT FALSE, params JSONB
);

-- Analytics --------------------------------------------------------------------
CREATE TABLE seasonality (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    period_type  TEXT NOT NULL,         -- month | week
    period       INT NOT NULL,
    mean_return  DOUBLE PRECISION, hit_rate DOUBLE PRECISION, n_years INT,
    PRIMARY KEY (commodity_id, period_type, period)
);

CREATE TABLE correlations (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    as_of        DATE NOT NULL,
    var_a TEXT, var_b TEXT, lag_days INT, corr DOUBLE PRECISION,
    is_lead_indicator BOOLEAN
);

CREATE TABLE trade_flows (
    commodity_id INT NOT NULL REFERENCES commodities(id),
    period       TEXT NOT NULL,         -- YYYY-MM
    reporter TEXT, partner TEXT, flow TEXT,   -- import|export
    qty DOUBLE PRECISION, value_usd DOUBLE PRECISION
);

-- News, alerts, twin -----------------------------------------------------------
CREATE TABLE news_items (
    id BIGSERIAL PRIMARY KEY,
    commodity_id INT REFERENCES commodities(id),
    published_at TIMESTAMPTZ, title TEXT, url TEXT,
    classification TEXT,                -- supply|demand|weather|geopolitical|policy|currency|logistics
    sentiment DOUBLE PRECISION, summary TEXT, ingested_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    commodity_id INT REFERENCES commodities(id),
    as_of DATE, indicator_key TEXT, rule TEXT, severity TEXT,
    message TEXT, value DOUBLE PRECISION, status TEXT DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE twin_runs (
    id BIGSERIAL PRIMARY KEY,
    commodity_id INT REFERENCES commodities(id),
    as_of TIMESTAMPTZ DEFAULT now(),
    inputs JSONB,                       -- {production:-5, exports:+3, inventory:-10, rainfall:-20}
    base_price DOUBLE PRECISION, projected_price DOUBLE PRECISION,
    impact_pct DOUBLE PRECISION, breakdown JSONB
);
