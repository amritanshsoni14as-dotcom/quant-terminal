"use client";

import { useState } from "react";
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
  const d = new Date(iso);
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

type ViewMode = "all" | "changes";

export default function SignalJournal({ entries }: { entries: SignalLogEntry[] }) {
  const [view, setView] = useState<ViewMode>("all");

  if (!entries.length) {
    return (
      <Card>
        <CardHeader><CardTitle>Signal track record</CardTitle></CardHeader>
        <CardContent className="text-terminal-muted text-sm">No signal events recorded yet — the journal will fill in as the model produces calls.</CardContent>
      </Card>
    );
  }

  const current = entries[0];
  const transitions = entries.filter((e) => e.event_type !== "same");
  const shown = view === "all" ? entries : transitions;

  const totalDays = entries.length;
  const transitionsCount = transitions.length;
  const inception = entries[entries.length - 1]?.as_of;

  const signalCounts: Record<string, number> = {};
  for (const e of entries) signalCounts[e.signal] = (signalCounts[e.signal] || 0) + 1;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Signal track record</CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-terminal-muted">
            {totalDays} day{totalDays === 1 ? "" : "s"} · {transitionsCount} transition{transitionsCount === 1 ? "" : "s"}
          </span>
          <div className="flex border border-terminal-border/60 rounded text-[10px] overflow-hidden">
            <button
              onClick={() => setView("all")}
              className={cn("px-2 py-0.5 transition-colors",
                view === "all" ? "bg-terminal-accent/20 text-terminal-accent" : "text-terminal-muted hover:text-terminal-text")}
            >All days</button>
            <button
              onClick={() => setView("changes")}
              className={cn("px-2 py-0.5 transition-colors border-l border-terminal-border/60",
                view === "changes" ? "bg-terminal-accent/20 text-terminal-accent" : "text-terminal-muted hover:text-terminal-text")}
            >Changes only</button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-[11px] text-terminal-muted mb-3">
          Current call <SignalPill signal={current.signal} /> as of{" "}
          <span className="text-terminal-text">{formatRelative(current.logged_at)}</span>
          {current.score != null && <> · score <span className="text-terminal-text tabular-nums">{current.score >= 0 ? "+" : ""}{current.score.toFixed(2)}</span></>}
          {current.confidence != null && <> · confidence <span className="text-terminal-text tabular-nums">{(current.confidence * 100).toFixed(0)}%</span></>}
          {inception && <> · since inception <span className="text-terminal-text">{inception}</span></>}
        </div>

        {/* Signal distribution over the full track record */}
        <div className="flex flex-wrap gap-3 mb-3 text-[10px]">
          {Object.entries(signalCounts).map(([sig, count]) => (
            <div key={sig} className="flex items-center gap-1.5">
              <SignalPill signal={sig} />
              <span className="text-terminal-muted tabular-nums">{count} ({((count / totalDays) * 100).toFixed(0)}%)</span>
            </div>
          ))}
        </div>

        <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-terminal-card z-10">
              <tr className="text-terminal-muted text-[10px] uppercase tracking-wider border-b border-terminal-border/60">
                <th className="text-left font-medium py-1.5">When</th>
                <th className="text-left font-medium py-1.5">Data date</th>
                <th className="text-left font-medium py-1.5">Signal</th>
                <th className="text-right font-medium py-1.5">Score</th>
                <th className="text-right font-medium py-1.5">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((e, i) => {
                const isChange = e.event_type !== "same";
                return (
                  <tr key={i} className={cn("border-b border-terminal-border/40 hover:bg-terminal-card/30",
                    isChange && "bg-terminal-accent/5")}>
                    <td className="py-1.5 text-terminal-muted tabular-nums whitespace-nowrap">
                      <Clock className="h-3 w-3 inline mr-1 opacity-60" />
                      {formatRelative(e.logged_at)}
                    </td>
                    <td className="py-1.5 text-terminal-muted tabular-nums">{e.as_of}</td>
                    <td className="py-1.5">
                      <span className="inline-flex items-center gap-1.5">
                        {isChange && e.prev_signal ? (
                          <>
                            <SignalPill signal={e.prev_signal} />
                            <ArrowRight className="h-3 w-3 text-terminal-muted" />
                            <SignalPill signal={e.signal} />
                          </>
                        ) : isChange ? (
                          <>
                            <SignalPill signal={e.signal} />
                            <span className="text-[10px] text-terminal-muted">first call</span>
                          </>
                        ) : (
                          <SignalPill signal={e.signal} />
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
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="text-[11px] text-terminal-muted mt-3">
          Every daily call the model has made since inception is logged here. Highlighted
          rows are BUY ↔ SELL ↔ NEUTRAL transitions. Use this as the full model track
          record for accuracy analysis.
        </p>
      </CardContent>
    </Card>
  );
}
