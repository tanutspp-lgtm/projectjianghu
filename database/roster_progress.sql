alter table public.sw_characters
    add column if not exists exp integer not null default 0 check (exp >= 0),
    add column if not exists progress_revision bigint not null default 0 check (progress_revision >= 0),
    add column if not exists progress_details jsonb not null default '{}'::jsonb
        check (jsonb_typeof(progress_details) = 'object');
grant select (id, level, exp, progress_details, progress_revision), update (level, exp, progress_details, progress_revision)
    on public.sw_characters to service_role;
