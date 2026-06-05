# Commodity Config Spec — the "no hardcoding" core

Each commodity is one JSON file in `backend/app/configs/<symbol>.json`, validated against
`_schema.json` at load. The engine renders sections, ingests data, computes scores, forecasts,
and runs the digital twin **entirely from this file**. To add a commodity you write a config and
(only if it references a new source) one connector.

## Top-level fields

| Field | Meaning |
|---|---|
| `symbol`, `name`, `category` | identity; `category` ∈ agriculture · metal · energy |
| `unit`, `currency` | display unit & quote currency |
| `contract` | exchange, ticker(s), lot, tick, futures root for the curve |
| `regions.producing` / `consuming` | weighted list `{name, share, lat, lon}` — drives weather & trade-flow per commodity |
| `seasonality` | sowing/harvest months (ag) or maintenance/withdrawal seasons (energy) |
| `indicators[]` | the data that matters for THIS commodity (see below) |
| `category_weights` | how the 6 categories roll into the composite (must sum ≈ 1) |
| `forecast` | horizons + model list for the ensemble |
| `twin.elasticities` | % price impact per 1% change of a driver (Section 15) |
| `alerts[]` | early-warning rules over indicators |
| `ui_sections[]` | which of the 18 sections to show (e.g. metals omit `weather`/sowing) |

## The Indicator object (repeated in `indicators[]`)

```jsonc
{
  "key": "us_ending_stocks",      // unique within the commodity
  "label": "US Ending Stocks",
  "category": "inventory",         // supply|demand|inventory|weather|macro|positioning|price
  "source": { "usda": { "commodity": "COTTON", "statisticcat": "STOCKS, ENDING" } },
  "transform": "yoy",              // raw|yoy|zscore|percentile|rolling_mean|anomaly_vs_normal
  "direction": -1,                 // +1 high→bullish price, -1 high→bearish
  "weight": 0.4,                   // share within its category
  "geography": "producing",        // optional: aggregate weather over producing regions
  "frequency": "monthly"           // ingest cadence
}
```

`direction` encodes the economics (high inventory → bearish ⇒ `-1`; tight rainfall vs normal →
bullish ⇒ depends on transform). The scoring engine never hardcodes these — it reads them.

## How scores are computed (generic, identical for every commodity)

```
sub_score(indicator)   = direction × normalize(transform(value))        # ~ [-1, +1]
category_score(cat)    = Σ_i ( weight_i × sub_score_i ) / Σ weight_i     # over indicators in cat
composite_bullish      = Σ_cat ( category_weights[cat] × category_score[cat] )   # [-1,+1]
HealthScore (0-100)    = round( 50 × (composite_bullish + 1) )
```
Category scores ARE the Section-17 scorecard (Supply/Demand/Weather/Inventory/Macro/Positioning).
The composite drives Section-1 "Composite Bullish Score" and Section-18 ranking.

## Example (embedded) — Cotton (agriculture)

