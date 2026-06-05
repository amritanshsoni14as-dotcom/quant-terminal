"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export default function RefreshButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState("");

  async function run() {
    if (loading) return;
    setLoading(true);
    setNote("Fetching headlines & summarizing…");
    try {
      const res = await fetch("/api/altdata-refresh", { method: "POST" });
      const data = await res.json();
      setNote(data.available ? `Updated · ${data.n_headlines} headlines` : `Failed: ${data.reason ?? "error"}`);
      router.refresh();
    } catch (e) {
      setNote(`Failed: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button onClick={run} disabled={loading}
        className="flex items-center gap-2 rounded-lg border border-terminal-border bg-terminal-panel px-3 py-1.5 text-xs text-terminal-text hover:border-terminal-accent/60 disabled:opacity-50">
        <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        {loading ? "Refreshing…" : "Refresh digest"}
      </button>
      {note && <span className="text-[11px] text-terminal-muted">{note}</span>}
    </div>
  );
}
