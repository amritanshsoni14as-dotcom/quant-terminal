import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import RefreshButton from "@/components/RefreshButton";

export const dynamic = "force-dynamic";

function FactorList({ items, tone }: { items: string[]; tone: string }) {
  if (!items.length) return <div className="text-terminal-muted text-xs">None identified.</div>;
  return (
    <ul className="space-y-1.5">
      {items.map((t, i) => (
        <li key={i} className={cn("text-xs border-l-2 pl-2 leading-relaxed", tone)}>{t}</li>
      ))}
    </ul>
  );
}

export default async function AltDataPage() {
  const d = await api.altdata();

  return (
    <div>
      <ModuleHeader title="Alternative-Data Research" subtitle="Module 11 · monsoon news → AI-extracted factors" />
      <DailyBrief />

      <div className="p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div className="text-xs text-terminal-muted">
            {d?.available ? <>Digest as of <span className="text-terminal-text">{d.as_of?.slice(0, 16).replace("T", " ")}</span>
              {d.sentiment != null && <> · sentiment <span className={cn("tabular-nums", d.sentiment >= 0 ? "text-terminal-pos" : "text-terminal-neg")}>{d.sentiment > 0 ? "+" : ""}{d.sentiment.toFixed(2)}</span></>}</>
              : "No digest yet — generate one."}
          </div>
          <RefreshButton />
        </div>

        {!d?.available ? (
          <Card><CardContent className="py-8 text-center text-terminal-muted text-sm">
            Click <span className="text-terminal-text">Refresh digest</span> to pull recent monsoon news and
            extract bullish / bearish factors via the AI model.
          </CardContent></Card>
        ) : (
          <>
            <Card>
              <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
              <CardContent><p className="text-sm text-terminal-text leading-relaxed">{d.summary}</p></CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader><CardTitle>Bullish factors</CardTitle></CardHeader>
                <CardContent><FactorList items={d.bullish ?? []} tone="border-terminal-pos/50 text-terminal-text" /></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Bearish factors</CardTitle></CardHeader>
                <CardContent><FactorList items={d.bearish ?? []} tone="border-terminal-neg/50 text-terminal-text" /></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Key risks</CardTitle></CardHeader>
                <CardContent><FactorList items={d.risks ?? []} tone="border-terminal-warn/50 text-terminal-text" /></CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader><CardTitle>Source headlines ({d.headlines?.length ?? 0})</CardTitle></CardHeader>
              <CardContent className="space-y-1.5">
                {(d.headlines ?? []).map((h, i) => (
                  <a key={i} href={h.url} target="_blank" rel="noopener noreferrer"
                     className="block text-xs text-terminal-muted hover:text-terminal-accent leading-relaxed">
                    • {h.title}
                  </a>
                ))}
              </CardContent>
            </Card>
          </>
        )}

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Headlines from Google News (monsoon / IMD / ENSO / IOD queries) are summarized by the AI model into
          rainfall-relevant factors. This is sentiment/context, not a primary signal — a qualitative overlay on the
          quantitative modules.
        </p>
      </div>
    </div>
  );
}
