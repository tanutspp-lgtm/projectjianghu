# Project Jianghu v8.0BQ — Online Guest common-beast parity (work in progress)

**Build date:** 2026-10-14. **Not deployed on Render or Netlify by this artifact.**

## Goal and exact scope
The user explicitly wants Online gameplay **indistinguishable from the Offline game**, rather than sprites over online mockup monsters. This first source-level integration brings the current Offline 5-platform **common-farm beast spawn layout, species, sprite timing and core wolf/boar contact behavior** into the Python authoritative Guest server. This is **NOT yet full online/offline gameplay parity**; see remaining work.

## Delivered
- `beast_map_common_v80bq.json` is a generated roster from `monster_spawns_v80au.js`, `mode=common`, using exactly the current client's `plats` and `climbs` collision geometry. 20 distinct slots (14 wolf, 6 boar) on 5 platforms. NEVER accept client-generated spawn state; load from server asset.
- `server.py` reads the JSON, creates actual `Monster.species` and sends it in snapshots. Removes five old mockup/humanoid training mobs from the Guest common farm.
- Server retains authoritative player and mob HP, hit, displacement, cooldown, WebSocket rate checks, defenses and Supabase read-only references.
- For common wolves/boars, server emulates the Offline basic same-platform patrol/chase, edge checks, 0.42s bite animation with contact occurring after 0.19s, ranged hit stopping a beast without far-distance knockback, and Classic-style **player recoil** `.28s, 300 px/s, vy=-240, invulnerability 1.12s`. Server outputs `biteAge` for the client's **existing** 24-frame boar / wolf atlas animation. Server mob death respawn delay is minimum 5 seconds, shared wave 7.56 seconds, and the browser keeps the original death fade / spawn fade / locked sound gains.
- Frontend `index.html` maps the server's `biteAge` to local animation clock. All original monster sprite files and audio left as-is. No replacement asset generation.
- `test_security.py`, `test_balance_v80bo.py` expectations updated for 20 beasts, and new `test_beast_parity_v80bq.py` checks roster, recoil, safe patrol and a **LOCAL** test with 30 actual Guest WebSockets + 20 monsters. All passed on the build machine. This does not establish public Render capacity or actual tablet FPS.

## NOT YET matching Offline; do not claim fully cloned
- Offline monster modes `premium/manual`, humanoid casters/healers, their waves/heals, wolf pounces, full offline spell behavior, and settings-driven monster profiles are not ported. Current Online server arena is common-only.
- Online Guest is still a temporary Lv5 server-owned character, without full Online XP progression, skills/inner arts, saved equipment, sealed loot, inventory persistence, drops and farming rewards. Offline skill/gear/bot paths differ. No client may authorize rewards.
- Offline and Online still have separate execution languages (browser JS vs server Python). For future game parity, define **shared map/monster behavior data** and parity tests for every mechanic, not duplicate tuning by hand.
- Offline game itself is unchanged. New mountain/tall maps, warp routing and jump/drop navigation are not implemented. Do not assume Bot Stress route finder works on those maps.
- New Python beast AI approximates the Offline common-mode behavior, but was not empirically compared side by side for 120 seconds on an actual live webpage; small chase/patrol/bite and knockback timing discrepancies may remain.

## Deployment (MANDATORY TWO SEPARATE STEPS)
1. **Backend:** upload/replace GitHub files `server.py` and add `beast_map_common_v80bq.json` next to it, plus optional new regression test/documentation. Render auto-deploy must finish. Check `https://projectjianghu.onrender.com/healthz` returns **`wuxia-online v8.0BQ beast-map common`** (not old build). Do not upload backend ZIP to Netlify.
2. **Frontend:** deploy `WUXIA_FLUTE_ARENA_v8_0BQ_COMMON_BEAST_ONLINE_TEST_NETLIFY.zip` to Netlify. Still run Online Guest at `wss://projectjianghu.onrender.com/ws`. The optional 30-Bot Stress panel remains behind `?botstress=1`.
3. Back up the old Render commit and current Netlify deploy before switching. These are test-stage changes affecting all Guest sessions on this server.
4. Confirm 20 beast monsters online, 6 boars + 14 wolves, correct atlas animations, attacks, fall/recoil, no missing frame images, respawn timing, and actual FPS with 30 bots on a test instance before treating as done.
5. Never falsely advertise this as full offline-online clone; use this as the first online beast-system parity stage only.

## Locked untouched specs
- All audio gains in `game_audio_v80bm.js`: hit .78, flute .24 (460ms, 1 voice), boar death .66, wolf death .67, jump .52, pickup .42 unrestricted; default BGM 70%/SFX 80%.
- Bot random goal architecture `HANDOFF_BOT_DESTINATION_DESIGN_LOCKED_TH.md`: 120 seconds per bot, weighted ground pool 25% vs floating pool 75%, encounter attacks during travel, destination held through knockback, recompute per map.
- Item/armor, inner arts, PvP-first HP and DEF formula and Supabase read-only tables unchanged.
