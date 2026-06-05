# UI Wireframes (text)

Shell: left sidebar (commodity dropdown + section nav, rendered from config `ui_sections`),
persistent top **Health bar**, dark/light toggle. Recharts for charts, Mapbox for maps.

## Global shell
```
┌──────────────┬───────────────────────────────────────────────────────────────┐
│ ◆ CIP        │  [Cotton ▼]   Health 62/100 ●  Bull 41% Neut 34% Bear 25%  ☀/☾ │
│ ───────────  ├───────────────────────────────────────────────────────────────┤
│ Overview     │                      <active section>                          │
│ Supply       │                                                                │
│ Demand       │                                                                │
│ Inventory    │                                                                │
│ Weather      │   (only sections in this commodity's config appear)            │
│ Macro        │                                                                │
│ Trade Flow   │                                                                │
│ Futures      │                                                                │
│ Positioning  │                                                                │
│ News         │                                                                │
│ Forecast     │                                                                │
│ Seasonality  │                                                                │
│ Correlations │                                                                │
│ Alerts (3)   │                                                                │
│ Digital Twin │                                                                │
│ Copilot      │                                                                │
│ Scorecard    │                                                                │
│ ───────────  │                                                                │
│ Portfolio    │                                                                │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

## 1 Overview
```
[ Spot 72.4 ▲0.8% ] [ 1W ] [ 1M ] [ YTD ] [ 1Y ]    Hist pct: 38th   52w 58–94
┌ Price + futures curve overlay ───────────┐ ┌ Score gauges ───────────────┐
│  candles + curve                          │ │ Trend 64  Fundamental 58    │
│                                           │ │ Risk 41   Seasonal 72       │
└───────────────────────────────────────────┘ │ Composite Bullish ▓▓▓▓ 62  │
[ Volatility ] [ Open Interest ] [ Volume ]    └─────────────────────────────┘
```

## 2/3/4 Supply / Demand / Inventory  (same template per category)
```
Big index gauge (Supply Tightness / Demand Strength / Inventory Stress)
Grid of indicator cards: value · YoY · z/percentile · ▲/▼ contribution to score
Trend chart for the key driver (e.g. ending stocks, stocks-to-use, days-of-consumption)
```

## 5 Weather & Climate
```
┌ Mapbox: producing regions, choropleth rainfall/soil-moisture anomaly ┐
│  ● India ● China ● US ● Brazil  (sized by share)                     │
└──────────────────────────────────────────────────────────────────────┘
Weather Risk Index gauge · ENSO/IOD/MJO strip · per-region rainfall vs normal · drought/frost flags
```

## 6 Macro
USD index / yields / inflation mini-charts + correlation bars (commodity vs each macro factor).

## 7 Trade Flow
```
Mapbox arcs: exporter → importer (width = volume). Freight rates & port congestion side panel.
Disruption flags.
```

## 8 Futures
Curve chart (front→back), contango/backwardation badge, calendar-spread table, roll-yield gauge.

## 9 Positioning
COT stacked area (specs vs commercials), net-spec percentile gauge, "extreme" alert banner.

## 10 News
Sentiment timeline + feed cards tagged Supply/Demand/Weather/Geopolitical/Policy/Currency/Logistics.

## 11 Forecast
```
For each horizon (5d / 21d / 63d):  point return + Bull/Neut/Bear probability bars
Fan chart (p10–p90). Top drivers list (explainable).
```

## 12 Seasonality
Monthly seasonality bars (avg return + hit-rate), harvest/demand-cycle ribbon, best-window callouts.

## 13 Correlations
Heatmap (commodity vs weather/FX/energy/freight/inventory) + ranked discovered lead indicators (with lag).

## 14 Alerts
Severity-sorted list; each: indicator, rule breached, value, time, ack button.

## 15 Digital Twin
```
Sliders: Production ±%  Exports ±%  Inventory ±%  Rainfall ±%
→  Projected price  ▲/▼ X%   waterfall of each driver's contribution
```

## 16 Copilot
Chat panel; suggested questions; answers cite the live scorecard/forecast/indicators.

## 17 Scorecard
Six category gauges (Supply/Demand/Weather/Inventory/Macro/Positioning) → big Health 0-100 dial + verdict.

## 18 Portfolio
Sortable table of all commodities: Health, Bull%, Risk, Trend, 1M, top driver. Tabs: Most Bullish / Bearish / Highest Risk / Best Opportunity.
```
Symbol  Health  Bull%  Risk  Trend  1M    Top driver
Cotton    62     41%   Med    ▲    +3%   Tight stocks-to-use
Copper    55     38%   High   ▲   +5%   China PMI rebound
Crude     47     33%   High   ▼   -4%   Builds in EIA stocks
```
