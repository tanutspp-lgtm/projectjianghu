alter table public.sw_characters add column level integer not null default 1 check (level >= 1);
alter table public.sw_characters add constraint sw_characters_name_spelling check (name !~ 'กระหรี่') not valid;
