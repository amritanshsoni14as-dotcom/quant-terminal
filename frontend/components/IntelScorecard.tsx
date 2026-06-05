import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Scorecard } from "@/lib/api";

const CAT_LABEL: Record<string, string> = {
  technical: "Technical / Trend", valuation: "Valuation (Rogers)", macro: "Macro",
  supply: "Supply", demand: "Demand", inventory: "Inventory", weather: "Weather",
  positioning: "Positioning", supply_capacity: "Supply Capacity", regime: "Regime",
};
const ALL_CATS = ["supply", "demand", "inventory", "weather", "macro", "positioning", "technical", "valuation"];

function verdictTone(v?: string) {
  if (!v) return "text-terminal-text";
  if (v.includes("Bull")) return "text-terminal-pos";
  if (v.includes("Bear")) return "text-terminal-neg";
  return "text-terminal-text";
}

function DivergingBar({ score }: { score: number }) {
  const pos = score >= 0;
  const w = Math.min(50, Math.abs(score) * 50);
  return (
    <div className="relative h-2 bg-terminal-border/40 rounded">
      <div className="absolute top-0 h-2 w-px bg-terminal-muted" style={{ left: "50%" }} />
      <div className={cn("absolute top-0 h-2 rounded", pos ? "bg-terminal-pos" : "bg-terminal-neg")}
        style={pos ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
    </div>
  );
}

export default function IntelScorecard({ data }: { data: Scorecard }) {
  if (!data?.available) return null;
  const health = data.health ?? 50;
  const covered = new Set(data.covered_categories ?? []);
  const catMap = new Map((data.categories ?? []).map((c) => [c.category, c]));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Health hero */}
      <Card>
        <CardHeader><CardTitle>Commodity Health Score</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-end gap-3">
            <div className={cn("text-5xl font-bold tabular-nums", verdictTone(data.verdict))}>{health}</div>
            <div className="text-sm text-terminal-muted mb-1">/100</div>
          </div>
          <div className={cn("text-sm font-semibold mt-1", verdictTone(data.verdict))}>{data.verdict}</div>
          <div className="mt-3 h-2.5 rounded-full bg-gradient-to-r from-terminal-neg via-terminal-muted to-terminal-pos relative">
            <div className="absolute -top-1 h-4 w-1 bg-terminal-text rounded" style={{ left: `calc(${health}% - 2px)` }} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-terminal-border bg-terminal-panel px-3 py-2">
              <div className="text-[10px] uppercase text-terminal-muted">Trend</div>
              <div className="text-lg tabular-nums text-terminal-text">{data.trend_score ?? "—"}</div>
            </div>
            <div className="rounded-lg border border-terminal-border bg-terminal-panel px-3 py-2">
              <div className="text-[10px] uppercase text-terminal-muted">Risk</div>
              <div className="text-lg tabular-nums text-terminal-warn">{data.risk_score ?? "—"}</div>
            </div>
          </div>
          {data.secular && typeof data.secular.supply_lead_time_months === "number" && (
            <p className="mt-3 text-[11px] text-terminal-muted">
              Rogers lens · new-supply lead time ≈ {Math.round((data.secular.supply_lead_time_months as number) / 12)}y
              {data.substitutes?.length ? ` · substitute: ${data.substitutes.join(", ")}` : ""}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Category scorecard */}
      <Card className="lg:col-span-2">
        <CardHeader><CardTitle>Category scores → composite</CardTitle></CardHeader>
        <CardContent className="space-y-2.5">
          {ALL_CATS.map((cat) => {
            const c = catMap.get(cat);
            const live = covered.has(cat);
            return (
              <div key={cat} className="text-xs">
                <div className="flex justify-between mb-1">
                  <span className={cn(live ? "text-terminal-text" : "text-terminal-muted/60")}>
                    {CAT_LABEL[cat] ?? cat}{!live && <span className="ml-2 text-[9px] uppercase rounded bg-terminal-border px-1 py-0.5">Phase 2</span>}
                  </span>
                  {c && <span className={cn("tabular-nums", c.score >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>{c.score >= 0 ? "+" : ""}{c.score.toFixed(2)}</span>}
                </div>
                {c ? <DivergingBar score={c.score} /> : <div className="h-2 bg-terminal-border/20 rounded" />}
                {c && (
                  <div className="text-terminal-muted mt-1">
                    {c.contributors.map((k) => `${k.label} ${k.sub_score >= 0 ? "+" : ""}${k.sub_score.toFixed(2)}`).join(" · ")}
                  </div>
                )}
              </div>
            );
          })}
          {(data.pending_phase2?.length ?? 0) > 0 && (
            <p className="text-[11px] text-terminal-muted pt-1 border-t border-terminal-border/50">
              Phase 2 adds real fundamentals: {data.pending_phase2!.join(" · ")}.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
