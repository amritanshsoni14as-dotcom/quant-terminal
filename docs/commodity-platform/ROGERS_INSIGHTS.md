# Making it Smarter — Jim Rogers' "Hot Commodities" → platform features

Distilled from Rogers, *Hot Commodities* (Wiley). Each principle is mapped to a **concrete,
buildable** feature: a config field, a score, an alert, or copilot knowledge. The big idea Rogers
adds that price/technical dashboards miss: **commodities move in long SUPPLY-LED cycles**, and the
*leading* signals are inventories, productive capacity, and price relative to cost & inflation —
not momentum.

---

## 1. The supply cycle is the master signal
> "Time turns even excess inventories into empty warehouses." Low prices → no new mines/wells/
> acreage → depletion → shortage → price spike → new supply → glut → low prices.
> "The cure for low prices is low prices; the cure for high prices is high prices."

**Feature — `Rogers Secular Score` (a second gauge next to the tactical Health Score):**
A slow-moving structural bull/bear read, separate from the short-term signal. Composed of:
| Component | Bullish when | Data |
|---|---|---|
| Inventory **trend** (multi-year slope, not just level) | drawing down | inventory indicators |
| **Capacity / capex** pipeline | few new projects, capex falling, high utilization | new `supply_capacity` indicators |
| **Real price percentile** (price ÷ CPI over 20–30y) | cheap vs history & inflation | price + FRED CPI |
| **Price ÷ cost-of-production** | near/below marginal cost | new `cost_of_production` indicator |
| **Secular demand** (Asia/EM) | structurally rising | demand indicators |
Shown as: *"Secular: early-bull / mid / late / bear"* with the contributing drivers.

## 2. Rogers' explicit checklist → indicator catalog
He literally lists the variables to check. Encode them as standard indicator keys so every config can include the relevant ones:

**Supply:** `production_global`, `reserves`, `mine_count`/`active_capacity`, `capacity_utilization`,
`ore_grade`, `new_supply_pipeline`, `supply_lead_time_months` (how long new supply takes to reach
market — governs how *persistent* a shortage is), `producing_region_risk` (share of output in
unstable countries; strikes/accidents).
**Demand:** `primary_use_demand`, `substitution_risk`, `new_tech_demand`, plus existing PMI/imports.

`supply_lead_time_months` is uniquely Rogersian and powerful: a deficit with a 7-year lead time
(a new mine) is far more bullish than one fixable in a season (acreage). Feed it as a **persistence
multiplier** on the supply score.

## 3. "The bull market is over when…" → Early-Warning rules
> "When you see headlines about new oil reserves… new mines coming on line… stockpiles rising —
> those are fundamental shifts. The bull market will be over."

**Feature — structural bearish alerts** (Section 14), in addition to the tactical ones:
- `inventory_trend` flips from drawdown to **multi-quarter build** → "supply response underway."
- `new_supply_pipeline` jumps / major discovery or mine-opening detected by the **news classifier**
  (new classification tag: `capacity_addition`) → structural bearish flag.
- `price_vs_cost` or `real_price_percentile` extreme high → mean-reversion / demand-destruction risk.

## 4. Substitution & cross-commodity opportunity
> Copper too pricey → plastic pipe → plastic is an oil product → demand shifts to oil. "In that blow
> to copper lies an opportunity."

**Feature — `substitutes` graph in config** (`{"COPPER":["ALUMINUM"], "CRUDE":["NATGAS"],
"SOYBEAN":["CORN"]}`). When a commodity hits an extreme (high real-price percentile + overbought),
the engine raises a **substitution-demand opportunity** flag on its substitute and surfaces it in
**Portfolio mode** ("Best Opportunity") and the Copilot.

## 5. Macro / monetary lens (Rogers is emphatic)
> Commodities are **negatively correlated** with stocks/bonds; they **outpace inflation**; central-
> bank **currency debasement** ⇒ hard assets win.

**Features:**
- `real_price_percentile` (CPI-deflated) — the contrarian "is it historically cheap?" gauge.
- `stocks_corr` / `bonds_corr` (rolling correlation to S&P/treasuries) → a **diversification/regime**
  readout (Rogers' core portfolio argument), shown in Macro + Portfolio.
- Monetary-debasement factor: rising CPI + falling real yields + weak USD → bullish weight
  (already partly in macro; elevate per Rogers).

## 6. Contrarian / "buy what's hated" composite
> Rogers buys what is cheap and out of favor; "investors never chase bears."

**Feature — `Contrarian Setup` flag:** low `real_price_percentile` (cheap vs history) **+** extreme
short speculative positioning (COT percentile low) **+** negative news sentiment → a high-conviction
contrarian-bullish badge. The mirror (expensive + crowded long + euphoric news) = caution.

## 7. Curve structure ↔ supply tightness
Backwardation = market paying up for prompt delivery = **tight supply** (Rogers' depletion thesis in
the curve); contango = ample supply. **Wire futures-curve shape into the Supply-Tightness Index** so
Section 8 (Futures) and Section 2 (Supply) reinforce each other.

## 8. Diversified, consumption-weighted basket (RICI)
Rogers built the **Rogers International Commodities Index** — a broad, consumption-weighted basket,
because diversification + the secular thesis beats single bets.
**Feature — Index/Basket view in Portfolio mode:** a consumption-weighted composite of all configured
commodities + an aggregate "where are we in the secular cycle" read.

## 9. Data sources Rogers names (add to connectors)
USGS (minerals: production, reserves, mine openings/closings), CRB Commodity Yearbook, industry
bodies (American Bureau of Metal Statistics, American Metal Market), exchanges (COMEX/LME), national
statistical sites. → Already aligned with [DATA_SOURCES.md](DATA_SOURCES.md); **add USGS MCS** as a
first-class supply connector (free) and `cost_of_production` via industry/CRU (paid/✍️).

## 10. Copilot "Rogers Lens"
Embed these principles as reasoning the Copilot applies. New canned questions + grounding:
- "Where are we in the secular cycle?" → cites Secular Score components.
- "Is this cheap historically?" → real-price percentile vs CPI.
- "What ends this bull market?" → inventory builds, new capacity, lead-time shrinking, real-price extreme.
- "What's the substitution risk?" → substitutes graph + price extremes.
The Copilot system prompt gains a short "Rogers principles" preamble so answers carry the supply-cycle
intuition, not just current numbers.

---

## Config additions (drop-in; engine reads them)
Add to any `<symbol>.json`:
```jsonc
"secular": {
  "cpi_series": "CPIAUCSL",            // FRED, for real-price percentile
  "cost_of_production": { "source": {"csv": {"feed": "copper_cost_curve"}}, "level": "marginal" },
  "supply_lead_time_months": 84,        // ~7y for a new copper mine
  "capacity": { "source": {"usgs": {"commodity": "copper"}} }
},
"substitutes": ["ALUMINUM"],
"contrarian": true
```
New indicator `category` values supported: `supply_capacity`, `valuation` (real-price/cost),
`regime` (cross-asset correlation). They flow through the **same generic scoring engine** — only the
config changes. The Secular Score is `valuation`+`supply_capacity`+inventory-trend+secular-demand;
the Health Score stays tactical. Two gauges, one engine.

> Net effect: the platform stops only answering "what's the price doing?" and starts answering
> Rogers' real question — *"where are we in the supply cycle, is it cheap, and what would end the
> move?"* — which is exactly the edge the book argues for.
