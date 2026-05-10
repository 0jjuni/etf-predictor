import { supabase } from "./supabase";
import type {
  DailyProbability,
  ModelMetrics,
  Prediction,
} from "./types";

/** Picks for the most recent training run (may be empty if nothing crossed 0.70). */
export async function fetchLatestPicks(): Promise<{
  targetDate: string | null;
  picks: Prediction[];
}> {
  const latest = await supabase
    .from("model_metrics")
    .select("target_date")
    .order("target_date", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!latest.data) return { targetDate: null, picks: [] };
  const targetDate = latest.data.target_date as string;

  const rows = await supabase
    .from("predictions")
    .select("*")
    .eq("target_date", targetDate)
    .order("probability", { ascending: false });

  return { targetDate, picks: (rows.data ?? []) as Prediction[] };
}

export async function fetchLatestModelMetrics(): Promise<ModelMetrics | null> {
  const r = await supabase
    .from("model_metrics")
    .select("*")
    .order("target_date", { ascending: false })
    .limit(1)
    .maybeSingle();
  return (r.data ?? null) as ModelMetrics | null;
}

export async function fetchResolvedHistory(limit = 500): Promise<Prediction[]> {
  const r = await supabase
    .from("predictions")
    .select("*")
    .not("outcome", "is", null)
    .order("target_date", { ascending: true })
    .limit(limit);
  return (r.data ?? []) as Prediction[];
}

export async function fetchUniverseLatest(): Promise<{
  targetDate: string | null;
  rows: DailyProbability[];
}> {
  const latest = await supabase
    .from("daily_probabilities")
    .select("target_date")
    .order("target_date", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!latest.data) return { targetDate: null, rows: [] };
  const targetDate = latest.data.target_date as string;
  const r = await supabase
    .from("daily_probabilities")
    .select("symbol,name,probability")
    .eq("target_date", targetDate)
    .order("probability", { ascending: false });
  return {
    targetDate,
    rows: ((r.data ?? []) as DailyProbability[]).map((row) => ({
      ...row,
      target_date: targetDate,
    })),
  };
}

export async function fetchProbabilityForSymbol(
  symbol: string,
): Promise<DailyProbability | null> {
  const r = await supabase
    .from("daily_probabilities")
    .select("*")
    .eq("symbol", symbol)
    .order("target_date", { ascending: false })
    .limit(1)
    .maybeSingle();
  return (r.data ?? null) as DailyProbability | null;
}
