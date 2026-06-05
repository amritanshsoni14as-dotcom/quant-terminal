import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ModuleHeader from "@/components/ModuleHeader";

export const dynamic = "force-static";

function Term({ name, tag, children }: { name: string; tag?: string; children: React.ReactNode }) {
  return (
    <div className="border-l-2 border-terminal-border pl-3 py-0.5">
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-semibold text-terminal-text">{name}</span>
        {tag && <span className="text-[9px] uppercase tracking-wider text-terminal-accent">{tag}</span>}
      </div>
      <p className="text-xs text-terminal-muted leading-relaxed mt-0.5">{children}</p>
    </div>
  );
}

function B({ children }: { children: React.ReactNode }) {
  return <span className="text-terminal-text">{children}</span>;
}
function Up({ children }: { children: React.ReactNode }) {
  return <span className="text-terminal-pos">{children}</span>;
}
function Down({ children }: { children: React.ReactNode }) {
  return <span className="text-terminal-neg">{children}</span>;
}

export default function GuidePage() {
  return (
    <div>
      <ModuleHeader title="Guide & Glossary" subtitle="Plain-English explanations of every term in the terminal" />

      <div className="p-5 space-y-5 max-w-5xl">
        {/* Intro */}
        <Card>
          <CardHeader><CardTitle>What this terminal does (in one minute)</CardTitle></CardHeader>
          <CardContent className="text-sm text-terminal-text leading-relaxed space-y-2">
            <p>
              It forecasts how much <B>rain Mumbai will get this monsoon</B> and turns that into a
              <B> trading view</B> on the NCDEX <B>RAINMUMBAI</B> rainfall contract (a financial contract that pays
              out based on seasonal rainfall). Every day it produces: an expected seasonal rainfall number, the
              probability of above/below-normal rain, a fair value for the contract, and a single
              signal — <Up>Buy</Up> (expect more rain) to <Down>Sell</Down> (expect less).
            </p>
            <p className="text-terminal-muted text-xs">
              &ldquo;Bullish&rdquo; here means <Up>more rainfall expected</Up>; &ldquo;bearish&rdquo; means <Down>less</Down>.
              Everything is for one point: <B>Santacruz, Mumbai</B> (19.09°N, 72.87°E).
            </p>
          </CardContent>
        </Card>

        {/* Climate drivers */}
        <Card>
          <CardHeader><CardTitle>Climate drivers — the big ocean/atmosphere signals</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Term name="ENSO" tag="El Niño / La Niña">
              The single biggest influence on the Indian monsoon. It describes whether the tropical Pacific Ocean is
              unusually warm or cool. <Down>El Niño</Down> (warm Pacific) usually means a <Down>weaker, drier</Down>
              {" "}monsoon for India; <Up>La Niña</Up> (cool Pacific) usually means a <Up>stronger, wetter</Up> one.
            </Term>
            <Term name="ONI" tag="the ENSO number">
              <B>Oceanic Niño Index</B> — the actual number we track for ENSO. It&rsquo;s the temperature anomaly (°C
              above/below average) of a patch of the Pacific. Rule of thumb: <Down>ONI ≥ +0.5 = El Niño</Down>,
              {" "}<Up>ONI ≤ −0.5 = La Niña</Up>, in between = Neutral. So a positive ONI leans bearish for rain.
            </Term>
            <Term name="IOD / DMI" tag="Indian Ocean">
              <B>Indian Ocean Dipole</B>, measured by the <B>Dipole Mode Index (DMI)</B>. It&rsquo;s the temperature
              difference between the western and eastern Indian Ocean. A <Up>Positive IOD</Up> (warm west) tends to
              {" "}<Up>boost</Up> monsoon rainfall; a <Down>Negative IOD</Down> tends to <Down>dampen</Down> it.
            </Term>
            <Term name="MJO" tag="the 30–60 day pulse">
              <B>Madden–Julian Oscillation</B> — a wave of cloud and rain that travels east around the tropics every
              30–60 days. It has 8 &ldquo;<B>phases</B>&rdquo; (positions). When the active wet phase sits over the
              Indian Ocean (roughly phases 1–4), it <Up>enhances</Up> rain over India; other phases <Down>suppress</Down> it.
              The <B>amplitude</B> is how strong the pulse is (above ~1 = significant).
            </Term>
            <Term name="SST anomaly" tag="sea temperature">
              <B>Sea-Surface-Temperature anomaly</B> — how much warmer/cooler the ocean is than normal. ONI and IOD are
              both SST-based indices. Warm seas feed more moisture into the monsoon.
            </Term>
            <Term name="Monsoon progress">
              How far through the June–September monsoon season we are (0% on June 1, 100% on Sept 30). Early in the
              season the forecast is very uncertain; it sharpens as real rain accumulates.
            </Term>
          </CardContent>
        </Card>

        {/* Signal & probability */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Card>
            <CardHeader><CardTitle>The Trading Signal</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Term name="Signal">
                The headline call, from <Up>Strong Buy → Buy → Neutral → Sell → </Up><Down>Strong Sell</Down>. Buy =
                the model expects above-normal rain (good for a rainfall contract); Sell = below-normal.
              </Term>
              <Term name="Score">
                A number from <Down>−1</Down> to <Up>+1</Up> behind the signal. Closer to +1 = more bullish, −1 = more
                bearish, near 0 = neutral.
              </Term>
              <Term name="Confidence">
                How sure the model is (0–100%), based on how much the individual factors agree and how strong the score is.
              </Term>
              <Term name="Components / Factors">
                The signal is a weighted blend of inputs (probability, ENSO, IOD, MJO, forecast revision, momentum).
                Each one&rsquo;s <B>contribution</B> shows how much it pushed the signal up or down — that&rsquo;s the
                &ldquo;explainable&rdquo; part.
              </Term>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Probability terms</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Term name="Normal / Climatology">
                The long-run average — here, the typical Jun–Sep rainfall (~1,990 mm for Mumbai). Everything is judged
                relative to &ldquo;normal&rdquo;.
              </Term>
              <Term name="Above / Below Normal">
                Probability that this season ends up wetter (above) or drier (below) than that historical average.
              </Term>
              <Term name="Deviation / Anomaly">
                How far current rainfall is from normal, in %. <Up>+20%</Up> = a fifth more rain than usual; <Down>−20%</Down> = a fifth less.
              </Term>
              <Term name="Posterior / Expected (E[season])">
                The model&rsquo;s best single estimate of total seasonal rainfall, after combining history with what&rsquo;s
                fallen so far. &ldquo;Posterior σ&rdquo; is its uncertainty (bigger σ = less certain).
              </Term>
              <Term name="P10 / P90 (percentiles)">
                A range: there&rsquo;s a 10% chance rainfall is below P10 and 10% chance above P90 — so the &ldquo;likely
                band&rdquo; sits between them.
              </Term>
            </CardContent>
          </Card>
        </div>

        {/* Derivative + revision */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Card>
            <CardHeader><CardTitle>The contract (Derivative Monitor)</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Term name="Fair Value">
                What the model thinks the contract is worth, based on expected rainfall. Compare it to the market price
                to spot mispricing.
              </Term>
              <Term name="Market Price vs Mispricing">
                Mispricing = <B>fair value − market price</B>. Positive = the model thinks it&rsquo;s
                {" "}<Up>underpriced</Up> (cheap), negative = <Down>overpriced</Down>. (Needs you to load NCDEX prices.)
              </Term>
              <Term name="Expected Settle">
                The rainfall total the contract is expected to settle against at season end.
              </Term>
              <Term name="Payoff / Strike / Tick / Accrual">
                <B>Payoff</B> = how the contract converts rainfall into money. <B>Strike</B> = the reference level.
                {" "}<B>Tick</B> = value per mm of rain. <B>Accrual window</B> = the dates rainfall is counted (Jun 1–Sep 30).
              </Term>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Forecast Revision Engine (the key idea)</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-xs text-terminal-muted leading-relaxed">
              <p>
                Rainfall contracts don&rsquo;t reprice on <B>today&rsquo;s</B> rain — they reprice on how the
                {" "}<B>forecast for the whole season changes</B>. So the most valuable thing to predict is whether the
                seasonal forecast will be <Up>revised up</Up> or <Down>revised down</Down> next.
              </p>
              <Term name="P(revise up)">
                The probability the seasonal rainfall forecast gets nudged higher soon. High = lean bullish.
              </Term>
              <Term name="Expected revision / Market impact">
                How big the next revision is likely to be (in mm), and what that does to the contract value.
              </Term>
            </CardContent>
          </Card>
        </div>

        {/* ML + satellite */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Card>
            <CardHeader><CardTitle>Machine-Learning Lab</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Term name="Horizons (1d/3d/7d/15d/30d)">
                How far ahead a forecast looks — e.g. &ldquo;7d&rdquo; = total rain over the next 7 days.
              </Term>
              <Term name="RMSE / MAE">
                Error measures (lower = better). <B>MAE</B> = average miss in mm. <B>RMSE</B> = similar but punishes big
                misses more. Used to rank models.
              </Term>
              <Term name="Hit Rate / Directional Accuracy">
                <B>Hit rate</B> = how often it got rain-vs-no-rain right. <B>Directional accuracy</B> = how often it got
                above-vs-below-normal right.
              </Term>
              <Term name="Champion ★">
                The best-scoring model for each horizon — the one actually used for the live forecast.
              </Term>
              <Term name="Time-series CV / LSTM / Transformer">
                <B>CV</B> = a fair test that never peeks at the future. <B>LSTM</B> &amp; <B>Transformer</B> are neural
                networks that learn from sequences of past days.
              </Term>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Satellite scores &amp; Research Lab</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Term name="Cloud Intensity / Rain Probability / Storm Risk">
                0–100 scores for the next 24h: how cloudy, how likely it is to rain, and how stormy (heavy rain + wind +
                low pressure) it&rsquo;s shaping up to be.
              </Term>
              <Term name="Correlation">
                How strongly two things move together, from <Down>−1</Down> (opposite) to <Up>+1</Up> (together). E.g.
                rain vs pressure is ~−0.5 (low pressure → more rain).
              </Term>
              <Term name="Lead / Lag">
                Whether a driver tends to move <B>before</B> rainfall (a lead — useful for prediction) or after.
              </Term>
              <Term name="Seasonality / Drought / Flood">
                The typical month-by-month rainfall pattern, plus the historically driest (drought) and wettest (flood) seasons.
              </Term>
            </CardContent>
          </Card>
        </div>

        <p className="text-[11px] text-terminal-muted">
          Tip: the green <span className="text-terminal-pos">LIVE</span> bar at the top of each page shows the data date.
          Everything updates automatically — hourly for weather, daily for models &amp; news.
        </p>
      </div>
    </div>
  );
}
