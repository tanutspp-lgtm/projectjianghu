# Game design decisions confirmed with the owner (2026-10-11)

**Title:** Project Jianghu / Wuxia Flute Arena. 2D side-scrolling wuxia MMORPG, MapleStory-style 2D layers; active combat rock-paper-scissors around attack / guard / guard break inspired by Age of Wushu. One initial playable flute combat profession, male and female avatars, three hairstyles and five colors each (30 sheets). PvE mob grinding, optional AUTO PvE, PvP only in designated contested-resource maps later.

## Character levels / EXP
- Character MAX LEVEL **60**.
- Lv 1-20 easy, Lv 20-40 moderate, Lv 40-59 increasingly hard, **Lv 59 -> 60 is a big endgame wall**, designed to need as many equivalent full-EXP kills as Lv 50 -> 59 combined.
- Assumed AUTO farm **12 eligible monsters per minute, 24 hours per day**. Approx progression target: Lv1->20 8.5h; Lv20->40 4d; Lv40->50 12d; Lv50->59 16.5d; Lv59->60 16.5d, total Lv40->60 **45d**. This is a BALANCE MODEL ONLY, not verified actual kill rate.
- `exp_v1` (already seeded in live Supabase) 40->60 requires 777,600 equivalent eligible monster kills; Lv50->59 285,120 and Lv59->60 285,120. Tune from actual gameplay later, do not silently modify now.
- Character PvE level advantage is separate from PvP. PvP should primarily depend on Qi effects/stats, equipment and player skill, not overwhelming PvE level damage bonuses.
- Level difference EXP penalties for too-low and too-high monsters; monsters +16 levels above provide ZERO EXP; +11 to +15 reduced/capped. Do not enable high-level carry/powerlevel exploit; server measures contributions/assists. See `database/exp_v1_gap_rules.csv`.

## Qi / inner arts
- Qi slot 1 unlocks **Character Lv20**, slot 2 unlocks **Character Lv40** (changed from older Lv60 idea).
- Qi progression EXP **separate** from Character EXP. Qi stages: 1-30 basic, 31-50 advanced gated by matching manual, 51-60 mastery gated by manual, stage 61 legendary gated by manual. Unlock raises level cap, does not auto-level.
- Qi stage stat increases are small; special proc effects with cooldown/counters are main PvP differentiator. Don't implement yet unless specifically assigned.
- MAIN gameplay HUD: Character EXP bar + **one tracked Qi EXP bar**; Qi menu: detailed bars for BOTH slots. The tracked bar must not clutter iPad/mobile view. Qi capped by missing manual displays a clear unlock requirement.

## Combat skill points
- **NO skill EXP.** Skill Points (SP) are awarded from CHARACTER level: +1 SP every 2 levels, 30 total by Lv60. Limited SP must prevent maxing all skill choices.
- One combat profession ultimately has **two mutually constrained paths**: flute DPS/control versus flute support/heal/buff. Support must PvE farm modestly but have much lower solo player-killing damage; professions like alchemist/cook are open to all combat builds.
- Skill Tree and other combat jobs are **future/end-stage content**, NOT immediate task. Preserve room in data model only.
- Combat mobile UI: three context-sensitive primary attack buttons switch to three MANUALLY TRIGGERED ground-combo actions when current target is knocked down. Guard, guard-break and movement dash accessible separately. Knockdown must permit follow-up combo window (not immediate invulnerability). Do not automatically execute ground combos.

## Professions / gathering (future)
- Main craft profession select ONE of four: alchemist (potions), tailor (clothing), cook (food buffs), smith (weapon/metal armor). Craft profession EXP granted once per successfully finished craft **transaction**, NOT per individual output item; recipe tier penalty prevents trivial recipe spam.
- Gathering professions tracked separately: herbs, silkworm/silk, mining, hunting/skinning. Hunting EXP occurs on VALIDATED skinning a corpse after kill, not killing a mob. Gathering EXP on actual action.
- Profession EXP UI lives inside Profession menu, not main HUD. Crafting requires items/recipes/ingredients/trade economy; build after character persistence + loot.

## Item/monster progression (future)
- Monster-specific rare cards are one-time permanent modest stat unlocks per species; duplicates can exchange but do not stack. Earned loot/items/cards must be server-validated and transactionally persisted. XP cap/penalties should not suppress rare-card drop eligibility unless specifically designed.
- Rare craft ingredients and valuable contested resources can exist in PK zones, but slower non-PK routes must remain viable.
