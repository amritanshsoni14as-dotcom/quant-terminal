import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import { CorrHeatmap, LeadLagChart, SeasonalityChart } from "@/components/charts5";

export const revalidate = 60;

export default async function ResearchPage() {
  const r = await api.research();
  if (!r?.available) {
    return (
      <div>
        <ModuleHeader title="Historical Research Lab" subtitle="Module 5" />
        <div className="p-8 text-terminal-muted text-sm">No data.</div>
      </div>
    );
  }

  return (
    <div>
      <ModuleHeader title="Historical Research Lab" subtitle={`Module 5 · ${r.coverage?.n_days.toLocaleString()} days · ${r.coverage?.n_seasons} seasons · ${r.coverage?.start}–${r.coverage?.end}`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader><CardTitle>Correlation matrix (daily variables)</CardTitle></CardHeader>
            <CardContent>{r.correlation && <CorrHeatmap data={r.correlation} />}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Lead / lag — drivers vs monthly rainfall</CardTitle></CardHeader>
            <CardContent>{r.leadlag && <LeadLagChart data={r.leadlag} />}</CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle>Seasonality — mean monthly rainfall</CardTitle></CardHeader>
          <CardContent>{r.seasonality && <SeasonalityChart data={r.seasonality} />}</CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card>
            <CardHeader><CardTitle>Flood years — wettest seasons</CardTitle></CardHeader>
            <CardContent>
              <SeasonTable rows={r.extremes?.wettest_seasons ?? []} tone="pos" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Drought years — driest seasons</CardTitle></CardHeader>
            <CardContent>
              <SeasonTable rows={r.extremes?.driest_seasons ?? []} tone="neg" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Extreme rainfall days</CardTitle></CardHeader>
            <CardContent>
              <table className="w-full text-xs">
                <tbody>
                  {(r.extremes?.wettest_days ?? []).map((d) => (
                    <tr key={d.date} className="border-t border-terminal-border/50">
                      <td className="py-1 text-terminal-muted">{d.date}</td>
                      <td className="py-1 text-right tabular-nums text-terminal-accent">{fmt(d.mm, 0)} mm</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Correlations over {r.coverage?.n_days.toLocaleString()} daily records: rainfall rises with humidity &amp;
          monsoon wind and falls with surface pressure — the expected monsoon signature. Lead/lag shows how each
          climate driver co-moves with rainfall at monthly leads/lags. Flood/drought rankings exclude the in-progress
          season. Normal Jun–Sep total: {fmt(r.normal_season_mm, 0)} mm.
        </p>
      </div>
    </div>
  );
}

function SeasonTable({ rows, tone }: { rows: { year: number; mm: number; deviation_pct: number | null }[]; tone: "pos" | "neg" }) {
  return (
    <table className="w-full text-xs">
      <tbody>
        {rows.map((s) => (
          <tr key={s.year} className="border-t border-terminal-border/50">
            <td className="py-1 text-terminal-text">{s.year}</td>
            <td className="py-1 text-right tabular-nums text-terminal-muted">{fmt(s.mm, 0)} mm</td>
            <td className={cn("py-1 text-right tabular-nums", tone === "pos" ? "text-terminal-pos" : "text-terminal-neg")}>
              {s.deviation_pct != null ? `${s.deviation_pct > 0 ? "+" : ""}${s.deviation_pct.toFixed(0)}%` : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
