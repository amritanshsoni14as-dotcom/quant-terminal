import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import { ImpactBars, MJOPhaseChart } from "@/components/charts4";
import type { DriverPanel } from "@/lib/api";

export const revalidate = 600;

function stateTone(state?: string | null) {
  if (!state) return "text-terminal-text";
  if (["La Niña", "Positive"].includes(state)) return "text-terminal-pos";
  if (["El Niño", "Negative"].includes(state)) return "text-terminal-neg";
  return "text-terminal-text";
}

function DriverCard({ title, panel, normal, fmtVal }: { title: string; panel: DriverPanel; normal: number; fmtVal: (n: number | null) => string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <span className={cn("text-sm font-semibold", stateTone(panel.state))}>{panel.state ?? "—"}</span>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-4 mb-2">
          <div className="text-3xl font-bold tabular-nums text-terminal-text">{fmtVal(panel.current)}</div>
          <div className="text-[11px] text-terminal-muted">
            as of {panel.as_of}<br />
            corr w/ rainfall: <span className={cn("tabular-nums", (panel.correlation ?? 0) >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>{panel.correlation ?? "—"}</span>
          </div>
        </div>
        <ImpactBars impact={panel.impact} normal={normal} />
        <p className="text-[11px] text-terminal-muted mt-2">{panel.note}</p>
      </CardContent>
    </Card>
  );
}

export default async function MonsoonPage() {
  const m = await api.monsoon();
  if (!m?.available || !m.enso || !m.iod || !m.mjo) {
    return (
      <div>
        <ModuleHeader title="Monsoon Intelligence" subtitle="Module 3" />
        <div className="p-8 text-terminal-muted text-sm">No data.</div>
      </div>
    );
  }
  const normal = m.normal_season_mm ?? 0;

  return (
    <div>
      <ModuleHeader title="Monsoon Intelligence" subtitle={`Module 3 · ENSO · IOD · MJO vs Mumbai rainfall · ${m.coverage_years?.[0]}–${m.coverage_years?.[1]}`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <DriverCard title="ENSO · ONI (Niño 3.4 SST anomaly)" panel={m.enso} normal={normal} fmtVal={(n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)}`)} />
          <DriverCard title="Indian Ocean Dipole · DMI" panel={m.iod} normal={normal} fmtVal={(n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)}`)} />
        </div>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Madden–Julian Oscillation — rainfall by phase</CardTitle>
            <span className="text-sm font-semibold text-terminal-accent">
              Phase {m.mjo.current_phase ?? "—"} · amp {fmt(m.mjo.current_amp, 1)}
            </span>
          </CardHeader>
          <CardContent>
            <MJOPhaseChart mjo={m.mjo} />
            <p className="text-[11px] text-terminal-muted mt-2">{m.mjo.note} Blue = convectively favourable phases (1–4); dashed = all-phase average.</p>
          </CardContent>
        </Card>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Historical impact bars show mean Jun–Sep rainfall in years of each regime vs the {fmt(normal, 0)} mm normal.
          The ENSO correlation of {m.enso.correlation} reflects the well-documented relationship — El Niño suppresses,
          La Niña enhances the Indian monsoon. These regimes feed the Trading Signal and Scenario Analysis.
        </p>
      </div>
    </div>
  );
}
