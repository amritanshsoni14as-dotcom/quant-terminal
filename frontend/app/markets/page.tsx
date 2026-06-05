import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ModuleHeader from "@/components/ModuleHeader";
import CommoditySwitcher from "@/components/CommoditySwitcher";
import StatCard from "@/components/StatCard";
import { PriceCandles, MacdChart } from "@/components/chartsCommodity";
import IntelScorecard from "@/components/IntelScorecard";
import ForecastPanel from "@/components/ForecastPanel";
import CommodityCopilot from "@/components/CommodityCopilot";

export const dynamic = "force-dynamic";

const CHANGE_LABELS: [string, string][] = [
  ["1d", "1 Day"], ["1w", "1 Week"], ["1m", "1 Month"], ["3m", "3 Month"], ["ytd", "YTD"], ["1y", "1 Year"],
];

function trendTone(t?: string) {
  return t === "Uptrend" ? "text-terminal-pos" : t === "Downtrend" ? "text-terminal-neg" : "text-terminal-text";
}

export default async function MarketsPage({ searchParams }: { searchParams: Promise<{ symbol?: string }> }) {
  const sp = await searchParams;
  const list = await api.commodities();
  const items = list?.commodities ?? [];
  const symbol = (sp.symbol ?? items.find((i) => i.has_data)?.symbol ?? "GOLD").toUpperCase();

  const [s, prices, tech, scorecard, forecast, copilot] = await Promise.all([
    api.commoditySummary(symbol),
    api.commodityPrices(symbol, 400),
    api.commodityTechnicals(symbol),
    api.intelScorecard(symbol),
    api.intelForecast(symbol),
    api.commodityCopilotSuggested(symbol),
  ]);

  const header = (
    <div className="h-14 px-5 flex items-center justify-between border-b border-terminal-border bg-terminal-panel">
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-base font-semibold text-terminal-text">Commodity Command Center</h1>
          <p className="text-[11px] text-terminal-muted">Multi-commodity markets · MCX / COMEX / NYMEX benchmarks</p>
        </div>
        <CommoditySwitcher items={items} current={symbol} />
      </div>
      {s?.available && (
        <div className="text-right">
          <div className="text-xl font-bold tabular-nums text-terminal-text">
            {s.currency === "USD" ? "$" : ""}{fmt(s.price, 2)} <span className="text-xs text-terminal-muted">{s.unit}</span>
          </div>
          <div className={cn("text-xs tabular-nums", (s.change?.["1d"] ?? 0) >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>
            {(s.change?.["1d"] ?? 0) >= 0 ? "▲" : "▼"} {fmt(Math.abs(s.change?.["1d"] ?? 0), 2)}% · as of {s.as_of}
          </div>
        </div>
      )}
    </div>
  );

  if (!s?.available) {
    return (
      <div>
        {header}
        <div className="p-6">
          <Card><CardContent className="py-10 text-center text-terminal-muted text-sm">
            <div className="text-terminal-warn font-semibold mb-1">No price data for {s?.name ?? symbol}.</div>
            {symbol === "ELECTRICITY"
              ? <>Electricity has no free public feed. Plug in IEX/MCX power prices via CSV or the import API and it activates — same seam as the other markets.</>
              : <>Data unavailable right now.</>}
          </CardContent></Card>
        </div>
      </div>
    );
  }

  return (
    <div>
      {header}
      <div className="p-5 space-y-5">
        {/* Performance */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {CHANGE_LABELS.map(([k, label]) => {
            const v = s.change?.[k] ?? null;
            return <StatCard key={k} label={label} value={v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`}
              tone={v == null ? "default" : v >= 0 ? "pos" : "neg"} />;
          })}
        </div>

        {/* Intelligence scorecard (config-driven Health Score) */}
        {scorecard?.available && <IntelScorecard data={scorecard} />}

        {/* AI forecast (bull/bear/neutral per horizon) */}
        {forecast?.available && <ForecastPanel data={forecast} unit={s.unit} />}

        {/* Price chart */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{s.name} — price & moving averages</CardTitle>
            <span className={cn("text-xs font-semibold uppercase", trendTone(s.trend))}>{s.trend}</span>
          </CardHeader>
          <CardContent>{prices?.series?.length ? <PriceCandles data={prices.series} /> : null}</CardContent>
        </Card>

        {/* Key stats + MACD */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card>
            <CardHeader><CardTitle>Key statistics</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1.5">
              <Row k="52-week high" v={`${fmt(s.high_52w, 2)}`} />
              <Row k="52-week low" v={`${fmt(s.low_52w, 2)}`} />
              <Row k="Annualised volatility" v={s.volatility_annual_pct != null ? `${s.volatility_annual_pct}%` : "—"} />
              <Row k="ATR (14)" v={fmt(s.atr_14, 2)} />
              <Row k="RSI (14)" v={s.rsi_14 != null ? s.rsi_14.toFixed(1) : "—"} tone={s.rsi_14 == null ? "" : s.rsi_14 >= 70 ? "text-terminal-neg" : s.rsi_14 <= 30 ? "text-terminal-pos" : ""} />
              <Row k="SMA 50" v={fmt(s.sma_50, 2)} />
              <Row k="SMA 200" v={fmt(s.sma_200, 2)} />
              <Row k="History" v={`${s.n_days?.toLocaleString()} days`} />
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>MACD (12,26,9)</CardTitle>
              {tech?.bollinger && (
                <span className="text-[11px] text-terminal-muted">
                  Bollinger: {fmt(tech.bollinger.lower, 0)} / <span className="text-terminal-text">{fmt(tech.bollinger.mid, 0)}</span> / {fmt(tech.bollinger.upper, 0)}
                </span>
              )}
            </CardHeader>
            <CardContent>{tech?.macd_series?.length ? <MacdChart data={tech.macd_series} /> : null}</CardContent>
          </Card>
        </div>

        {/* AI Copilot — grounded on this commodity's scorecard + forecast */}
        <Card>
          <CardHeader><CardTitle>AI Copilot — ask why {s.name} is moving</CardTitle></CardHeader>
          <CardContent>
            <CommodityCopilot symbol={symbol} suggested={copilot?.suggested ?? []} />
          </CardContent>
        </Card>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Prices are daily settlement from Yahoo Finance ({s.exchange} benchmark, {s.currency}). MCX/Indian
          contracts track these closely; swap in your broker/MCX feed later via the same ingest seam.
          Phase C1 covers the command center &amp; core technicals — ML forecasting, probability, a trading
          signal, cross-commodity research, news &amp; copilot for commodities come next.
        </p>
      </div>
    </div>
  );
}

function Row({ k, v, tone }: { k: string; v: string; tone?: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-terminal-muted">{k}</span>
      <span className={cn("tabular-nums text-right", tone || "text-terminal-text")}>{v}</span>
    </div>
  );
}
