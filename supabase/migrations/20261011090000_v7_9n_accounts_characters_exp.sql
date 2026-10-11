-- PROJECT JIANGHU v7.9N
-- Additive migration only. Existing exp_v1 balance tables remain read-only.

create table if not exists public.characters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(btrim(name)) between 2 and 24),
  avatar text not null check (
    avatar ~ '^(male|female)_hair_(01|02|03)_(black|white|brown|red|gold)$'
  ),
  level smallint not null default 1 check (level between 1 and 60),
  total_exp bigint not null default 0 check (total_exp >= 0),
  balance_version text not null default 'exp_v1',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint characters_one_per_account unique (user_id),
  constraint characters_balance_version_fk foreign key (balance_version)
    references public.game_balance_versions(balance_version)
);

create index if not exists characters_user_id_idx on public.characters(user_id);

create table if not exists public.character_exp_ledger (
  reward_event_id text not null,
  character_id uuid not null references public.characters(id) on delete cascade,
  amount bigint not null check (amount >= 0),
  created_at timestamptz not null default now(),
  primary key (reward_event_id, character_id)
);

create index if not exists character_exp_ledger_character_id_idx
  on public.character_exp_ledger(character_id);

alter table public.characters enable row level security;
alter table public.character_exp_ledger enable row level security;

revoke all on table public.characters from anon, authenticated;
revoke all on table public.character_exp_ledger from anon, authenticated;
grant select on table public.characters to authenticated;

drop policy if exists "characters_select_own" on public.characters;
create policy "characters_select_own"
  on public.characters
  for select
  to authenticated
  using ((select auth.uid()) = user_id);

-- There are intentionally no client INSERT/UPDATE/DELETE policies. Character
-- creation and rewards are server-owned and use a server-only key.

create or replace function public.award_character_exp(
  p_user_id uuid,
  p_character_id uuid,
  p_reward_event_id text,
  p_amount bigint,
  p_balance_version text default 'exp_v1'
)
returns table (
  id uuid,
  user_id uuid,
  name text,
  avatar text,
  level smallint,
  total_exp bigint,
  balance_version text,
  applied boolean
)
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  v_current public.characters%rowtype;
  v_inserted boolean := false;
  v_rows bigint := 0;
  v_max_exp bigint;
  v_new_total bigint;
  v_new_level smallint;
begin
  if p_amount < 0 or p_amount > 1000000 then
    raise exception 'EXP award out of bounds';
  end if;
  if p_reward_event_id is null or char_length(p_reward_event_id) not between 8 and 160 then
    raise exception 'Invalid reward event id';
  end if;

  select c.* into v_current
    from public.characters as c
    where c.id = p_character_id
      and c.user_id = p_user_id
      and c.balance_version = p_balance_version
    for update;
  if not found then
    raise exception 'Character ownership or balance mismatch';
  end if;

  insert into public.character_exp_ledger(reward_event_id, character_id, amount)
    values (p_reward_event_id, p_character_id, p_amount)
    on conflict do nothing;
  get diagnostics v_rows = row_count;
  v_inserted := v_rows > 0;

  if v_inserted then
    select cle.cumulative_exp_to_reach_level into strict v_max_exp
      from public.character_level_exp as cle
      where cle.balance_version = p_balance_version and cle.level = 60;
    v_new_total := least(v_max_exp, v_current.total_exp + p_amount);
    select max(cle.level)::smallint into strict v_new_level
      from public.character_level_exp as cle
      where cle.balance_version = p_balance_version
        and cle.cumulative_exp_to_reach_level <= v_new_total;
    update public.characters as c
      set total_exp = v_new_total,
          level = v_new_level,
          updated_at = now()
      where c.id = p_character_id;
  end if;

  return query
    select c.id, c.user_id, c.name, c.avatar, c.level, c.total_exp,
           c.balance_version, v_inserted
      from public.characters as c
      where c.id = p_character_id and c.user_id = p_user_id;
end;
$$;

revoke all on function public.award_character_exp(uuid, uuid, text, bigint, text)
  from public, anon, authenticated;
grant execute on function public.award_character_exp(uuid, uuid, text, bigint, text)
  to service_role;

grant all on table public.characters to service_role;
grant all on table public.character_exp_ledger to service_role;
