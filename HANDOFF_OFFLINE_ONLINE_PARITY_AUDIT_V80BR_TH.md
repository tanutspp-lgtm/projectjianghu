# PROJECT JIANGHU — v8.0BR Offline ↔ Online Parity Audit and permanent patch rule
**Date:** 2026-10-14. **STATUS:** Work in progress. DO NOT call Online an Offline 100% clone.

## คำสั่งล็อกจากผู้ใช้ (สำคัญสูงสุด)
ผู้ใช้ต้องการ Online เล่นแล้วเหมือน Offline แบบโคลนแกะ ทั้งภาพ เสียง ตำแหน่งมอน จำนวนมอน พฤติกรรมมอน การต่อสู้ ปราณ สกิล EXP/เลเวล สเตตัส ATK/HP/DEF/การคิดดาเมจ อุปกรณ์/ไอเท็ม/ดรอป และบอท/แมพ แค่มี Asset อยู่ใน ZIP ไม่ได้ถือว่าเป็นระบบ Online แล้ว
**ทุกแพตช์หลังจากนี้ต้องทำ impact assessment กับ Offline + Online Client + authoritative Python Online Server + protocol/snapshots + database/saving + QA ในแพตช์เดียวกัน** และอัปเดต handoff ของทั้งสอง ZIP; หากชิ้นใดไม่เสร็จต้องระบุชัด ห้ามแอบเขียนว่า parity 100%.

## v8.0BR ทำแล้วจริง
- `index.html`: แก้เฉพาะการแสดงผลด้านทิศของ Wolf/Boar ใน Online; ความผิดพลาดเกิดเมื่อ WebSocket Snapshot เปลี่ยน `face` ก่อนที่ตัวภาพ `rx` (interpolated x) จะขยับตามจนถึงทิศใหม่ ทำให้เห็น sprite หันขวาแต่ภาพเคลื่อนซ้าย. เพิ่ม `onlineBeastVisualFace` ให้ตัวภาพหันตาม actual visible delta-x ขณะเดิน แต่ตอนกัดใช้ server `face`. ไม่แก้ Offline, monster AI server, collisions, stat, balances หรือไฟล์ Sprite.
- `TEST_WOLF_DIRECTION_V80BR.js`: 5 regression cases via Node ผ่าน; ตรวจ Node syntax ของ inline JS ผ่าน. ยังต้องมี visual QA บน Browser/Render สำหรับทิศเดินจริง 2 ทิศ + กลับตัว + bite + knockback.
- เพิ่มเอกสารตรวจความต่างเพื่อให้แชทใหม่ไม่เข้าใจว่าระบบออฟไลน์ถูกพอร์ตแล้ว.

## ช่องว่างจริงระหว่าง Offline และ Online (ตรวจจากโค้ด v8.0BQ+v8.0BR)
| ระบบ | Offline | Online ใน Server v8.0BQ / Client v8.0BR | สถานะ |
|---|---|---|---|
| ภาพผู้เล่น / wolf/boar | Atlas/PNG + animations | ใช้ asset และ monster species เดียวกัน; Online ใช้ network snapshots แทน local sim | PARTIAL: แก้ทิศแสดงภาพแล้ว; ต้องทดสอบจริง |
| เสียง SFX/BGM | `game_audio_v80bm.js` six sounds/BGM | ไฟล์และ mixer เดียวกันถูกโหลดใน client; calls for `cast/flute`, hit, jump, species death; pickup only on authoritative pickup event | PARTIAL: Online ไม่มี pickup/drop backend จริง; จังหวะ event ต้องเทียบละเอียด |
| มอนป่าฟาร์มทั่วไป | `monster_spawns_v80au.js`, `monster_ai_v80ar.js`, 20 จุด | Backend `beast_map_common_v80bq.json` 20 จุด, Wolf 14, Boar 6; Python AI เลียนแบบ core patrol/chase/bite, ไม่ใช่ source function เดียวกัน | PARTIAL: ไม่รับประกัน behavior 100% |
| มอน Premium / Manual / Humanoid / healer / leap | ทดสอบใน Offline | Server รองรับเฉพาะ common beast | MISSING |
| Character level + EXP | `offline_progression.js`, level/stats + level up | Guest server `guest_level=5`; ส่ง `level=5`; ไม่มี EXP/level up จริง | MISSING |
| STR / DEX / AGI / VIT / INT, regen, stats | `derivedStats()` และ Offline stat allocations | Server Guest ไม่มี allocated stats, damage scaling, regen parity | MISSING |
| ATK / skill damage | Damage computed in Offline from INT, weapon, crit, qi, skill | Python `ATTACKS` fixed (`attack` 165, `aoe` 135, `break` 45); ignores real character build | MISSING parity |
| HP / DEF | `player_hp_balance_v80bn.js`, GearLab `DEF/(250+DEF)` | Python `hp_reference(level)` loads matching Supabase table when available, `mitigate` identical DEF reduction shape; but actual Guest Lv5 with reference +5 armor only | PARTIAL: shared reference tables != real gear/level |
| Monster attack damage | ZoneCombat rolls common/premium/manual raw by monster level, gear mitigation and attributes | Python loads Supabase v8.0BN monster raw table; common only; `mitigate(round(raw*.88), defense)` on bites | PARTIAL: requires parity test for offline exact hit formula / multiplier |
| Inner arts/Qi | Qi prototype (`qi_test_system.js`, `qi_catalog_v1.js`, `qiActive`) | `qiActive` explicitly returns false if not Offline; no authoritative Qi state/effects | MISSING |
| Crit, Hit/Flee, dodge, status resistance | Offline derived stats and crit multipliers | Server has no complete player-derived Crit/Flee/Hit pipeline | MISSING |
| Equipment | offline gear lab/test and catalogs; actual full MMO gear is still partly design | Server Guest only `armor_enhance=5`; no owned/equipped item instances, affix server rolls | MISSING |
| Loot / inventory / pickup | `inventoryRecords`, LocalStorage; droppedLoot and offline pickup | Online UI has placeholder `onlineInventoryRecords`/`onlineGroundLoot`; server snapshot has no loot reward/drop/pickup authoritative flow | MISSING |
| Bot | Offline AUTO currently nearest same-floor mob (`updateOfflineAuto`) | Stress bots in `bot_stress_v80bp.js` follow locked 120s weighted random Tile goal, not player-account server bots | DIVERGENT |
| Maps / warp / vertical | Original common arena map; taller descending maps still planned | Python map JSON matches current arena, no multi-map warp protocol | NOT BUILT |
| PvP combat | offline combo/prototype | Server owns input, cooldown, projectile contact, basic guard/break/recoil; full PvP spec not implemented | PARTIAL |
| Persistence | Offline progression/localStorage testing | Guest-only temporary state, no saved character | MISSING |

