-- SAMCO CTO Project Standards & Controls Hub
-- Production schema for Supabase/Postgres.
create extension if not exists pgcrypto;

do $$ begin
  create type public.app_role as enum ('admin','top_management','tender','planning','cost_control','technical','viewer');
exception when duplicate_object then null; end $$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default 'User',
  role public.app_role not null default 'viewer',
  department text not null default 'cto',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.current_app_role() returns public.app_role
language sql stable security definer set search_path=public as $$
  select coalesce((select role from public.profiles where id=auth.uid()),'viewer'::public.app_role)
$$;
create or replace function public.is_admin() returns boolean language sql stable security definer set search_path=public as $$select public.current_app_role()='admin'::public.app_role$$;
create or replace function public.is_management() returns boolean language sql stable security definer set search_path=public as $$select public.current_app_role() in ('admin'::public.app_role,'top_management'::public.app_role)$$;

create table if not exists public.role_page_access (
  role public.app_role not null,
  path text not null,
  allowed boolean not null default true,
  updated_at timestamptz not null default now(),
  primary key(role,path)
);

create table if not exists public.app_settings (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

create table if not exists public.ui_nodes (
  key text primary key,
  text_override text,
  style jsonb not null default '{}'::jsonb,
  hidden boolean not null default false,
  roles public.app_role[],
  revision integer not null default 1,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

create table if not exists public.activities (
  master_code text primary key check(master_code ~ '^SAM-CTO-[0-9]{9}$'),
  title text not null,
  legacy_activity_code text,
  legacy_division text,
  legacy_subdivision text,
  csi_2026_mapping text,
  csi_migration_status text,
  discipline text,
  department_owner text,
  uom text,
  crew_type text,
  daily_production numeric,
  crew_hours_per_day numeric,
  crew_hours_per_unit numeric,
  status text not null default 'Draft',
  revision integer not null default 1,
  source jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id)
);

create table if not exists public.resources (
  id text primary key,
  source_resource_code text,
  category text,
  description text not null,
  uom text,
  source_main_code text,
  extension text,
  rate numeric,
  status text not null default 'Draft',
  source jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.material_prices (
  code text primary key,
  category text,
  description text not null,
  unit text,
  avg_price numeric,
  low_price numeric,
  high_price numeric,
  confidence text,
  source text,
  effective_date date,
  updated_at timestamptz not null default now()
);

create table if not exists public.rate_register (
  code text primary key,
  category text,
  name text not null,
  unit text,
  low_rate numeric,
  high_rate numeric,
  avg_rate numeric,
  source text,
  effective_date date,
  updated_at timestamptz not null default now()
);

create table if not exists public.commercial_assumptions (
  key text primary key,
  value jsonb not null,
  effective_date date not null default current_date,
  revision integer not null default 1,
  updated_at timestamptz not null default now()
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  project_code text unique,
  project_name text not null,
  sector text,
  client_name text,
  contractor text default 'SAMCO',
  currency text default 'EGP',
  contract_value numeric,
  bac numeric,
  planned_start date,
  planned_finish date,
  actual_progress numeric,
  planned_progress numeric,
  status text,
  source jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.project_boq_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  scope text not null,
  item text,
  section text,
  description text not null,
  unit text,
  quantity numeric default 0,
  material_code text,
  material_unit_price numeric default 0,
  wastage numeric default 0,
  labor_cost_per_unit numeric default 0,
  equipment_cost_per_unit numeric default 0,
  subcontractor_rate_per_unit numeric default 0,
  updated_at timestamptz not null default now()
);

create table if not exists public.planning_working (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  master_code text references public.activities(master_code),
  quantity numeric default 0,
  crews numeric default 1,
  daily_production numeric,
  predecessor text,
  relationship text default 'FS',
  lag numeric default 0,
  calendar_code text,
  wbs_code text,
  project_override_reason text,
  updated_at timestamptz not null default now()
);

create table if not exists public.technical_working (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  master_code text references public.activities(master_code),
  method text,
  specification text,
  inspection text,
  interfaces text,
  evidence text,
  updated_at timestamptz not null default now(),
  unique(project_id,master_code)
);

create table if not exists public.evm_periods (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  data_date date not null,
  bac numeric,
  pv numeric,
  ev numeric,
  ac numeric,
  created_at timestamptz not null default now(),
  unique(project_id,data_date)
);

create table if not exists public.deadlines (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  target_at timestamptz not null,
  enabled boolean not null default true,
  alarm_minutes_before integer[] not null default '{1440,60,15}',
  alarm_tone text not null default 'chime',
  custom_sound_url text,
  created_by uuid references auth.users(id),
  updated_at timestamptz not null default now()
);

create table if not exists public.report_templates (
  id uuid primary key,
  department text not null,
  format text not null check(format in ('html','docx','xlsx')),
  name text not null,
  storage_path text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  created_by uuid references auth.users(id)
);

create table if not exists public.audit_log (
  id bigint generated always as identity primary key,
  actor uuid references auth.users(id),
  action text not null,
  entity_type text,
  entity_key text,
  before_value jsonb,
  after_value jsonb,
  created_at timestamptz not null default now()
);

-- Initial page matrix. Admin is implicitly unrestricted in UI and RLS.
insert into public.role_page_access(role,path,allowed) values
 ('top_management','/',true),('top_management','/standards',true),('top_management','/control-center',true),('top_management','/outputs',true),
 ('tender','/',true),('tender','/standards',true),('tender','/tender',true),('tender','/outputs',true),
 ('planning','/',true),('planning','/standards',true),('planning','/planning',true),('planning','/outputs',true),
 ('cost_control','/',true),('cost_control','/standards',true),('cost_control','/cost-control',true),('cost_control','/outputs',true),
 ('technical','/',true),('technical','/standards',true),('technical','/technical',true),('technical','/outputs',true),
 ('viewer','/',true)
on conflict(role,path) do nothing;

-- RLS
alter table public.profiles enable row level security;
alter table public.role_page_access enable row level security;
alter table public.app_settings enable row level security;
alter table public.ui_nodes enable row level security;
alter table public.activities enable row level security;
alter table public.resources enable row level security;
alter table public.material_prices enable row level security;
alter table public.rate_register enable row level security;
alter table public.commercial_assumptions enable row level security;
alter table public.projects enable row level security;
alter table public.project_boq_items enable row level security;
alter table public.planning_working enable row level security;
alter table public.technical_working enable row level security;
alter table public.evm_periods enable row level security;
alter table public.deadlines enable row level security;
alter table public.report_templates enable row level security;
alter table public.audit_log enable row level security;

create policy "profile self read" on public.profiles for select to authenticated using(id=auth.uid() or public.is_management());
create policy "admin profiles" on public.profiles for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "access authenticated read" on public.role_page_access for select to authenticated using(true);
create policy "access admin write" on public.role_page_access for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "settings authenticated read" on public.app_settings for select to authenticated using(true);
create policy "settings admin write" on public.app_settings for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "ui authenticated read" on public.ui_nodes for select to authenticated using(true);
create policy "ui admin write" on public.ui_nodes for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "masters authenticated read" on public.activities for select to authenticated using(true);
create policy "activities admin write" on public.activities for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "resources authenticated read" on public.resources for select to authenticated using(true);
create policy "resources admin write" on public.resources for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "material authenticated read" on public.material_prices for select to authenticated using(true);
create policy "material admin write" on public.material_prices for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "rates authenticated read" on public.rate_register for select to authenticated using(true);
create policy "rates admin write" on public.rate_register for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "assumptions authenticated read" on public.commercial_assumptions for select to authenticated using(true);
create policy "assumptions admin write" on public.commercial_assumptions for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "projects management read" on public.projects for select to authenticated using(public.is_management() or public.current_app_role() in ('tender','planning','cost_control','technical'));
create policy "projects admin write" on public.projects for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "boq tender readwrite" on public.project_boq_items for all to authenticated using(public.current_app_role() in ('admin','tender','top_management')) with check(public.current_app_role() in ('admin','tender'));
create policy "planning planning readwrite" on public.planning_working for all to authenticated using(public.current_app_role() in ('admin','planning','top_management')) with check(public.current_app_role() in ('admin','planning'));
create policy "technical technical readwrite" on public.technical_working for all to authenticated using(public.current_app_role() in ('admin','technical','top_management')) with check(public.current_app_role() in ('admin','technical'));
create policy "evm cost readwrite" on public.evm_periods for all to authenticated using(public.current_app_role() in ('admin','cost_control','top_management')) with check(public.current_app_role() in ('admin','cost_control'));
create policy "deadlines authenticated read" on public.deadlines for select to authenticated using(true);
create policy "deadlines admin write" on public.deadlines for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "templates authenticated read" on public.report_templates for select to authenticated using(true);
create policy "templates admin write" on public.report_templates for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "audit management read" on public.audit_log for select to authenticated using(public.is_management());
create policy "audit admin insert" on public.audit_log for insert to authenticated with check(public.is_admin());

-- Storage buckets.
insert into storage.buckets(id,name,public) values ('templates','templates',false),('media','media',true),('brand','brand',true) on conflict(id) do nothing;
create policy "templates authenticated read" on storage.objects for select to authenticated using(bucket_id='templates');
create policy "templates admin write" on storage.objects for all to authenticated using(bucket_id='templates' and public.is_admin()) with check(bucket_id='templates' and public.is_admin());
create policy "media authenticated read" on storage.objects for select to authenticated using(bucket_id='media');
create policy "media admin write" on storage.objects for all to authenticated using(bucket_id='media' and public.is_admin()) with check(bucket_id='media' and public.is_admin());
create policy "brand authenticated read" on storage.objects for select to authenticated using(bucket_id='brand');
create policy "brand admin write" on storage.objects for all to authenticated using(bucket_id='brand' and public.is_admin()) with check(bucket_id='brand' and public.is_admin());

-- Realtime authorization for private Presence/Broadcast channels. Authenticated users may read/send;
-- page/data permissions remain governed by application roles and table RLS.
alter table realtime.messages enable row level security;
do $$ begin
 create policy "authenticated realtime receive" on realtime.messages for select to authenticated using(true);
exception when duplicate_object then null; end $$;
do $$ begin
 create policy "authenticated realtime send" on realtime.messages for insert to authenticated with check(true);
exception when duplicate_object then null; end $$;

-- Department working-state settings used by the prototype UI while the normalized project tables
-- are being connected page-by-page. Corporate data:* keys remain admin-only.
create policy "department working settings insert" on public.app_settings for insert to authenticated
with check(
 public.is_admin() or
 (public.current_app_role()='tender' and key like 'work:tender:%') or
 (public.current_app_role()='planning' and key like 'work:planning:%') or
 (public.current_app_role()='cost_control' and key like 'work:cost_control:%') or
 (public.current_app_role()='technical' and key like 'work:technical:%')
);
create policy "department working settings update" on public.app_settings for update to authenticated
using(
 public.is_admin() or
 (public.current_app_role()='tender' and key like 'work:tender:%') or
 (public.current_app_role()='planning' and key like 'work:planning:%') or
 (public.current_app_role()='cost_control' and key like 'work:cost_control:%') or
 (public.current_app_role()='technical' and key like 'work:technical:%')
)
with check(
 public.is_admin() or
 (public.current_app_role()='tender' and key like 'work:tender:%') or
 (public.current_app_role()='planning' and key like 'work:planning:%') or
 (public.current_app_role()='cost_control' and key like 'work:cost_control:%') or
 (public.current_app_role()='technical' and key like 'work:technical:%')
);
