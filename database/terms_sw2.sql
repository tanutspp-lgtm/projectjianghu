alter table public.sw_terms_acceptances drop constraint sw_terms_acceptances_version_check,
  add constraint sw_terms_acceptances_version_check check (version in ('sw-1','sw-2'));
alter policy sw_terms_accept on public.sw_terms_acceptances with check (owner_id = (select auth.uid()) and version='sw-2');
alter policy sw_roster_read on public.sw_characters using (owner_id = (select auth.uid()) and exists (select 1 from public.sw_terms_acceptances where owner_id = (select auth.uid()) and version='sw-2'));
alter policy sw_roster_create on public.sw_characters with check (owner_id = (select auth.uid()) and exists (select 1 from public.sw_terms_acceptances where owner_id = (select auth.uid()) and version='sw-2'));
