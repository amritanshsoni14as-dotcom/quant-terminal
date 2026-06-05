"use client";

import { useRouter } from "next/navigation";
import { ChevronDown } from "lucide-react";
import type { CommodityItem } from "@/lib/api";

export default function CommoditySwitcher({ items, current }: { items: CommodityItem[]; current: string }) {
  const router = useRouter();
  return (
    <div className="relative inline-flex items-center">
      <select
        value={current}
        onChange={(e) => router.push(`/markets?symbol=${e.target.value}`)}
        className="appearance-none rounded-lg border border-terminal-border bg-terminal-panel pl-3 pr-9 py-2 text-sm font-semibold text-terminal-text focus:outline-none focus:border-terminal-accent/60 cursor-pointer"
      >
        {items.map((c) => (
          <option key={c.symbol} value={c.symbol} disabled={!c.has_data}>
            {c.name}{c.has_data ? "" : " (no data)"}
          </option>
        ))}
      </select>
      <ChevronDown className="h-4 w-4 text-terminal-muted absolute right-2.5 pointer-events-none" />
    </div>
  );
}