```jsonc
{
  "symbol": "COTTON", "name": "Cotton", "category": "agriculture",
  "unit": "USc/lb", "currency": "USD",
  "contract": { "exchange": "ICE", "ticker": "CT=F", "futures_root": "CT" },
  "regions": {
    "producing": [
      { "name": "India",  "share": 0.24, "lat": 21.1, "lon": 78.0 },
      { "name": "China",  "share": 0.23, "lat": 37.0, "lon": 95.0 },
      { "name": "USA",    "share": 0.14, "lat": 33.5, "lon": -90.0 },
      { "name": "Brazil", "share": 0.12, "lat": -12.6, "lon": -55.0 }
    ],
    "consuming": [ { "name": "China", "share": 0.35 }, { "name": "India", "share": 0.22 } ]
  },
  "seasonality": { "sowing_months": [5,6,7], "harvest_months": [10,11,12] },
  "indicators": [
    { "key": "price", "category": "price", "source": { "yahoo": { "ticker": "CT=F" } }, "transform": "raw" },
    { "key": "us_ending_stocks", "label": "US Ending Stocks", "category": "inventory",
      "source": { "usda": { "commodity": "COTTON", "statisticcat": "STOCKS, ENDING" } },
      "transform": "yoy", "direction": -1, "weight": 0.5, "frequency": "monthly" },
    { "key": "stocks_to_use", "label": "Stocks-to-Use", "category": "inventory",
      "source": { "usda": { "derived": "stocks_to_use" } }, "transform": "percentile",
      "direction": -1, "weight": 0.5, "frequency": "monthly" },
    { "key": "us_acreage", "label": "Planted Acreage", "category": "supply",
      "source": { "usda": { "commodity": "COTTON", "statisticcat": "AREA PLANTED" } },
      "transform": "yoy", "direction": -1, "weight": 0.6, "frequency": "seasonal" },
    { "key": "crop_progress", "label": "Crop Condition (Good/Excellent %)", "category": "supply",
      "source": { "usda": { "commodity": "COTTON", "statisticcat": "CONDITION" } },
      "transform": "anomaly_vs_normal", "direction": -1, "weight": 0.4, "frequency": "weekly" },
    { "key": "rainfall_anom", "label": "Rainfall anomaly (producing regions)", "category": "weather",
      "source": { "weather": { "var": "precip_anom" } }, "geography": "producing",
      "transform": "anomaly_vs_normal", "direction": 1, "weight": 0.5, "frequency": "daily" },
    { "key": "soil_moisture", "label": "Soil moisture", "category": "weather",
      "source": { "weather": { "var": "soil_moisture" } }, "geography": "producing",
      "transform": "percentile", "direction": -1, "weight": 0.3, "frequency": "daily" },
    { "key": "enso_oni", "label": "ENSO (ONI)", "category": "weather",
      "source": { "noaa": { "index": "ONI" } }, "transform": "raw", "direction": 1, "weight": 0.2 },
    { "key": "china_imports", "label": "China imports", "category": "demand",
      "source": { "comtrade": { "reporter": "China", "hs": "5201" } },
      "transform": "yoy", "direction": 1, "weight": 0.6, "frequency": "monthly" },
    { "key": "global_pmi", "label": "Global Mfg PMI", "category": "demand",
      "source": { "fred": { "series": "..." } }, "transform": "zscore", "direction": 1, "weight": 0.4 },
    { "key": "usd_index", "label": "US Dollar Index", "category": "macro",
      "source": { "fred": { "series": "DTWEXBGS" } }, "transform": "zscore", "direction": -1, "weight": 1.0 },
    { "key": "cot_net_spec", "label": "COT net speculative", "category": "positioning",
      "source": { "cftc": { "market": "COTTON" } }, "transform": "percentile",
      "direction": 1, "weight": 1.0, "frequency": "weekly" }
  ],
  "category_weights": { "supply": 0.22, "demand": 0.18, "inventory": 0.22, "weather": 0.20, "macro": 0.10, "positioning": 0.08 },
  "forecast": { "horizons": ["5d","21d","63d"], "models": ["xgboost","lightgbm","prophet","ensemble"] },
  "twin": { "elasticities": { "production": -0.7, "exports": 0.4, "inventory": -0.6, "rainfall": -0.25 } },
  "alerts": [
    { "indicator": "rainfall_anom", "rule": "abs_z>2", "severity": "high" },
    { "indicator": "stocks_to_use", "rule": "<0.5", "severity": "high" },
    { "indicator": "cot_net_spec", "rule": "percentile>0.9", "severity": "medium" }
  ],
  "ui_sections": ["overview","supply","demand","inventory","weather","macro","tradeflow",
                  "futures","positioning","news","forecast","seasonality","correlations",
                  "alerts","twin","copilot","scorecard"]
}
```

## Category differences by commodity type (why config beats code)

| | Agriculture (Cotton) | Metal (Copper) | Energy (Crude) |
|---|---|---|---|
| Supply indicators | acreage, crop condition, yield | mine production, smelter output, ore grade | rig count, production, OPEC quota |
| Inventory | USDA ending stocks, stocks-to-use | LME/SHFE/COMEX warehouse stocks | EIA crude stocks, Cushing, SPR |
| Weather | **heavy** (rainfall, soil, ENSO, frost) | minimal (hydro for smelters) | hurricanes (Gulf), heating/cooling degree days |
| Demand | mill use, China imports | China PMI, construction, EV/grid | refinery runs, miles driven, GDP |
| `weather` section shown? | yes | usually off | partial (energy weather) |

Same engine. Different JSON. That is the whole design.

Standalone example files: [config/cotton.json](config/cotton.json) · [config/crude.json](config/crude.json) · [config/copper.json](config/copper.json).
