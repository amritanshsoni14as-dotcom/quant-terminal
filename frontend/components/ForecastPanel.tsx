import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CommodityForecastT } from "@/lib/api";

const HLABEL: Record<string, string> = { "5d": "1 Week", "21d": "1 Month", "63d": "1 Quarter" };

export default function ForecastPanel({ data, unit }: { data: CommodityForecastT; unit?: string }) {
  if (!data?.available || !data.horizons?.length) return null;
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>AI Forecast — bull / bear / neutral probability</CardTitle>
        <span className="text-[10px] text-terminal-muted">LightGBM × fundamental tilt · as of {data.as_of}</span>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.horizons.map((h) => {
            const up = (h.point_return_pct ?? 0) >= 0;
            return (
              <div key={h.horizon} className="rounded-lg border border-terminal-border bg-terminal-panel px-3 py-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs uppercase tracking-wider text-terminal-muted">{HLABEL[h.horizon] ?? h.horizon}</span>
                  <span className={cn("text-sm font-semibold tabular-nums", up ? "text-terminal-pos" : "text-terminal-neg")}>
                    {up ? "+" : ""}{h.point_return_pct?.toFixed(1)}%
                  </span>
                </div>
                <div className="text-[11px] text-terminal-muted">target ≈ {h.expected_price} {unit}</div>

                {/* stacked probability bar */}
                <div className="mt-2 h-3 rounded-full overflow-hidden flex text-[8px]">
                  <div className="bg-terminal-pos h-full" style={{ width: `${h.p_bull * 100}%` }} />
                  <div className="bg-terminal-muted/50 h-full" style={{ width: `${h.p_neutral * 100}%` }} />
                  <div className="bg-terminal-neg h-full" style={{ width: `${h.p_bear * 100}%` }} />
                </div>
                <div className="mt-1 flex justify-between text-[10px] tabular-nums">
                  <span className="text-terminal-pos">Bull {Math.round(h.p_bull * 100)}%</span>
                  <span className="text-terminal-muted">Neut {Math.round(h.p_neutral * 100)}%</span>
                  <span className="text-terminal-neg">Bear {Math.round(h.p_bear * 100)}%</span>
                </div>
                {h.drivers && (
                  <div className="mt-2 text-[10px] text-terminal-muted leading-relaxed">
                    ML {h.drivers.ml_return_pct?.toFixed(1)}% · tilt {h.drivers.fundamental_tilt}
                    {h.drivers.top_features?.length ? <> · drivers: {h.drivers.top_features.join(", ")}</> : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-[11px] text-terminal-muted">
          Per-horizon forward-return model (LightGBM on price features), blended with the fundamental
          Health composite, then converted to volatility-scaled bull / neutral / bear probabilities.
        </p>
      </CardContent>
    </Card>
  );
}
