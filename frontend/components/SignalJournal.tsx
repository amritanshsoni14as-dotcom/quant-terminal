import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SignalLogEntry } from "@/lib/api";

const SIGNAL_TONE: Record<string, { text: string; bg: string }> = {
  STRONG_BUY:  { text: "text-terminal-pos", bg: "bg-terminal-pos/15 border-terminal-pos/40" },
  BUY:         { text: "text-terminal-pos", bg: "bg-terminal-pos/10 border-terminal-pos/30" },
  NEUTRAL:     { text: "text-terminal-text", bg: "bg-terminal-border/40 border-terminal-border" },
  SELL:        { text: "text-terminal-neg", bg: "bg-terminal-neg/10 border-terminal-neg/30" },
  STRONG_SELL: { text: "text-terminal-neg", bg: "bg-terminal-neg/15 border-terminal-neg/40" },
};

function SignalPill({ signal }: { signal: string }) {
  const tone = SIGNAL_TONE[signal] ?? SIGNAL_TONE.NEUTRAL;
  return (
    <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider", tone.bg, tone.text)}>
      {signal.replace("_", " ")}
    </span>
  );
}

function formatRelative(iso: string): string {
  // Tag the absolute timestamp; the relative bit is computed client-side once mounted.
  const d = new Date(iso);
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function SignalJournal({ entries }: { entries: SignalLogEntry[] }) {
  if (!entries.length) {
    return (
      <Card>
        <CardHeader><CardTitle>Signal track record</CardTitle></CardHeader>
        <CardContent className="text-terminal-muted text-sm">No signal events recorded yet — the journal will fill in as the model produces calls.</CardContent>
      </Card>
    );
  }

  // Current call is the newest entry (entries are returned newest-first).
  const current = entries[0];
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Signal track record</CardTitle>
        <span className="text-[10px] text-terminal-muted">
          {entries.length} event{entries.length === 1 ? "" : "s"} · append-only
        </span>
      </CardHeader>
      <CardContent>
        <div className="text-[11px] text-terminal-muted mb-3">
          Current call <SignalPill signal={current.signal} /> since{" "}
          <span className="text-terminal-text">{formatRelative(current.logged_at)}</span>
          {current.score != null && <> · score <span className="text-terminal-text tabular-nums">{current.score >= 0 ? "+" : ""}{current.score.toFixed(2)}</span></>}
          {current.confidence != null && <> · confidence <span className="text-terminal-text tabular-nums">{(current.confidence * 100).toFixed(0)}%</span></>}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-terminal-muted text-[10px] uppercase tracking-wider border-b border-terminal-border/60">
                <th className="text-left font-medium py-1.5">When</th>
                <th className="text-left font-medium py-1.5">Data date</th>
                <th className="text-left font-medium py-1.5">Transition</th>
                <th className="text-right font-medium py-1.5">Score</th>
                <th className="text-right font-medium py-1.5">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i} className="border-b border-terminal-border/40 hover:bg-terminal-card/30">
                  <td className="py-1.5 text-terminal-muted tabular-nums whitespace-nowrap">
                    <Clock className="h-3 w-3 inline mr-1 opacity-60" />
                    {formatRelative(e.logged_at)}
                  </td>
                  <td className="py-1.5 text-terminal-muted tabular-nums">{e.as_of}</td>
                  <td className="py-1.5">
                    <span className="inline-flex items-center gap-1.5">
                      {e.prev_signal ? (
                        <>
                          <SignalPill signal={e.prev_signal} />
                          <ArrowRight className="h-3 w-3 text-terminal-muted" />
                          <SignalPill signal={e.signal} />
                        </>
                      ) : (
                        <>
                          <SignalPill signal={e.signal} />
                          <span className="text-[10px] text-terminal-muted">first call</span>
                        </>
                      )}
                    </span>
                  </td>
                  <td className={cn("py-1.5 text-right tabular-nums",
                    e.score == null ? "text-terminal-muted" : e.score >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>
                    {e.score == null ? "—" : `${e.score >= 0 ? "+" : ""}${e.score.toFixed(2)}`}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-terminal-muted">
                    {e.confidence == null ? "—" : `${(e.confidence * 100).toFixed(0)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-[11px] text-terminal-muted mt-3">
          The journal records only state changes — every BUY ↔ SELL ↔ NEUTRAL transition the model makes,
          with the exact timestamp the new call was generated. Use it as a model track record.
        </p>
      </CardContent>
    </Card>
  );
}
