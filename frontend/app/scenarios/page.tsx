import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import { ScenarioChart } from "@/components/charts4";

export const revalidate = 60;

export default async function ScenariosPage() {
  const s = await api.scenarios();
  if (!s?.available || !s.scenarios) {
    return (
      <div>
        <ModuleHeader title="Scenario Analysis" subtitle="Module 10" />
        <div className="p-8 text-terminal-muted text-sm">No data.</div>
      </div>
    );
  }
  const normal = s.normal_season_mm ?? 0;

  return (
    <div>
      <ModuleHeader title="Scenario Analysis" subtitle={`Module 10 · projected seasonal rainfall by climate regime · ${s.n_total_years} analog years`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <Card>
          <CardHeader><CardTitle>Projected seasonal rainfall vs normal ({fmt(normal, 0)} mm)</CardTitle></CardHeader>
          <CardContent><ScenarioChart scenarios={s.scenarios} normal={normal} /></CardContent>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {s.scenarios.map((sc) => {
            const dev = sc.deviation_pct ?? 0;
            return (
              <Card key={sc.code}>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>{sc.label}</CardTitle>
                  <span className={cn("text-sm font-semibold tabular-nums", dev >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>
                    {dev >= 0 ? "+" : ""}{dev.toFixed(0)}%
                  </span>
                </CardHeader>
                <CardContent className="text-xs space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-terminal-muted">Projected season</span>
                    <span className="tabular-nums text-terminal-text">{fmt(sc.projected_season_mm, 0)} mm</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-muted">Analog years</span>
                    <span className="tabular-nums">{sc.n_years} <span className="text-terminal-muted">({(sc.probability * 100).toFixed(0)}% of record)</span></span>
                  </div>
                  {sc.distribution && (
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">Range (p25–p75)</span>
                      <span className="tabular-nums text-terminal-muted">{fmt(sc.distribution.p25, 0)}–{fmt(sc.distribution.p75, 0)}</span>
                    </div>
                  )}
                  <p className="text-terminal-muted pt-1 leading-relaxed">{sc.note}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Each scenario conditions on the historical analog years matching that regime and reports their mean
          Jun–Sep rainfall and deviation from the {fmt(normal, 0)} mm normal. Small analog counts (n) mean wider
          uncertainty. Proxied scenarios are noted; direct Arabian-Sea SST and onset-date data arrive in a later phase.
        </p>
      </div>
    </div>
  );
}
