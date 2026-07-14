-- Persistent, append-only Voxplot analysis history.
-- Raw recordings are deliberately not stored; only the calculated metrics and
-- recording metadata are retained. The Streamlit server alone uses the
-- service-role-backed secret API key. Browser roles get no table privileges.

create extension if not exists pgcrypto;

create table if not exists public.voice_sessions (
    id uuid primary key default gen_random_uuid(),
    record_hash text not null unique check (record_hash ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz not null,
    sample_meta jsonb not null,
    parameters jsonb not null,
    indices jsonb not null,
    norms jsonb not null,
    created_at timestamptz not null default now()
);

create index if not exists voice_sessions_recorded_at_idx
    on public.voice_sessions (recorded_at asc, id asc);

alter table public.voice_sessions enable row level security;

revoke all on table public.voice_sessions from anon, authenticated;
grant usage on schema public to service_role;
grant select, insert on table public.voice_sessions to service_role;
