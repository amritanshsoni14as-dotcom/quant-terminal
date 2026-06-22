import { api } from "@/lib/api";
import { fmt, cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DailyBrief from "@/components/DailyBrief";
import ModuleHeader from "@/components/ModuleHeader";
import { SatelliteHourlyChart } from "@/components/charts6";

export const revalidate = 60;

function level(v: number) {
  return v >= 66 ? "High" : v >= 33 ? "Moderate" : "Low";
}

function ScoreCard({ label, value, hint, text, bar }: { label: string; value: number; hint: string; text: string; bar: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{label}</CardTitle>
        <span className={cn("text-[10px] uppercase font-semibold", text)}>{level(value)}</span>
      </CardHeader>
      <CardContent>
        <div className={cn("text-4xl font-bold tabular-nums", text)}>{value.toFixed(0)}<span className="text-base text-terminal-muted">/100</span></div>
        <div className="mt-2 h-2 rounded-full bg-terminal-border/50">
          <div className={cn("h-2 rounded-full", bar)} style={{ width: `${value}%` }} />
        </div>
        <p className="mt-2 text-[11px] text-terminal-muted">{hint}</p>
      </CardContent>
    </Card>
  );
}

export default async function SatellitePage() {
  const s = await api.satellite();
  if (!s?.available || !s.scores) {
    return (
      <div>
        <ModuleHeader title="Satellite Intelligence" subtitle="Module 4" />
        <div className="p-8 text-terminal-muted text-sm">Satellite service unavailable.</div>
      </div>
    );
  }
  const si = s.score_inputs!;

  return (
    <div>
      <ModuleHeader title="Satellite Intelligence" subtitle={`Module 4 · NASA imagery ${s.imagery_date} · scores from next-24h forecast`} />
      <DailyBrief />

      <div className="p-5 space-y-5">
        {/* Scores */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ScoreCard label="Cloud Intensity" value={s.scores.cloud_intensity}
            text="text-terminal-accent" bar="bg-terminal-accent" hint={`Mean cloud cover next 24h`} />
          <ScoreCard label="Rain Probability" value={s.scores.rain_probability}
            text="text-terminal-rain" bar="bg-terminal-rain" hint={`Peak ${si.max_rain_prob_24h}% · up to ${si.max_precip_mm_24h}mm/h`} />
          <ScoreCard label="Storm Risk" value={s.scores.storm_risk}
            text="text-terminal-warn" bar="bg-terminal-warn" hint={`Wind ${fmt(si.max_wind_kmh_24h, 0)}km/h · min pressure ${fmt(si.min_pressure_hpa_24h, 0)}hPa`} />
        </div>

        {/* Imagery */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {(s.images ?? []).map((img) => (
            <Card key={img.title}>
              <CardHeader><CardTitle>{img.title}</CardTitle></CardHeader>
              <CardContent>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={img.url} alt={img.title} loading="lazy"
                     className="w-full rounded-lg border border-terminal-border bg-terminal-bg" />
                <p className="mt-1.5 text-[11px] text-terminal-muted">{img.subtitle} · NASA GIBS · {s.imagery_date}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Hourly outlook */}
        <Card>
          <CardHeader><CardTitle>48-hour cloud / rain outlook</CardTitle></CardHeader>
          <CardContent>{s.hourly?.length ? <SatelliteHourlyChart data={s.hourly} /> : null}</CardContent>
        </Card>

        <p className="text-[11px] text-terminal-muted max-w-3xl">
          Imagery is live NASA GIBS (VIIRS true colour + GPM IMERG precipitation) over the Arabian Sea, India and
          Bay of Bengal — useful for spotting monsoon rain bands and developing systems. The three scores are
          derived transparently from the Open-Meteo hourly forecast for {s.location?.name}: cloud intensity = mean
          cloud cover, rain probability blends peak &amp; mean precip probability, and storm risk combines heavy-rain,
          high-wind and low-pressure factors over the next 24 hours.
        </p>
      </div>
    </div>
  );
}
