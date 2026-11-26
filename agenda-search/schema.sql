-- Apply to the isolated demo Supabase project.
create table public.resident_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade default auth.uid(),
  topics text[] not null default '{}',
  district smallint check (district between 1 and 13),
  school text check (length(school) <= 150)
);
alter table public.resident_preferences enable row level security;
revoke all on public.resident_preferences from public, anon, authenticated;
grant select, insert, update, delete on public.resident_preferences to authenticated;
create policy own_preferences on public.resident_preferences
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create table public.agenda_imports (
  id uuid primary key default gen_random_uuid(),
  jurisdiction text not null,
  body text not null,
  meeting_date date not null,
  pdf_path text not null,
  simulated boolean not null default false,
  status text not null default 'draft' check (status in ('draft','approved','superseded'))
);
create unique index current_agenda on public.agenda_imports(jurisdiction, body, meeting_date, simulated)
  where status = 'approved';
create table public.agenda_search_items (
  id uuid primary key default gen_random_uuid(),
  agenda_id uuid not null references public.agenda_imports(id) on delete cascade,
  item_number text not null,
  file_number text,
  page_start integer not null check (page_start >= 1),
  page_end integer not null check (page_end >= page_start),
  original_text text not null,
  description text not null,
  evidence jsonb not null default '[]' check (jsonb_typeof(evidence) = 'array'),
  unique (agenda_id, item_number)
);
alter table public.agenda_imports enable row level security;
alter table public.agenda_search_items enable row level security;
revoke all on public.agenda_imports, public.agenda_search_items from public, anon, authenticated;
grant select on public.agenda_imports, public.agenda_search_items to anon, authenticated;
create policy published_imports on public.agenda_imports for select using (status = 'approved');
create policy published_items on public.agenda_search_items for select using (
  exists (select 1 from public.agenda_imports a where a.id = agenda_id and a.status = 'approved')
);
