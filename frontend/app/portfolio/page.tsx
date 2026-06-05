import { api } from "@/lib/api";
import ModuleHeader from "@/components/ModuleHeader";
import StatCard from "@/components/StatCard";
import PortfolioTable from "@/components/PortfolioTable";

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  const p = await api.portfolio();

  if (!p?.available || !p.commodities?.length) {
    return (
      <div>
        <ModuleHeader title="Portfolio Mode" subtitle="Cross-commodity ranking" />
        <div className="p-8 text-terminal-muted text-sm">No commodities scored yet.</div>
      </div>
    );
  }

  const s = p.summary;
  return (
    <div>
      <ModuleHeader title="Portfolio Mode" subtitle="Cross-commodity ranking · health · forecast · risk · opportunity" />
      <div className="p-5 space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Commodities" value={String(s?.count ?? 0)} />
          <StatCard label="Bullish" value={String(s?.bullish ?? 0)} tone="pos" />
          <StatCard label="Bearish" value={String(s?.bearish ?? 0)} tone="neg" />
          <StatCard label="Avg Health" value={s?.avg_health != null ? String(s.avg_health) : "—"} tone="accent" />
        </div>

        <PortfolioTable rows={p.commodities} />

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Health = config-driven fundamental score (technical · valuation · macro · positioning, with
          supply/demand/inventory once keyed). Fcst 1M &amp; Bull% come from the blended LightGBM forecast.
          Opportunity blends fundamental health + forecast tilt − risk. Click any commodity to open its
          Command Center.
        </p>
      </div>
    </div>
  );
}
