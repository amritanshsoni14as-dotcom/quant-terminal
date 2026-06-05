# Data Sources

Honest sourcing strategy. ✅ = free & no key · 🔑 = free but needs registration · 💵 = paid ·
✍️ = manual/CSV. The pipeline degrades gracefully: anything missing simply leaves its columns null.

## Weather (Mumbai: 19.0896 N, 72.8656 E — Santacruz)

| Source | What | Coverage | Access | Module |
|--------|------|----------|--------|--------|
| **Open-Meteo Archive** ✅ | Daily rain, temp, humidity, pressure, wind | 1940→present | `archive-api.open-meteo.com/v1/archive` | 1,5,6 |
| **Open-Meteo Forecast** ✅ | 16-day forecast (rain/temp) | rolling | `api.open-meteo.com/v1/forecast` | 1,7 |
| **NASA POWER** ✅ | Daily reanalysis (precip, T, RH, wind, pressure) | 1981→present | `power.larc.nasa.gov/api/temporal/daily/point` | 1,5,6 |
| **IMD** ✍️ | Official station rainfall / bulletins | long | scrape/manual; no clean API | 1,11 |

> Strategy: use **NASA POWER + Open-Meteo Archive** for the 30y backfill (cross-validate the two),
> **Open-Meteo Forecast** for live forward forecasts. IMD is best-effort enrichment.

## Climate drivers

| Source | Index | Access | Module |
|--------|-------|--------|--------|
| **NOAA CPC** ✅ | ONI (ENSO), Niño 3.4 SST anomaly | CPC text/CSV endpoints | 3,5,6 |
| **NOAA** ✅ | SOI | CSV | 3,5 |
| **BoM (Australia)** ✅ | IOD / DMI | BoM data files | 3,5,6 |
| **BoM / NOAA** ✅ | MJO RMM1, RMM2, phase, amplitude | RMM index files | 3,5,6 |
| **NOAA OISST** ✅ | Arabian Sea / Bay of Bengal SST anomalies | gridded; sample at boxes | 3 |

## Satellite (Module 4 — later phase)

| Source | What | Access |
|--------|------|--------|
| **NASA GIBS / Worldview** ✅ | Cloud, precip imagery tiles | WMTS tiles |
| **NOAA** ✅ | GOES/POES products | public |
| **IMD INSAT** ✍️ | Indian satellite imagery | web (no API) |
| **ECMWF** 💵 | High-res NWP / ERA5 (ERA5 itself is free via CDS 🔑) | Copernicus CDS |

## Derivative contract (Module 2)

| Source | What | Access |
|--------|------|--------|
| **NCDEX** ✍️/🔑 | RAINMUMBAI prices, settlement, OI | No clean public history API — ingest via **CSV/manual** (`ingest/ncdex.py`). Confirm the live contract spec (accrual window, index definition, payoff) and put it in `contract_specs.payoff_params`. |

> **This is the main external dependency.** The system computes a *model* fair value regardless;
> market price + mispricing require you to supply contract data. Provide whatever you have
> (even a few historical settlements) and the fair-value module calibrates against it.

## AI / Alt-data (Modules 11, 12)

| Source | Use | Access |
|--------|-----|--------|
| **Anthropic Claude API** 🔑 | Copilot (M12) + document summarization (M11) | `ANTHROPIC_API_KEY` |
| News/RSS, IMD bulletins, research PDFs | bullish/bearish factor extraction | scrape/RSS |

## Rate limits & etiquette
- Cache raw responses; upsert by natural key (see schema `UNIQUE` constraints) so re-runs are idempotent.
- Backfill once, then daily incremental pulls only.
- Respect each API's TOS and rate limits; add backoff in `ingest/base.py`.
