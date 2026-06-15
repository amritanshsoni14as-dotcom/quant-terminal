import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import SignalJournal from "@/components/SignalJournal";

export const dynamic = "force-dynamic";

const TONE: Record<string, { text: string; bg: string }> = {
  STRONG_BUY: { text: "text-terminal-pos", bg: "bg-terminal-pos/15 border-terminal-pos/40" },
  BUY: { text: "text-terminal-pos", bg: "bg-terminal-pos/10 border-terminal-pos/30" },
  NEUTRAL: { text: "text-terminal-text", bg: "bg-terminal-border/40 border-terminal-border" },
  SELL: { text: "text-terminal-neg", bg: "bg-terminal-neg/10 border-terminal-neg/30" },
  STRONG_SELL: { text: "text-terminal-neg", bg: "bg-terminal-neg/15 border-terminal-neg/40" },
};

export default async function SignalPage() {
  const [signal, brief, history] = await Promise.all([
    api.signal(),
    api.brief(),
    api.signalHistory(100),
  ]);

  if (!signal?.available) {
    return (
      <div>
        <ModuleHeader title="Trading Signal Engine" subtitle="Module 9" />
        <div className="p-8 text-terminal-muted text-sm">No signal yet — run the signal engine.</div>
      </div>
    );
  }

  const sig = signal.signal ?? "NEUTRAL";
  const tone = TONE[sig] ?? TONE.NEUTRAL;
  const score = signal.score ?? 0;
  const comps = [...(signal.components ?? [])].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const maxC = Math.max(0.01, ...comps.map((c) => Math.abs(c.contribution)));

  return (
    <div>
      <ModuleHeader title="Trading Signal Engine" subtitle="Module 9 · explainable composite signal for RAINMUMBAI" />
      <DailyBrief />

      <div className="p-5 space-y-5">
        {/* Signal hero */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className={cn("rounded-xl border px-6 py-6 flex flex-col justify-center", tone.bg)}>
            <div className="text-[10px] uppercase tracking-wider text-terminal-muted">Signal · {signal.as_of}</div>
            <div className={cn("mt-1 text-4xl font-bold", tone.text)}>{sig.replace("_", " ")}</div>
            <div className="mt-3 flex gap-6 text-sm">
              <div><span className="text-terminal-muted">Score </span><span className="tabular-nums">{score >= 0 ? "+" : ""}{score.toFixed(2)}</span></div>
              <div><span className="text-terminal-muted">Confidence </span><span className="tabular-nums">{((signal.confidence ?? 0) * 100).toFixed(0)}%</span></div>
            </div>
            {/* score gauge -1..+1 */}
            <div className="mt-4">
              <div className="relative h-2 rounded-full bg-terminal-border">
                <div className="absolute top-1/2 -translate-y-1/2 h-4 w-0.5 bg-terminal-muted" style={{ left: "50%" }} />
                <div
                  className={cn("absolute top-1/2 -translate-y-1/2 h-3 w-3 rounded-full", score >= 0 ? "bg-terminal-pos" : "bg-terminal-neg")}
                  style={{ left: `calc(${((score + 1) / 2) * 100}% - 6px)` }}
                />
              </div>
              <div className="flex justify-between text-[9px] text-terminal-muted mt-1"><span>Strong Sell</span><span>Neutral</span><span>Strong Buy</span></div>
            </div>
          </div>

          {/* Factor contributions */}
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Factor contributions</CardTitle></CardHeader>
            <CardContent className="space-y-2.5">
              {comps.map((c) => {
                const pos = c.contribution >= 0;
                const w = (Math.abs(c.contribution) / maxC) * 50;
                return (
                  <div key={c.key} className="text-xs">
                    <div className="flex justify-between mb-1">
                      <span className="text-terminal-text">{c.label}</span>
                      <span className={cn("tabular-nums", pos ? "text-terminal-pos" : "text-terminal-neg")}>
                        {pos ? "+" : ""}{c.contribution.toFixed(3)} <span className="text-terminal-muted">· w{(c.weight * 100).toFixed(0)}%</span>
                      </span>
                    </div>
                    <div className="relative h-2 bg-terminal-border/40 rounded">
                      <div className="absolute top-0 h-2 w-px bg-terminal-muted" style={{ left: "50%" }} />
                      <div
                        className={cn("absolute top-0 h-2 rounded", pos ? "bg-terminal-pos" : "bg-terminal-neg")}
                        style={pos ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
                      />
                    </div>
                    <div className="text-terminal-muted mt-1">{c.detail}</div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        {/* Bull / Bear */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader><CardTitle>Top bullish factors</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(brief?.bullish_factors ?? []).length ? brief!.bullish_factors!.map((f, i) => (
                <div key={i} className="text-xs border-l-2 border-terminal-pos/50 pl-3">
                  <div className="text-terminal-text">{f.label} <span className="text-terminal-pos tabular-nums">+{f.contribution.toFixed(3)}</span></div>
                  <div className="text-terminal-muted">{f.detail}</div>
                </div>
              )) : <div className="text-terminal-muted text-sm">None currently.</div>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Top bearish factors</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(brief?.bearish_factors ?? []).length ? brief!.bearish_factors!.map((f, i) => (
                <div key={i} className="text-xs border-l-2 border-terminal-neg/50 pl-3">
                  <div className="text-terminal-text">{f.label} <span className="text-terminal-neg tabular-nums">{f.contribution.toFixed(3)}</span></div>
                  <div className="text-terminal-muted">{f.detail}</div>
                </div>
              )) : <div className="text-terminal-muted text-sm">None currently.</div>}
            </CardContent>
          </Card>
        </div>

        {/* Signal track record — append-only journal */}
        <SignalJournal entries={history?.entries ?? []} />
      </div>
    </div>
  );
}
