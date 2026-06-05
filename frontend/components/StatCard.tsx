import { cn } from "@/lib/utils";

export default function StatCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "pos" | "neg" | "warn" | "accent";
}) {
  const toneClass = {
    default: "text-terminal-text",
    pos: "text-terminal-pos",
    neg: "text-terminal-neg",
    warn: "text-terminal-warn",
    accent: "text-terminal-accent",
  }[tone];

  return (
    <div className="rounded-xl border border-terminal-border bg-terminal-card px-4 py-3">
      <div className="text-[10px] uppercase tracking-wider text-terminal-muted">{label}</div>
      <div className={cn("mt-1 text-2xl font-semibold tabular-nums", toneClass)}>{value}</div>
      {sub && <div className="mt-0.5 text-[11px] text-terminal-muted">{sub}</div>}
    </div>
  );
}
