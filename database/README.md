# EXP v1 — server-side balance source of truth (snapshot)

Active **Supabase project:** `project jianghu` / `uxxkyptoocbswedwizct`, Singapore. EXISTING schema in `public` contains exactly these tables as verified 2026-10-11:
- `game_balance_versions(balance_version PRIMARY KEY, description, is_active, max_character_level, qi_slot_1_unlock_level, qi_slot_2_unlock_level, reference_kills_per_minute, reference_auto_hours_per_day, overlevel_mob_exp_cap_ratio, created_at)`
- `character_level_exp(balance_version, level, equivalent_monster_kills, exp_to_next_level, cumulative_exp_to_reach_level)` composite PK balance_version+level
- `monster_level_base_exp(balance_version, monster_level, base_exp)` composite PK balance_version+monster_level
- `exp_level_gap_rules(balance_version, min_delta, max_delta, exp_multiplier, note)` composite PK balance_version+min_delta

All 4 tables use Row Level Security. The live database currently has `exp_v1` seeded: 1 version record, 60 character level rows, 60 monster level rows, 7 level-gap rows.

`exp_v1_character_levels.csv`, `exp_v1_monster_base.csv`, and `exp_v1_gap_rules.csv` are reproducible OFFLINE reference copies for tests, not the actual game player database, and must not be used as an excuse to seed/reset production. Exact sampled levels and cumulative XP have been compared against Supabase, including Lv59->60. Read from live DB using a server-only connection for authoritative runtime balance.

### EXP calculation requirements
- `monster_level_base_exp` is the **normal monster award per kill** BEFORE level-difference penalty, per-species difficulty override, active bonus and server validated assistance rules.
- delta = `monster.level - character.level`, inclusive ranges in gap rules; for monsters higher than player's level, cap award at **2x** same-level normal monster base EXP (exp_v1). At +16 and higher difference: zero EXP. At -21 or below: 10% minimum reward.
- `character_level_exp.exp_to_next_level` is the current level's XP requirement; `cumulative_exp_to_reach_level` starts at zero for Level 1 and ends at total XP to arrive at Level 60. XP should be retained across reconnects, and level cap prevents overflow/reward duplication.
- XP curves are testing targets at 12 eligible full-EXP kills/min, 24h/day, not guaranteed due to different monsters and player DPS.
- Separate Qi EXP/profession EXP tables should be designed later. **Skill XP has been explicitly DROPPED; SP from character level only.**

### Useful read-only queries
See `exp_v1_read_only_queries.sql`. Never put the service role key in a client bundle.
