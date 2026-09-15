-- SAMCO CTO Hub v0.4 - Project document intake and scope integration.
-- This layer turns tender/project documents into a controlled CSI/SAM-CTO scope register.

create table if not exists public.project_documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  ingestion_id uuid not null,
  filename text not null,
  document_type text not null default 'unknown',
  storage_path text,
  sha256 text,
  pages integer not null default 0,
  char_count integer not null default 0,
  extraction_mode text,
  needs_ocr boolean not null default false,
  status text not null default 'processed',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists project_documents_project_idx on public.project_documents(project_id, ingestion_id);

create table if not exists public.project_scope_entries (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  ingestion_id uuid not null,
  scope_key text not null,
  csi_code text not null default '00 00 00',
  csi_title text,
  division text,
  selected_samco_code text references public.activities(master_code) on update cascade,
  mapping_status text not null default 'unmapped' check(mapping_status in ('unmapped','review_required','auto_mapped','approved','rejected')),
  mapping_confidence numeric not null default 0,
  quantity_by_unit jsonb not null default '{}'::jsonb,
  completeness jsonb not null default '{}'::jsonb,
  conflicts jsonb not null default '[]'::jsonb,
  payload jsonb not null default '{}'::jsonb,
  reviewed_by uuid references auth.users(id),
  reviewed_at timestamptz,
  updated_at timestamptz not null default now(),
  unique(project_id,ingestion_id,scope_key)
);
create index if not exists project_scope_entries_project_idx on public.project_scope_entries(project_id, mapping_status, csi_code);
create index if not exists project_scope_entries_samco_idx on public.project_scope_entries(selected_samco_code);

create table if not exists public.document_mapping_rules (
  id uuid primary key default gen_random_uuid(),
  rule_type text not null check(rule_type in ('document_keyword','boq_section_to_csi','symbol_to_csi','keyword_to_csi','contract_term')),
  match_value text not null,
  mapped_value text not null,
  enabled boolean not null default true,
  priority integer not null default 100,
  notes text,
  revision integer not null default 1,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id),
  unique(rule_type,match_value)
);

create table if not exists public.scope_review_actions (
  id bigint generated always as identity primary key,
  scope_entry_id uuid not null references public.project_scope_entries(id) on delete cascade,
  action text not null check(action in ('approve_mapping','change_mapping','reject_mapping','resolve_conflict','add_note')),
  before_value jsonb,
  after_value jsonb,
  note text,
  actor uuid references auth.users(id),
  created_at timestamptz not null default now()
);

alter table public.project_documents enable row level security;
alter table public.project_scope_entries enable row level security;
alter table public.document_mapping_rules enable row level security;
alter table public.scope_review_actions enable row level security;

create policy "project docs authenticated read" on public.project_documents for select to authenticated using(true);
create policy "project docs department write" on public.project_documents for all to authenticated using(public.current_app_role() in ('admin','technical','tender','planning','cost_control')) with check(public.current_app_role() in ('admin','technical','tender','planning','cost_control'));
create policy "scope authenticated read" on public.project_scope_entries for select to authenticated using(true);
create policy "scope department write" on public.project_scope_entries for all to authenticated using(public.current_app_role() in ('admin','technical','tender','planning','cost_control')) with check(public.current_app_role() in ('admin','technical','tender','planning','cost_control'));
create policy "mapping rules authenticated read" on public.document_mapping_rules for select to authenticated using(true);
create policy "mapping rules admin write" on public.document_mapping_rules for all to authenticated using(public.is_admin()) with check(public.is_admin());
create policy "scope actions authenticated read" on public.scope_review_actions for select to authenticated using(true);
create policy "scope actions department write" on public.scope_review_actions for insert to authenticated with check(public.current_app_role() in ('admin','technical','tender','planning','cost_control'));

-- Page access for the new front-door intake workspace.
insert into public.role_page_access(role,path,allowed) values
 ('top_management','/intake',true),
 ('tender','/intake',true),
 ('planning','/intake',true),
 ('cost_control','/intake',true),
 ('technical','/intake',true)
on conflict(role,path) do update set allowed=excluded.allowed;

create table if not exists public.project_scope_feeds (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  scope_entry_id uuid not null references public.project_scope_entries(id) on delete cascade,
  department text not null check(department in ('technical','tender','planning','cost_control')),
  status text not null default 'new' check(status in ('new','review','accepted','rejected','completed')),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(scope_entry_id,department)
);
alter table public.project_scope_feeds enable row level security;
create policy "scope feeds management read" on public.project_scope_feeds for select to authenticated using(
  public.is_management() or department=(select department from public.profiles where id=auth.uid())
);
create policy "scope feeds department write" on public.project_scope_feeds for all to authenticated using(
  public.is_admin() or department=(select department from public.profiles where id=auth.uid())
) with check(public.is_admin() or department=(select department from public.profiles where id=auth.uid()));
