create table public.sw_terms_acceptances (
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  version text not null check (version in ('sw-1')),
  accepted_at timestamptz not null default now(),
  primary key (owner_id, version)
);
create table public.sw_characters (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  slot smallint not null check (slot between 1 and 4),
  name text not null check (char_length(name) between 2 and 18 and name ~ '^[A-Za-z0-9ก-ฮะ-ฺเ-๎๐-๙]+$' and name ~ '[A-Za-zก-ฮ]'),
  weapon text not null check (weapon in ('jian','flute','tang','healer')),
  hair text not null check (hair in ('male','female')),
  unique (owner_id,slot)
);
create unique index sw_characters_name_unique on public.sw_characters (lower(name));
alter table public.sw_terms_acceptances enable row level security;
alter table public.sw_characters enable row level security;
revoke all on public.sw_terms_acceptances, public.sw_characters from public, anon, authenticated;
grant select on public.sw_terms_acceptances, public.sw_characters to authenticated;
grant insert(version) on public.sw_terms_acceptances to authenticated;
grant insert(slot, name, weapon, hair) on public.sw_characters to authenticated;
create policy sw_terms_read on public.sw_terms_acceptances for select to authenticated using (owner_id = (select auth.uid()));
create policy sw_terms_accept on public.sw_terms_acceptances for insert to authenticated with check (owner_id = (select auth.uid()) and version = 'sw-1');
create policy sw_roster_read on public.sw_characters for select to authenticated using (owner_id = (select auth.uid()) and exists (select 1 from public.sw_terms_acceptances where owner_id = (select auth.uid()) and version='sw-1'));
create policy sw_roster_create on public.sw_characters for insert to authenticated with check (owner_id = (select auth.uid()) and exists (select 1 from public.sw_terms_acceptances where owner_id = (select auth.uid()) and version='sw-1'));
