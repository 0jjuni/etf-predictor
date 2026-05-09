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
