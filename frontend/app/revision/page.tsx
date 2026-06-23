import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import StatCard from "@/components/StatCard";
import { RevisionSeriesChart } from "@/components/charts3";

export const revalidate = 600;

export default async function RevisionPage() {
  const rev = await api.revision();
  if (!rev?.available) {
    return (
      <div>
        <ModuleHeader title="Forecast Revision Engine" subtitle="Module 7" />
        <div className="p-8 text-terminal-muted text-sm">No revision model yet — run <code className="text-terminal-accent">python -m app.signals.run</code>.</div>
      </div>
    );
  }

  const pUp = rev.prob_revise_up ?? 0.5;
  const up = pUp >= 0.5;

  return (
    <div>
      <ModuleHeader title="Forecast Revision Engine" subtitle={`Module 7 · the primary alpha · as of ${rev.as_of}`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Hero */}
          <div className={cn("rounded-xl border px-6 py-6 flex flex-col justify-center",
            up ? "bg-terminal-pos/10 border-terminal-pos/40" : "bg-terminal-neg/10 border-terminal-neg/40")}>
            <div className="text-[10px] uppercase tracking-wider text-terminal-muted">Probability the seasonal forecast is revised…</div>
            <div className={cn("mt-1 text-4xl font-bold", up ? "text-terminal-pos" : "text-terminal-neg")}>
              {up ? "UP" : "DOWN"} {((up ? pUp : (rev.prob_revise_down ?? 0)) * 100).toFixed(0)}%
            </div>
            <div className="mt-3 text-sm text-terminal-muted">
              Expected revision <span className={cn("tabular-nums", (rev.expected_revision_mm ?? 0) >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>
                {(rev.expected_revision_mm ?? 0) >= 0 ? "+" : ""}{fmt(rev.expected_revision_mm, 0)} mm</span>
            </div>
            {/* up/down bar */}
            <div className="mt-4 h-2.5 rounded-full overflow-hidden flex">
              <div className="bg-terminal-pos h-full" style={{ width: `${pUp * 100}%` }} />
              <div className="bg-terminal-neg h-full" style={{ width: `${(1 - pUp) * 100}%` }} />
            </div>
            <div className="flex justify-between text-[9px] text-terminal-muted mt-1"><span>revise up</span><span>revise down</span></div>
          </div>

          <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-3 content-start">
            <StatCard label="P(revise up)" value={`${(pUp * 100).toFixed(0)}%`} tone={up ? "pos" : "neg"} />
            <StatCard label="Expected Market Impact" value={fmt(rev.expected_market_impact, 0)} sub="revision × tick" tone={(rev.expected_market_impact ?? 0) >= 0 ? "pos" : "neg"} />
            <StatCard label="Model Confidence" value={`${((rev.confidence ?? 0) * 100).toFixed(0)}%`} tone="accent" />
            <StatCard label="Backtest Accuracy" value={rev.model?.test_accuracy != null ? `${(rev.model.test_accuracy * 100).toFixed(0)}%` : "—"} sub={`n=${rev.model?.n_samples ?? "—"}`} />
          </div>
        </div>

        <Card>
          <CardHeader><CardTitle>How the seasonal forecast evolved &amp; revised — {rev.display_season} monsoon</CardTitle></CardHeader>
          <CardContent>
            {(rev.forecast_series ?? []).length ? <RevisionSeriesChart data={rev} /> :
              <div className="h-[300px] flex items-center justify-center text-terminal-muted text-sm">Season just started — series builds as the monsoon progresses.</div>}
          </CardContent>
        </Card>

        <p className="text-[11px] text-terminal-muted max-w-3xl leading-relaxed">
          This is the core idea: rainfall derivatives reprice on how the <em>seasonal forecast changes</em>, not on
          today&apos;s rain. We reconstruct E[season] with no look-ahead for every week of every past monsoon
          (analog regression on prior years), difference consecutive estimates to get the realised revisions, and
          train a model on {rev.model?.n_samples} examples to predict the next revision&apos;s direction and size from
          the climate drivers and revision momentum. Backtest accuracy {rev.model?.test_accuracy != null ? `${(rev.model.test_accuracy * 100).toFixed(0)}%` : "—"} vs
          a {rev.model?.base_rate_up != null ? `${(rev.model.base_rate_up * 100).toFixed(0)}%` : "—"} base rate — modest, as expected for a hard problem; it feeds the
          Trading Signal as the highest-weighted in-season factor.
        </p>
      </div>
    </div>
  );
}
