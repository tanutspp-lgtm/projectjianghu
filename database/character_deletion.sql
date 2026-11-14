alter table public.sw_characters add column delete_after timestamptz;

create function public.sw_character_deletion(
  character_id uuid, action text, expected_deadline timestamptz, typed_name text
) returns void
language plpgsql security definer set search_path = ''
as $$
declare
  target public.sw_characters%rowtype;
begin
  select * into target from public.sw_characters
    where id = character_id and owner_id = (select auth.uid()) for update;
  if not found then raise exception using errcode='P1001', message='character unavailable'; end if;
  if target.delete_after is distinct from expected_deadline then
    raise exception using errcode='P1002', message='request changed';
  end if;
  case action
    when 'request' then
      if target.delete_after is not null then raise exception using errcode='P1002', message='already requested'; end if;
      update public.sw_characters set delete_after=clock_timestamp()+interval '168 hours' where id=target.id;
    when 'cancel' then
      if target.delete_after is null then raise exception using errcode='P1002', message='no request'; end if;
      update public.sw_characters set delete_after=null where id=target.id;
    when 'confirm' then
      if target.delete_after is null or clock_timestamp()<target.delete_after then
        raise exception using errcode='P1003', message='not yet available';
      end if;
      if typed_name collate "C" is distinct from target.name collate "C" then
        raise exception using errcode='P1004', message='name mismatch';
      end if;
      delete from public.sw_characters where id=target.id;
    else raise exception using errcode='22023', message='invalid action';
  end case;
end; $$;
revoke all on function public.sw_character_deletion(uuid,text,timestamptz,text) from public,anon;
grant execute on function public.sw_character_deletion(uuid,text,timestamptz,text) to authenticated;
