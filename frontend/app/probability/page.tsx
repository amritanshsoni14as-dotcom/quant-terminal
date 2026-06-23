import { api } from "@/lib/api";
import { fmt } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import StatCard from "@/components/StatCard";
import { ProbabilityDistChart } from "@/components/charts2";

export const revalidate = 600;

const BARS: { key: string; label: string; tone: string }[] = [
  { key: "above_normal", label: "P(Above Normal)", tone: "bg-terminal-pos" },
  { key: "below_normal", label: "P(Below Normal)", tone: "bg-terminal-neg" },
  { key: "above_10pct", label: "P(> +10%)", tone: "bg-terminal-pos/80" },
  { key: "above_20pct", label: "P(> +20%)", tone: "bg-terminal-pos/60" },
  { key: "below_10pct", label: "P(< −10%)", tone: "bg-terminal-neg/80" },
  { key: "below_20pct", label: "P(< −20%)", tone: "bg-terminal-neg/60" },
];

export default async function ProbabilityPage() {
  const prob = await api.probability();
  if (!prob?.available) {
    return (
      <div>
        <ModuleHeader title="Probability Engine" subtitle="Module 8" />
        <div className="p-8 text-terminal-muted text-sm">No probability snapshot yet — run the signal engine.</div>
      </div>
    );
  }
  const p = prob.probabilities ?? {};

  return (
    <div>
      <ModuleHeader title="Probability Engine" subtitle={`Module 8 · ${prob.method} over ${prob.n_years} seasons · as of ${prob.as_of}`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Expected Season" value={fmt(prob.expected_mm, 0, " mm")} tone="accent" />
          <StatCard label="Climatological Normal" value={fmt(prob.normal_mm, 0, " mm")} />
          <StatCard label="Posterior σ" value={fmt(prob.posterior_sd_mm, 0, " mm")} sub="forecast uncertainty" />
          <StatCard label="P(Above Normal)" value={`${((p.above_normal ?? 0) * 100).toFixed(0)}%`} tone={(p.above_normal ?? 0) >= 0.5 ? "pos" : "neg"} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Posterior distribution of seasonal rainfall</CardTitle></CardHeader>
            <CardContent><ProbabilityDistChart data={prob} /></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Threshold probabilities</CardTitle></CardHeader>
            <CardContent className="space-y-3 pt-1">
              {BARS.map((b) => {
                const v = (p[b.key] ?? 0) * 100;
                return (
                  <div key={b.key} className="text-xs">
                    <div className="flex justify-between mb-1">
                      <span className="text-terminal-text">{b.label}</span>
                      <span className="tabular-nums text-terminal-muted">{v.toFixed(0)}%</span>
                    </div>
                    <div className="h-2.5 rounded bg-terminal-border/40">
                      <div className={`h-2.5 rounded ${b.tone}`} style={{ width: `${v}%` }} />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Method: the full Jun–Sep total is regressed on rainfall accumulated to today across {prob.n_years} historical
          seasons, giving a predictive Normal({fmt(prob.expected_mm, 0)}, {fmt(prob.posterior_sd_mm, 0)}) that updates as
          the monsoon progresses. Probabilities are evaluated against the climatological normal of {fmt(prob.normal_mm, 0)} mm.
        </p>
      </div>
    </div>
  );
}
