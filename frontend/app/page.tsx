import { api } from "@/lib/api";
import { fmt } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatCard from "@/components/StatCard";
import DailyBrief from "@/components/DailyBrief";
import { CumulativeChart, DailyRainChart, MonthlyChart, WeeklyChart } from "@/components/charts";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [summary, meta, daily, weekly, monthly, cumulative] = await Promise.all([
    api.summary(),
    api.meta(),
    api.daily(120),
    api.weekly(52),
    api.monthly(48),
    api.cumulative(),
  ]);

  if (!summary) {
    return (
      <div className="p-8 text-terminal-muted">
        <h1 className="text-lg text-terminal-text mb-2">Backend unavailable</h1>
        <p className="text-sm">
          Start the API: <code className="text-terminal-accent">uvicorn app.main:app --reload</code> on
          port 8000, then refresh.
        </p>
      </div>
    );
  }

  const dev = summary.deviation_pct ?? null;
  const regime = dev === null ? "—" : dev >= 10 ? "Above-Normal" : dev <= -10 ? "Below-Normal" : "Near-Normal";

  return (
    <div>
      {/* Top bar */}
      <div className="h-14 px-5 flex items-center justify-between border-b border-terminal-border bg-terminal-panel">
        <div>
          <h1 className="text-base font-semibold text-terminal-text">Weather Command Center</h1>
          <p className="text-[11px] text-terminal-muted">
            {meta?.location?.name ?? "Mumbai"} · {meta?.location?.lat}°N {meta?.location?.lon}°E
          </p>
        </div>
        <div className="text-right text-[11px] text-terminal-muted">
          <div>As of <span className="text-terminal-text">{summary.as_of}</span></div>
          <div>
            {meta?.coverage?.years}y history · {meta?.coverage?.days?.toLocaleString()} days ·{" "}
            {Object.keys(meta?.raw_sources ?? {}).join(", ")}
          </div>
        </div>
      </div>

      <DailyBrief />

      <div className="p-5 space-y-5">
        {/* KPI grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Today" value={fmt(summary.today_rainfall_mm, 1, " mm")} tone="accent" />
          <StatCard label="Weekly (7d)" value={fmt(summary.weekly_rainfall_mm, 1, " mm")} />
          <StatCard label="Monthly (30d)" value={fmt(summary.monthly_rainfall_mm, 1, " mm")} />
          <StatCard label="Seasonal" value={fmt(summary.seasonal_rainfall_mm, 1, " mm")} sub={`since ${summary.season_start}`} />
          <StatCard
            label="Deviation"
            value={dev === null ? "—" : `${dev > 0 ? "+" : ""}${dev.toFixed(1)}%`}
            tone={dev === null ? "default" : dev >= 0 ? "pos" : "neg"}
            sub="vs climatology"
          />
          <StatCard label="Historical Avg" value={fmt(summary.historical_avg_seasonal_mm, 1, " mm")} sub="seasonal-to-date" />
          <StatCard
            label="Monsoon Progress"
            value={summary.monsoon_progress != null ? `${(summary.monsoon_progress * 100).toFixed(0)}%` : "—"}
            sub={regime}
            tone="warn"
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Daily Rainfall (last 120 days)</CardTitle></CardHeader>
            <CardContent>{daily?.series?.length ? <DailyRainChart data={daily.series} /> : <Empty />}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Cumulative Season vs Climatology</CardTitle></CardHeader>
            <CardContent>{cumulative?.series?.length ? <CumulativeChart data={cumulative.series} /> : <Empty />}</CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader><CardTitle>Monthly Rainfall (4y)</CardTitle></CardHeader>
            <CardContent>{monthly?.series?.length ? <MonthlyChart data={monthly.series} /> : <Empty />}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Weekly Rainfall (52w)</CardTitle></CardHeader>
            <CardContent>{weekly?.series?.length ? <WeeklyChart data={weekly.series} /> : <Empty />}</CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Empty() {
  return <div className="h-[280px] flex items-center justify-center text-terminal-muted text-sm">No data</div>;
}
