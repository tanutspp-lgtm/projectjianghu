-- Run in Supabase SQL editor or through a safe server-side SQL client.
-- Existing live tables: do not run migrations or destructive queries without owner approval.
SELECT * FROM public.game_balance_versions WHERE balance_version = 'exp_v1';
SELECT * FROM public.character_level_exp WHERE balance_version = 'exp_v1' ORDER BY level;
SELECT * FROM public.monster_level_base_exp WHERE balance_version = 'exp_v1' ORDER BY monster_level;
SELECT * FROM public.exp_level_gap_rules WHERE balance_version = 'exp_v1' ORDER BY min_delta;
