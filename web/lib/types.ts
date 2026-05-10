// Mirrors the Supabase schema in db/schema.sql.

export interface Prediction {
  id: number;
  target_date: string; // YYYY-MM-DD
  symbol: string;
  name: string;
  probability: number; // 0..1
  rise_threshold: number; // e.g. 1.025
  created_at: string;
  // Filled in once close[target_date] becomes known.
  actual_close_prev: number | null;
  actual_close_target: number | null;
  actual_change: number | null; // (target/prev - 1)
  outcome: boolean | null; // true if actual_change >= rise_threshold - 1
  resolved_at: string | null;
  news_json: Article[] | null;
}

export interface Article {
  title: string;
  url: string;
  source: string;
  published: string;
}

export interface ThresholdRow {
  threshold: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  support_total: number;
  support_positive: number;
}

export interface FallbackPick {
  symbol: string;
  name: string;
  probability: number;
  precision_band: number | null;
  fallback_threshold: number;
  news_json?: Article[];
}

export interface ModelMetrics {
  target_date: string;
  test_size: number;
  positive_rate: number;
  metrics_json: ThresholdRow[];
  fallback_picks_json: FallbackPick[] | null;
  created_at: string;
}

export interface DailyProbability {
  target_date: string;
  symbol: string;
  name: string;
  probability: number;
}
