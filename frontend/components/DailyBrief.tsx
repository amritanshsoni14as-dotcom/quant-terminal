import { api } from "@/lib/api";
import { fmt } from "@/lib/utils";

const SIGNAL_TONE: Record<string, string> = {
  STRONG_BUY: "text-terminal-pos", BUY: "text-terminal-pos",
  NEUTRAL: "text-terminal-text", SELL: "text-terminal-neg", STRONG_SELL: "text-terminal-neg",
};

// Persistent "Daily Brief" strip — the 8 final outputs of the system.
// Self-fetching async server component so every page shows the same header.
export default async function DailyBrief() {
  const [summary, drivers, brief] = await Promise.all([api.summary(), api.drivers(), api.brief()]);
  const oni = drivers?.ONI?.value ?? null;
  const enso = oni === null ? "—" : oni >= 0.5 ? "El Niño" : oni <= -0.5 ? "La Niña" : "Neutral";
  const dev = summary?.deviation_pct ?? null;
  const sig = brief?.signal ?? null;

  const cells: { k: string; v: string; tone?: string }[] = [
    { k: "E[Season]", v: fmt(brief?.expected_season_mm, 0, " mm") },
    { k: "Deviation", v: dev == null ? "—" : `${dev > 0 ? "+" : ""}${dev.toFixed(0)}%`, tone: dev == null ? "" : dev >= 0 ? "text-terminal-pos" : "text-terminal-neg" },
    { k: "Monsoon", v: summary?.monsoon_progress != null ? `${(summary.monsoon_progress * 100).toFixed(0)}%` : "—" },
    { k: "ENSO", v: enso, tone: enso === "El Niño" ? "text-terminal-neg" : enso === "La Niña" ? "text-terminal-pos" : "" },
    { k: "Fair Value", v: fmt(brief?.fair_value, 0) },
    { k: "Confidence", v: brief?.confidence_score != null ? `${(brief.confidence_score * 100).toFixed(0)}%` : "—", tone: "text-terminal-accent" },
    { k: "Revision P", v: brief?.revision_probability == null ? "Phase 3" : `${(brief.revision_probability * 100).toFixed(0)}%`, tone: brief?.revision_probability == null ? "text-terminal-muted" : "" },
    { k: "Signal", v: sig ? sig.replace("_", " ") : "—", tone: sig ? SIGNAL_TONE[sig] : "" },
  ];

  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-1 bg-terminal-panel border-t border-terminal-border text-[10px]">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full rounded-full bg-terminal-pos opacity-60 animate-ping" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-terminal-pos" />
        </span>
        <span className="uppercase tracking-wider text-terminal-pos font-semibold">Live</span>
        <span className="text-terminal-muted">
          data as of <span className="text-terminal-text">{summary?.as_of ?? "—"}</span> · auto-refresh 3 min
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-px bg-terminal-border border-y border-terminal-border">
        {cells.map((c) => (
          <div key={c.k} className="bg-terminal-panel px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-terminal-muted">{c.k}</div>
            <div className={`text-sm font-semibold tabular-nums ${c.tone || "text-terminal-text"}`}>{c.v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
