-- SAMCO CTO Hub - Event-driven orchestration extension

-- Align pre-existing installations with the 9-digit SAM-CTO corporate identity used by the Excel/JSON pipeline.
do $$ begin
  alter table public.activities drop constraint if exists activities_master_code_check;
  alter table public.activities add constraint activities_master_code_check check(master_code ~ '^SAM-CTO-[0-9]{9}$');
exception when others then
  raise notice 'Could not refresh activities master-code constraint: %', sqlerrm;
end $$;

-- Core business writes remain synchronous in PostgreSQL. Async work is published through a transactional outbox.

create table if not exists public.outbox_events (
  id bigint generated always as identity primary key,
  event_type text not null,
  aggregate_type text not null,
  aggregate_key text not null,
  payload jsonb not null default '{}'::jsonb,
  actor_label text,
  idempotency_key text,
  status text not null default 'pending' check(status in ('pending','published','processing','completed','failed')),
  attempts integer not null default 0,
  available_at timestamptz not null default now(),
  published_at timestamptz,
  completed_at timestamptz,
  last_error text,
  created_at timestamptz not null default now()
);
create unique index if not exists outbox_idempotency_unique on public.outbox_events(idempotency_key) where idempotency_key is not null;
create index if not exists outbox_pending_idx on public.outbox_events(status, available_at, id);

create table if not exists public.background_jobs (
  id uuid primary key default gen_random_uuid(),
  event_id bigint references public.outbox_events(id) on delete set null,
  job_type text not null,
  department text,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check(status in ('queued','running','completed','failed','cancelled')),
  result jsonb,
  error text,
  attempts integer not null default 0,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists background_jobs_status_idx on public.background_jobs(status, created_at);
create unique index if not exists background_jobs_event_unique on public.background_jobs(event_id) where event_id is not null;

create table if not exists public.planning_duration_rules (
  master_code text primary key references public.activities(master_code) on update cascade on delete cascade,
  duration_method text not null default 'PRODUCTIVITY' check(duration_method in ('PRODUCTIVITY','FIXED','CONTRACTUAL','LEAD_TIME','QUANTITY_RATIO','CALENDAR_PERIOD','MANUAL_CONTROLLED','ENGINEERING_REVIEW')),
  corporate_productivity numeric,
  corporate_crews numeric default 1,
  min_duration_days numeric,
  typical_duration_days numeric,
  max_duration_days numeric,
  fixed_duration_days numeric,
  calendar_code text,
  predecessor_rule jsonb not null default '[]'::jsonb,
  successor_rule jsonb not null default '[]'::jsonb,
  engineering_prerequisites jsonb not null default '[]'::jsonb,
  procurement_prerequisites jsonb not null default '[]'::jsonb,
  material_required_on_site_days integer,
  source jsonb not null default '{}'::jsonb,
  revision integer not null default 1,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

create table if not exists public.integration_endpoints (
  key text primary key,
  provider text not null,
  enabled boolean not null default false,
  config jsonb not null default '{}'::jsonb,
  last_health_status text,
  last_health_at timestamptz,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

alter table public.outbox_events enable row level security;
alter table public.background_jobs enable row level security;
alter table public.planning_duration_rules enable row level security;
alter table public.integration_endpoints enable row level security;

create policy "management outbox read" on public.outbox_events for select to authenticated using(public.is_management());
create policy "admin outbox manage" on public.outbox_events for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "management jobs read" on public.background_jobs for select to authenticated using(public.is_management());
create policy "admin jobs manage" on public.background_jobs for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "planning duration read" on public.planning_duration_rules for select to authenticated using(true);
create policy "planning duration write" on public.planning_duration_rules for all to authenticated using(public.current_app_role() in ('admin','planning')) with check(public.current_app_role() in ('admin','planning'));
create policy "integration management read" on public.integration_endpoints for select to authenticated using(public.is_management());
create policy "integration admin write" on public.integration_endpoints for all to authenticated using(public.is_admin()) with check(public.is_admin());

-- Helper used by workers to atomically claim pending outbox work.
create or replace function public.claim_outbox_batch(batch_size integer default 20)
returns setof public.outbox_events
language plpgsql security definer set search_path=public as $$
begin
  return query
  with claimed as (
    select id from public.outbox_events
    where status='pending' and available_at<=now()
    order by id
    for update skip locked
    limit greatest(batch_size,1)
  )
  update public.outbox_events o
     set status='processing', attempts=o.attempts+1
    from claimed c
   where o.id=c.id
  returning o.*;
end $$;
