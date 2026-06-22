// Typed API client for the RAINMUMBAI Terminal backend.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";

async function get<T>(path: string): Promise<T | null> {
  try {
    // 60s ISR-aligned data cache: multiple pages share a single backend hit
    // inside the window, and a stale render serves instantly while Vercel
    // revalidates in the background.
    const res = await fetch(`${BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export interface Summary {
  available: boolean;
  reason?: string;
  as_of?: string;
  today_rainfall_mm?: number;
  weekly_rainfall_mm?: number;
  monthly_rainfall_mm?: number;
  seasonal_rainfall_mm?: number;
  historical_avg_seasonal_mm?: number;
  deviation_pct?: number | null;
  monsoon_progress?: number;
  season_start?: string;
  temp_mean_c?: number | null;
  humidity_pct?: number | null;
  pressure_hpa?: number | null;
  wind_kmh?: number | null;
}

export interface Meta {
  location: { code: string; name: string; lat: number; lon: number } | null;
  coverage: { start: string; end: string; days: number; years: number } | null;
  raw_sources?: Record<string, number>;
}

export interface DailyPoint { date: string; rainfall_mm: number | null; roll7: number | null; roll30: number | null; }
export interface MonthlyPoint { month: string; rainfall_mm: number; }
export interface WeeklyPoint { week: string; rainfall_mm: number; }
export interface CumPoint { date: string; actual: number; climatology: number; p10: number; p90: number; }
export interface DriverVal { value: number; as_of: string }
export type Drivers = Record<string, DriverVal | null>;

// ---- Phase 2 ----
export interface Probability {
  available: boolean;
  as_of?: string;
  normal_mm?: number;
  expected_mm?: number;
  posterior_sd_mm?: number;
  probabilities?: Record<string, number>;
  method?: string;
  n_years?: number;
  curve?: { x: number; pdf: number }[];
  thresholds?: Record<string, number | null>;
}

export interface FairValue {
  available: boolean;
  as_of?: string;
  fair_value?: number;
  expected_settle?: number;
  market_price?: number | null;
  mispricing?: number | null;
  has_market_data?: boolean;
  inputs?: Record<string, unknown>;
  payoff_curve?: { index: number; payoff: number }[];
}

export interface SignalComponent {
  key: string; weight: number; score: number; label: string; detail: string; contribution: number;
}
export interface Signal {
  available: boolean;
  as_of?: string;
  signal?: string;
  score?: number;
  confidence?: number;
  components?: SignalComponent[];
}

export interface SignalLogEntry {
  logged_at: string;
  as_of: string;
  signal: string;
  prev_signal: string | null;
  score: number | null;
  confidence: number | null;
  event_type: "first" | "change" | "same";
}
export interface SignalHistory {
  available: boolean;
  count: number;
  entries: SignalLogEntry[];
}

export interface Factor { label: string; detail: string; contribution: number; }
export interface Brief {
  available: boolean;
  as_of?: string;
  symbol?: string;
  rainfall_forecast?: Record<string, number>;
  confidence_score?: number;
  revision_probability?: number | null;
  expected_season_mm?: number;
  fair_value?: number;
  signal?: string;
  bullish_factors?: Factor[];
  bearish_factors?: Factor[];
}

export interface ContractSpec {
  available: boolean;
  symbol?: string; description?: string;
  accrual_start?: string; accrual_end?: string;
  payoff_type?: string; payoff_params?: Record<string, unknown>; lot_size?: number;
}

// ---- Phase 3 ----
export interface LeaderboardModel {
  model: string; rmse: number | null; mae: number | null;
  hit_rate: number | null; directional_acc: number | null; is_champion: boolean;
}
export interface Leaderboard {
  available: boolean;
  horizons?: { horizon: string; cv_folds: number | null; models: LeaderboardModel[] }[];
}
export interface MLForecast { horizon: string; model: string; point_mm: number; p10_mm: number; p90_mm: number; confidence: number; }
export interface MLForecasts { available: boolean; issued_date?: string; forecasts?: MLForecast[]; }

export interface Revision {
  available: boolean;
  as_of?: string;
  display_season?: number | null;
  prob_revise_up?: number;
  prob_revise_down?: number;
  expected_revision_mm?: number;
  expected_market_impact?: number;
  confidence?: number;
  model?: { test_accuracy: number | null; n_samples: number | null; base_rate_up: number | null; size_rmse: number | null };
  forecast_series?: { date: string; expected_season_mm: number }[];
  revisions?: { date: string; revision_mm: number; direction: string }[];
}

// ---- Phase 4 ----
export interface ImpactRow { state: string; n_years: number; mean_season_mm: number; deviation_pct: number | null; }
export interface DriverPanel {
  current: number | null; as_of: string | null; state?: string | null;
  correlation: number | null; impact: ImpactRow[]; note: string;
}
export interface MJOPanel {
  current_phase: number | null; current_amp: number | null; as_of: string | null;
  phase_rainfall: { phase: number; mean_daily_mm: number; n: number }[];
  baseline_daily_mm: number; note: string;
}
export interface Monsoon {
  available: boolean;
  normal_season_mm?: number;
  enso?: DriverPanel; iod?: DriverPanel; mjo?: MJOPanel;
  coverage_years?: [number, number];
}

export interface Scenario {
  code: string; label: string; n_years: number;
  projected_season_mm: number | null; deviation_pct: number | null; probability: number;
  distribution?: { min: number; p25: number; median: number; p75: number; max: number };
  years?: number[]; note: string;
}
export interface Scenarios {
  available: boolean; normal_season_mm?: number; n_total_years?: number; scenarios?: Scenario[];
}

// ---- Phase 5 ----
export interface SeasonExtreme { year: number; mm: number; deviation_pct: number | null; }
export interface Research {
  available: boolean;
  coverage?: { start: string; end: string; n_days: number; n_seasons: number };
  normal_season_mm?: number;
  correlation?: { labels: string[]; matrix: number[][] };
  leadlag?: { driver: string; series: { lag: number; corr: number | null }[] }[];
  seasonality?: { month: number; mean_mm: number; std_mm: number }[];
  extremes?: {
    wettest_days: { date: string; mm: number }[];
    wettest_seasons: SeasonExtreme[];
    driest_seasons: SeasonExtreme[];
  };
}

// ---- Module 4 ----
export interface Satellite {
  available: boolean;
  imagery_date?: string;
  location?: { name: string; lat: number; lon: number };
  scores?: { cloud_intensity: number; rain_probability: number; storm_risk: number };
  score_inputs?: { max_rain_prob_24h: number; max_precip_mm_24h: number; max_wind_kmh_24h: number; min_pressure_hpa_24h: number };
  images?: { title: string; subtitle: string; url: string }[];
  hourly?: { time: string; date: string; cloud: number | null; rain_prob: number | null; precip: number | null }[];
}

// ---- Modules 11 / 12 ----
export interface AiStatus { provider: string; model: string; available: boolean; installed_models?: string[]; error?: string; }
export interface CopilotSuggested { suggested: string[]; engine: AiStatus; }
export interface AltData {
  available: boolean;
  as_of?: string;
  summary?: string;
  sentiment?: number;
  bullish?: string[];
  bearish?: string[];
  risks?: string[];
  headlines?: { title: string; url: string; published: string; query: string }[];
}

export const api = {
  summary: () => get<Summary>("/weather/summary"),
  meta: () => get<Meta>("/meta"),
  daily: (days = 120) => get<{ series: DailyPoint[] }>(`/weather/daily?days=${days}`),
  weekly: (weeks = 52) => get<{ series: WeeklyPoint[] }>(`/weather/weekly?weeks=${weeks}`),
  monthly: (months = 60) => get<{ series: MonthlyPoint[] }>(`/weather/monthly?months=${months}`),
  cumulative: () => get<{ season_start: string; series: CumPoint[] }>("/weather/cumulative"),
  drivers: () => get<Drivers>("/weather/drivers"),
  // Phase 2
  probability: () => get<Probability>("/probability"),
  fairValue: () => get<FairValue>("/derivative/fair-value"),
  spec: () => get<ContractSpec>("/derivative/spec"),
  signal: () => get<Signal>("/signal"),
  signalHistory: (limit = 100) => get<SignalHistory>(`/signal/history?limit=${limit}`),
  brief: () => get<Brief>("/brief"),
  // Phase 3
  leaderboard: () => get<Leaderboard>("/ml/leaderboard"),
  mlForecasts: () => get<MLForecasts>("/ml/forecasts"),
  revision: () => get<Revision>("/revision"),
  // Phase 4
  monsoon: () => get<Monsoon>("/monsoon"),
  scenarios: () => get<Scenarios>("/scenarios"),
  // Phase 5
  research: () => get<Research>("/research"),
  // Module 4
  satellite: () => get<Satellite>("/satellite"),
  // Modules 11 / 12
  aiStatus: () => get<AiStatus>("/ai/status"),
  copilotSuggested: () => get<CopilotSuggested>("/copilot/suggested"),
  altdata: () => get<AltData>("/altdata"),
};

// Base used by Next route handlers to proxy interactive POSTs to the backend.
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
