import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";

export const revalidate = 600;

const MODEL_LABEL: Record<string, string> = {
  linreg: "Linear Reg", random_forest: "Random Forest", xgboost: "XGBoost",
  lightgbm: "LightGBM", prophet: "Prophet", lstm: "LSTM", transformer: "Transformer",
};

export default async function MLPage() {
  const [lb, fc] = await Promise.all([api.leaderboard(), api.mlForecasts()]);

  if (!lb?.available) {
    return (
      <div>
        <ModuleHeader title="Machine Learning Lab" subtitle="Module 6" />
        <div className="p-8 text-terminal-muted text-sm">No models trained yet — run <code className="text-terminal-accent">python -m app.ml.run</code>.</div>
      </div>
    );
  }

  return (
    <div>
      <ModuleHeader title="Machine Learning Lab" subtitle={`Module 6 · 7 models × 5 horizons · time-series CV + DL holdout`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        {/* Champion forecasts */}
        <Card>
          <CardHeader><CardTitle>Champion forecasts · issued {fc?.issued_date}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {(fc?.forecasts ?? []).map((f) => (
                <div key={f.horizon} className="rounded-lg border border-terminal-border bg-terminal-panel px-3 py-2.5">
                  <div className="flex justify-between items-baseline">
                    <span className="text-[10px] uppercase tracking-wider text-terminal-muted">{f.horizon}</span>
                    <span className="text-[9px] text-terminal-accent">{MODEL_LABEL[f.model] ?? f.model}</span>
                  </div>
                  <div className="text-xl font-semibold text-terminal-text tabular-nums mt-0.5">{fmt(f.point_mm, 0)}<span className="text-xs text-terminal-muted"> mm</span></div>
                  <div className="text-[10px] text-terminal-muted">[{fmt(f.p10_mm, 0)}–{fmt(f.p90_mm, 0)}] · conf {(f.confidence * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Leaderboards per horizon */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {(lb.horizons ?? []).map((h) => (
            <Card key={h.horizon}>
              <CardHeader><CardTitle>{h.horizon} rainfall — leaderboard</CardTitle></CardHeader>
              <CardContent>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-terminal-muted text-[10px] uppercase">
                      <th className="text-left font-medium pb-1">Model</th>
                      <th className="text-right font-medium pb-1">RMSE</th>
                      <th className="text-right font-medium pb-1">MAE</th>
                      <th className="text-right font-medium pb-1">Hit</th>
                      <th className="text-right font-medium pb-1">Dir</th>
                    </tr>
                  </thead>
                  <tbody>
                    {h.models.map((m) => (
                      <tr key={m.model} className={cn("border-t border-terminal-border/50", m.is_champion && "bg-terminal-pos/5")}>
                        <td className="py-1 text-terminal-text">
                          {m.is_champion && <span className="text-terminal-pos">★ </span>}
                          {MODEL_LABEL[m.model] ?? m.model}
                        </td>
                        <td className="py-1 text-right tabular-nums">{fmt(m.rmse, 1)}</td>
                        <td className="py-1 text-right tabular-nums text-terminal-muted">{fmt(m.mae, 1)}</td>
                        <td className="py-1 text-right tabular-nums text-terminal-muted">{m.hit_rate != null ? (m.hit_rate * 100).toFixed(0) : "—"}</td>
                        <td className="py-1 text-right tabular-nums text-terminal-muted">{m.directional_acc != null ? (m.directional_acc * 100).toFixed(0) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Targets are h-day-forward cumulative rainfall. Metrics are pooled over expanding-window
          time-series CV (no look-ahead) for the tabular/Prophet models; LSTM &amp; Transformer (PyTorch
          sequence models, 21-day window) use a single chronological holdout. ★ = champion (lowest RMSE),
          promoted to generate the live forecast for that horizon.
        </p>
      </div>
    </div>
  );
}
