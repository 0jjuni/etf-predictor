-- Supabase schema. Run once in the SQL editor.

create table if not exists predictions (
    id              bigserial primary key,
    target_date     date        not null,
    symbol          text        not null,
    name            text        not null,
    probability     double precision not null,
    rise_threshold  double precision not null,
    created_at      timestamptz not null default now(),
    unique (target_date, symbol)
);

-- Outcome columns are filled in by a later run once close[target_date] is known.
-- A null outcome means the prediction is still pending resolution.
alter table predictions
    add column if not exists actual_close_prev   double precision,
    add column if not exists actual_close_target double precision,
    add column if not exists actual_change       double precision,
    add column if not exists outcome             boolean,
    add column if not exists resolved_at         timestamptz;

-- news_json: best-effort recent news for the recommended ETF, populated at
-- training time. Schema: [{title, url, source, published}, ...] or null.
alter table predictions
    add column if not exists news_json jsonb;

create index if not exists predictions_outcome_pending_idx
    on predictions (target_date) where outcome is null;

create index if not exists predictions_target_date_idx
    on predictions (target_date desc);

create index if not exists predictions_symbol_idx
    on predictions (symbol);

-- RLS: anon may read, only service-role writes.
alter table predictions enable row level security;

drop policy if exists "predictions_read_anon" on predictions;
create policy "predictions_read_anon"
    on predictions for select
    to anon
    using (true);

-- One row per training run, keyed by target_date. metrics_json holds the
-- threshold curve as a JSON array: [{threshold, precision, recall, f1,
-- support_total, support_positive}, ...]
create table if not exists model_metrics (
    target_date    date primary key,
    test_size      int not null,
    positive_rate  double precision not null,
    metrics_json   jsonb not null,
    created_at     timestamptz not null default now()
);

-- fallback_picks_json: top-N highest-probability ETFs when no regular pick
-- crossed PROB_THRESHOLD. Display-only; never feeds the predictions table or
-- empirical-precision computation. Schema:
-- [{symbol, name, probability, precision_band, fallback_threshold, news_json}, ...]
alter table model_metrics
    add column if not exists fallback_picks_json jsonb;

alter table model_metrics enable row level security;

drop policy if exists "model_metrics_read_anon" on model_metrics;
create policy "model_metrics_read_anon"
    on model_metrics for select
    to anon
    using (true);

-- Table-level privileges. RLS only kicks in after the role passes the GRANT check;
-- we disabled "automatically expose new tables" so we grant explicitly.
grant usage on schema public to anon;
grant select on public.predictions to anon;
grant select on public.model_metrics to anon;

-- daily_probabilities: per-day probability for EVERY ETF in the universe.
-- Used by the "종목 둘러보기" tab so visitors can look up any ETF's current
-- model probability, not just the ones above the recommendation threshold.
create table if not exists daily_probabilities (
    target_date date not null,
    symbol      text not null,
    name        text not null,
    probability double precision not null,
    primary key (target_date, symbol)
);

create index if not exists daily_prob_target_idx
    on daily_probabilities (target_date desc);
create index if not exists daily_prob_symbol_idx
    on daily_probabilities (symbol);

alter table daily_probabilities enable row level security;
drop policy if exists "daily_prob_read_anon" on daily_probabilities;
create policy "daily_prob_read_anon"
    on daily_probabilities for select
    to anon
    using (true);

-- service_role is used by the training job (cron) and the local backfill script
-- to write predictions and metrics. With auto-expose disabled, service_role
-- also needs explicit grants on each new table + sequences.
grant usage on schema public to service_role;
grant select, insert, update on public.predictions to service_role;
grant select, insert, update on public.model_metrics to service_role;
grant select, insert, update on public.daily_probabilities to service_role;
grant select on public.daily_probabilities to anon;
grant usage, select on all sequences in schema public to service_role;
