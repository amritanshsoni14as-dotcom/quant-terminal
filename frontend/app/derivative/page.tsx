import { api } from "@/lib/api";
import { fmt } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import StatCard from "@/components/StatCard";
import { PayoffCurveChart } from "@/components/charts2";

export const dynamic = "force-dynamic";

export default async function DerivativePage() {
  const [fv, spec] = await Promise.all([api.fairValue(), api.spec()]);

  if (!fv?.available) {
    return (
      <div>
        <ModuleHeader title="Rainfall Derivative Monitor" subtitle="Module 2" />
        <div className="p-8 text-terminal-muted text-sm">No fair value yet — run the signal engine.</div>
      </div>
    );
  }
  const pp = (spec?.payoff_params ?? {}) as Record<string, number | string>;

  return (
    <div>
      <ModuleHeader title="Rainfall Derivative Monitor" subtitle={`Module 2 · RAINMUMBAI · model-derived · as of ${fv.as_of}`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Model Fair Value" value={fmt(fv.fair_value, 1)} tone="accent" />
          <StatCard label="Expected Settle" value={fmt(fv.expected_settle, 0, " mm")} sub="E[rainfall index]" />
          <StatCard label="Market Price" value={fv.market_price == null ? "—" : fmt(fv.market_price, 1)} sub={fv.has_market_data ? "" : "ingest CSV"} />
          <StatCard
            label="Mispricing"
            value={fv.mispricing == null ? "—" : fmt(fv.mispricing, 1)}
            tone={fv.mispricing == null ? "default" : fv.mispricing >= 0 ? "pos" : "neg"}
            sub={fv.has_market_data ? "fair − market" : "needs market data"}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Contract payoff function</CardTitle></CardHeader>
            <CardContent><PayoffCurveChart data={fv} /></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Contract specification</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1.5 text-terminal-text">
              <Row k="Symbol" v={spec?.symbol} />
              <Row k="Accrual" v={`${spec?.accrual_start} → ${spec?.accrual_end}`} />
              <Row k="Payoff type" v={spec?.payoff_type} />
              <Row k="Index" v={String(pp.index ?? "")} />
              <Row k="Strike" v={fmt(pp.strike as number, 0, " mm")} />
              <Row k="Tick" v={String(pp.tick ?? "")} />
              <Row k="Floor / Cap" v={`${pp.floor} / ${pp.cap}`} />
              <p className="text-terminal-muted pt-2 leading-relaxed">{spec?.description}</p>
            </CardContent>
          </Card>
        </div>

        {!fv.has_market_data && (
          <div className="rounded-xl border border-terminal-warn/30 bg-terminal-warn/5 px-4 py-3 text-xs text-terminal-muted">
            <span className="text-terminal-warn font-semibold">Market data not loaded.</span>{" "}
            Fair value is fully model-derived. Import NCDEX prices to unlock market price + mispricing:
            <code className="text-terminal-accent"> python -m app.ingest.ncdex prices.csv</code>{" "}
            or POST to <code className="text-terminal-accent">/api/v1/derivative/prices</code> — no other changes needed.
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v?: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-terminal-muted">{k}</span>
      <span className="tabular-nums text-right">{v ?? "—"}</span>
    </div>
  );
}
