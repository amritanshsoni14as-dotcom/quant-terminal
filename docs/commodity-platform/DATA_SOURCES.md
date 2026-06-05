# Data Source Mapping

Access tags: ✅ free/no-key · 🔑 free w/ registration · 💵 paid · ✍️ CSV/manual · ♻️ already built.
Every indicator's `source` in the config points at one of these connectors. Start free, upgrade
later by editing config — no code change.

## Prices, futures, volatility
| Need | Source | Access |
|---|---|---|
| Daily OHLCV (gold/silver/copper/crude/natgas + ag futures CT,ZS,ZW,ZC,SB,KC,CC…) | **Yahoo Finance v8 chart** | ✅ ♻️ |
| Full futures curve (all expiries), OI, volume | Barchart / CME / broker (e.g. Samco) | 💵/🔑 (Yahoo gives front month free) |
| Intraday / live | broker API (Samco/Zerodha), MCX | 🔑 |

## Supply
| Commodity type | Indicator | Source | Access |
|---|---|---|---|
| Agriculture | acreage, crop progress/condition, yield, production | **USDA NASS QuickStats** + **USDA PSD / WASDE** | 🔑 (free key) |
| Agriculture | global S&D balances | USDA FAS PSD Online | ✅ |
| Energy | US production, rig-adjacent | **EIA API** | 🔑 (free key) |
| Energy | rig count | Baker Hughes (weekly CSV) | ✅/✍️ |
| Energy | OPEC quotas/output | OPEC MOMR / news | ✍️ |
| Metals | mine production | **USGS MCS**, ICSG/WBMS | ✅/💵 |
| Metals | smelter TC/RC, ore grades | Fastmarkets/CRU | 💵/✍️ |

## Demand
| Indicator | Source | Access |
|---|---|---|
| Manufacturing PMI (global/China) | FRED / S&P Global | 🔑/💵 |
| Industrial production, GDP | **FRED** | 🔑 |
| Imports/exports by country | **UN Comtrade** | ✅ (rate-limited) |
| Refinery runs / products supplied | **EIA** | 🔑 |
| Sector demand (EV, construction, mill use) | industry bodies / news | ✍️ |

## Inventory
| Commodity | Source | Access |
|---|---|---|
| Crude/products (US) | **EIA Weekly Petroleum Status** | 🔑 |
| Natural gas storage | **EIA** | 🔑 |
| Grains/cotton ending stocks, stocks-to-use | **USDA WASDE/PSD** | 🔑/✅ |
| Base-metal warehouse stocks | LME (daily, 💵 for full), SHFE, COMEX | 💵/✍️ |

## Weather & climate  ♻️ (all reused from the existing terminal)
| Indicator | Source | Access |
|---|---|---|
| Rainfall/temp/wind/pressure (any lat/lon) | **Open-Meteo**, **NASA POWER** | ✅ ♻️ |
| Soil moisture | Open-Meteo / NASA SMAP | ✅/🔑 |
| ENSO/ONI | **NOAA CPC** | ✅ ♻️ |
| IOD (DMI), MJO (RMM) | **NOAA PSL / BoM** | ✅ ♻️ |
| Drought index | NOAA / SPI computed | ✅ |
| Cyclones | NOAA NHC / IMD | ✅/✍️ |
| Maps | **Mapbox** (base) + NASA GIBS overlays | 🔑/✅ |

## Macro
| Indicator | Source | Access |
|---|---|---|
| US Dollar Index, real yields, CPI, rates, GDP | **FRED** | 🔑 |
| FX, equity indices | Yahoo Finance | ✅ |

## Trade flow & logistics
| Indicator | Source | Access |
|---|---|---|
| Bilateral trade flows | **UN Comtrade** | ✅ |
| Freight (Baltic Dry, BDI) | Yahoo (^BDIY proxy) / providers | ✅/💵 |
| Vessel tracking (AIS), port congestion | MarineTraffic / Kpler / Spire | 💵 |

## Positioning
| Indicator | Source | Access |
|---|---|---|
| COT (managed money, commercials, OI) | **CFTC** (weekly, free) | ✅ |

## News & events
| Need | Source | Access |
|---|---|---|
| Headlines per commodity | **Google News RSS** ♻️, GDELT | ✅ |
| Classification + sentiment | **local LLM (Ollama)** ♻️ or Claude API | ✅/🔑 |

## Practical MVP cut (zero paid feeds)
Yahoo (prices) + EIA (energy) + USDA (ag) + FRED (macro) + CFTC (positioning) + Comtrade (trade) +
Open-Meteo/NOAA (weather, reused) + Google News + Ollama. That alone powers ~14 of the 18 sections.
Paid feeds (LME full, AIS/freight, intraday curve) are config-swappable upgrades.
