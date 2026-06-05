# API Design

REST, read-mostly. Base: `/api/v1`. Everything is parameterized by `{symbol}` so one set of
endpoints serves all commodities. Heavy compute is precomputed by workers; these endpoints read.

## Registry & config
| Method | Path | Returns |
|---|---|---|
| GET | `/commodities` | list of configured commodities (symbol, name, category, health, available sections) |
| GET | `/commodities/{symbol}/config` | the (sanitized) config — UI uses it to render only enabled sections |

## Per-section (maps 1:1 to the 18 dashboard sections)
| Section | Endpoint |
|---|---|
| 1 Overview | `GET /commodities/{symbol}/overview` → spot, %changes, vol, percentile, 52w, scores (trend/fundamental/risk/composite) |
| 2 Supply | `GET /{symbol}/supply` → indicators + Supply Tightness Index |
| 3 Demand | `GET /{symbol}/demand` → indicators + Demand Strength Index |
| 4 Inventory | `GET /{symbol}/inventory` → stocks, days-of-consumption, stocks-to-use, Inventory Stress |
| 5 Weather | `GET /{symbol}/weather` → per-region series + Weather Risk Index + map GeoJSON |
| 6 Macro | `GET /{symbol}/macro` → USD/rates/inflation + correlations |
| 7 Trade flow | `GET /{symbol}/tradeflow` → flows + GeoJSON arcs (+ freight if available) |
| 8 Futures | `GET /{symbol}/futures` → curve, contango/backwardation, spreads, roll yield |
| 9 Positioning | `GET /{symbol}/positioning` → COT series + extremes flags |
| 10 News | `GET /{symbol}/news` → classified items + sentiment timeline |
| 11 Forecast | `GET /{symbol}/forecast` → per-horizon point + bull/bear/neutral probs + drivers |
| 12 Seasonality | `GET /{symbol}/seasonality` → monthly/weekly seasonality, best/worst windows |
| 13 Correlation | `GET /{symbol}/correlations` → matrix + discovered lead indicators |
| 14 Alerts | `GET /{symbol}/alerts` (+ `GET /alerts` global feed) |
| 15 Digital twin | `POST /{symbol}/twin` body `{production, exports, inventory, rainfall,…}` → price impact |
| 16 Copilot | `POST /{symbol}/copilot` body `{question}` → grounded answer; `GET /{symbol}/copilot/suggested` |
| 17 Scorecard | `GET /{symbol}/scorecard` → 6 category scores + Health 0-100 |
| 18 Portfolio | `GET /portfolio` → all commodities ranked (bullish/bearish/risk/opportunity) |

## Admin / ops
| Method | Path | Purpose |
|---|---|---|
| POST | `/admin/commodities/reload` | re-read config dir → upsert registry/indicators |
| POST | `/admin/{symbol}/refresh` | force ingest+score+forecast for one commodity |
| GET | `/health`, `/meta` | liveness + data coverage |

## Conventions
- All responses include `as_of` + `available` (graceful nulls for missing feeds).
- Interactive POSTs (twin, copilot) are proxied by Next route handlers so remote users work
  without exposing the backend (same pattern as the existing terminal).
- OpenAPI auto-served at `/docs`; the frontend's typed client mirrors it.