## Audio locked values — NEVER adjust silently
`game_audio_v80bm.js`: hit .78; flute .24 with 460 ms cooldown and 1 voice; boar death .66; wolf death .67; jump .52; pickup .42 UNLIMITED and NO COOLDOWN. Default BGM 70%, SFX 80%. Source MP3 paths are in `assets/audio/sfx/`; BGM in `assets/audio/bgm/`. Online client **does call** sound for server-confirmed casts/hits/deaths/jump. It does **not** establish pickup equivalence: backend doesn't issue loot_pickup in v8.0BQ. The audio bus is shared, but verified parity is NOT achieved for every game event.

## How to achieve real parity safely (not just swap client files)
1. Create formal mechanic specs and golden fixture tests from Offline (same map positions, spawn JSON, timestamps, RNG seeds, damage inputs). Refactor common declarative rules into versioned JSON (NOT duplicated tuning by hand).
2. Port actual authoritative level/stat/progression and equipment/affix/inner-art state with server-side derivation, DB schema and login/character persistent identities. Frontend must never dictate damage, HP, EXP, item IDs, loot, crit results or drop rolls.
3. Port skills/ATK/Crit/Hit/Flee/guard and verify math with 100+ deterministic cross-implementation cases. Include DEF K=250 formula and locked PvP-first HP tables; preserve existing user-locked balancing.
4. Port authoritative monster types/modes/AI/spawns/hitboxes and synchronized sprite/sound events. Verify side-by-side visual and recording tests on actual clients.
5. Add authoritative EXP/loot/inventory/pickup and persistence, then compare live gameplay and combat logs Offline/Online. Keep rate limits and anti-cheat.
6. Add map routing and weighted random navigation for each map; test 30 users with external load driver and separate single-screen observer; don't confuse with opening 30 browser windows.
7. Only mark a subsystem "parity passed" after programmatic tests + real browser QA. Leave unfinished rows openly marked.

## Rule for every future patch (MANDATORY)
Before sending a new ZIP: report impacted systems, update Offline JS + Online client + Online Python server together when necessary, maintain versioned protocol and backward compatible deploy ordering, run regression tests, document pass/fail parity checklist, update `HANDOFF_LATEST_TH.md`, `CHANGELOG_LATEST_TH.md`, `ASSET_MAP_TH.md`, mirror docs in backend archive. If server unchanged, say so explicitly. Separate ZIPs for Netlify vs GitHub/Render; never claim Render deployed until verified. **Offline is behavioral reference**; however authoritative multiplayer server cannot blindly execute untrusted client code or share LocalStorage as source of truth.

## Deploy / test v8.0BR
Deploy latest v8.0BQ server first (if not already). v8.0BR needs no Python code change: the wolf-facing hotfix is visual-only. Replace Netlify ZIP; open Online Guest; inspect wolf/boar turning left/right, patrol, chase, bite, stop, spawn/death; confirm server reports beast-v80bq. Test internal JS regression `node TEST_WOLF_DIRECTION_V80BR.js`. DO NOT conclude parity with all systems based on this patch.
