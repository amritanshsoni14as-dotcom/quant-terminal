"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import type { PortfolioRow } from "@/lib/api";

const TABS = [
  { key: "health", label: "Overview", sort: (a: PortfolioRow, b: PortfolioRow) => b.health - a.health },
  { key: "bull", label: "Most Bullish", sort: (a: PortfolioRow, b: PortfolioRow) => (b.composite ?? 0) - (a.composite ?? 0) },
  { key: "bear", label: "Most Bearish", sort: (a: PortfolioRow, b: PortfolioRow) => (a.composite ?? 0) - (b.composite ?? 0) },
  { key: "risk", label: "Highest Risk", sort: (a: PortfolioRow, b: PortfolioRow) => (b.risk_score ?? 0) - (a.risk_score ?? 0) },
  { key: "opp", label: "Best Opportunity", sort: (a: PortfolioRow, b: PortfolioRow) => b.opportunity - a.opportunity },
];

function verdictTone(v?: string) {
  if (!v) return "text-terminal-text";
  if (v.includes("Bull")) return "text-terminal-pos";
  if (v.includes("Bear")) return "text-terminal-neg";
  return "text-terminal-muted";
}
function pct(v: number | null) {
  return v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export default function PortfolioTable({ rows }: { rows: PortfolioRow[] }) {
  const [tab, setTab] = useState("health");
  const active = TABS.find((t) => t.key === tab) ?? TABS[0];
  const sorted = [...rows].sort(active.sort);

  return (
    <div>
      <div className="flex gap-2 mb-3 flex-wrap">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={cn("text-xs rounded-full px-3 py-1.5 border transition-colors",
              tab === t.key ? "border-terminal-accent/60 text-terminal-accent bg-terminal-accent/10"
                : "border-terminal-border text-terminal-muted hover:text-terminal-text")}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-xl border border-terminal-border">
        <table className="w-full text-xs">
          <thead className="bg-terminal-panel">
            <tr className="text-terminal-muted text-[10px] uppercase">
              <th className="text-left font-medium px-3 py-2">Commodity</th>
              <th className="text-right font-medium px-3 py-2">Price</th>
              <th className="text-left font-medium px-3 py-2 w-40">Health</th>
              <th className="text-left font-medium px-3 py-2">Verdict</th>
              <th className="text-right font-medium px-3 py-2">Fcst 1M</th>
              <th className="text-right font-medium px-3 py-2">Bull%</th>
              <th className="text-right font-medium px-3 py-2">1M</th>
              <th className="text-right font-medium px-3 py-2">1Y</th>
              <th className="text-right font-medium px-3 py-2">Risk</th>
              <th className="text-right font-medium px-3 py-2">Opp</th>
              <th className="text-left font-medium px-3 py-2">Top driver</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.symbol} className="border-t border-terminal-border/50 hover:bg-terminal-card/40">
                <td className="px-3 py-2">
                  <Link href={`/markets?symbol=${r.symbol}`} className="text-terminal-text hover:text-terminal-accent font-medium">{r.name}</Link>
                  <span className="text-terminal-muted ml-1 text-[10px] uppercase">{r.category}</span>
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-terminal-muted">{r.price ?? "—"}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full bg-gradient-to-r from-terminal-neg via-terminal-muted to-terminal-pos relative">
                      <div className="absolute -top-0.5 h-2.5 w-0.5 bg-terminal-text" style={{ left: `calc(${r.health}% - 1px)` }} />
                    </div>
                    <span className="tabular-nums text-terminal-text w-6">{r.health}</span>
                  </div>
                </td>
                <td className={cn("px-3 py-2 font-medium", verdictTone(r.verdict))}>{r.verdict}</td>
                <td className={cn("px-3 py-2 text-right tabular-nums", (r.forecast_21d_pct ?? 0) >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>{pct(r.forecast_21d_pct)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-terminal-muted">{r.p_bull_21d == null ? "—" : `${Math.round(r.p_bull_21d * 100)}%`}</td>
                <td className={cn("px-3 py-2 text-right tabular-nums", (r.change_1m ?? 0) >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>{pct(r.change_1m)}</td>
                <td className={cn("px-3 py-2 text-right tabular-nums", (r.change_1y ?? 0) >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>{pct(r.change_1y)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-terminal-warn">{r.risk_score ?? "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums text-terminal-accent">{r.opportunity}</td>
                <td className="px-3 py-2 text-terminal-muted">{r.top_driver ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
