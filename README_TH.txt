# LATEST v8.0CA — READ HANDOFF_V80CA_RESPONSIVE_WALK_NO_PK_TH.md FIRST. Coop PvE only; no automatic PK. Paired Netlify ZIP must deploy.

LATEST v8.0BZ Performance Phase 2: Pair Netlify and GitHub ZIPs. See HANDOFF_V80BZ_PERFORMANCE_PHASE2_TH.md; /healthz v8.0BZ, still Guest-only with no persistence.

LATEST v8.0BY: OPT-IN AOI+DELTA protocol. New Netlify v80BY sends `protocol:"aoi-delta-v80by"` on join; old Clients still get Full Snapshot. Requires paired Netlify and Backend deployments. See HANDOFF_V80BY_AOI_DELTA_PREDICTION_PERFORMANCE_TH.md. Never trust browser positions or damage.

UPDATE v8.0BS (2026-10-14)
Server now implements Guest ephemeral Lv1 EXP exp_v1, level-up +3 Stat/+1 Skill, authoritative Stat/Flute Mastery attacks/CRIT/SP/STA, common beast loot/Bag and 30-guest support. EXP tables already exist in Supabase (unchanged); local exp_balance_v1.json fallback. Netlify v8.0BS is REQUIRED for full v8.0BS UI. Not 100% offline parity: Qi / actual gear/equip / persisted accounts / premium+manual mobs / map warps remain.
Run: python test_online_parity_v80bs.py; python test_online_protocol_v80bs.py; python test_security.py; python test_beast_parity_v80bq.py; python test_balance_v80bo.py.

v8.0BQ TEST SERVER: เพิ่ม beast_map_common_v80bq.json + server.py ใหม่ (20 มอน) ดู HANDOFF_SERVER_V80BQ_BEAST_PARITY_TH.md ก่อนอัปเดต Render

PROJECT JIANGHU — ONLINE GUEST SERVER v8.0BO (2026-10-14)

Primary service: Render projectjianghu, Python server.py (WebSocket /ws, HTTP /healthz)
Repo: https://github.com/tanutspp-lgtm/projectjianghu
Mode: Guest-only server authoritative arena Lv5. This is NOT a fully ported v8.0BN MMORPG.

SERVER CHANGE v8.0BO
- Server-owned guest Lv5 HP 1300; PvP-first HP table Lv1–60 exists in Supabase.
- Uses Supabase read-only tables jianghu_pvp_hp_v80bo (60 rows) and
  jianghu_monster_damage_v80bo (360 rows), verifies version. Local fallback if unavailable.
- Server calculates monster raw attack and defense reduction for +5 reference gear;
  mode common Lv5 training arena. Other modes and tiers prepared as data, not active online maps.
- Attack rate protection: server-side animation/action cooldown, second monotonic clock check,
  input validation, 35 packets/s and 12 action packets/s rate limits. No attack queue.
- Guest level/gear/spell strength cannot be supplied by client.

FILES IN THIS REPOSITORY
server.py             REQUIRED update (source of truth for current online server)
requirements.txt      UNCHANGED: websockets>=15,<17
render.yaml           UNCHANGED from the current repository; not needed for this code update
README_TH.txt         UPDATED usage and limitations
 test_security.py     UPDATED integration/security test; useful but not required by Render
 test_balance_v80bo.py NEW balance/flood unit tests; useful but not required by Render

HOW TO DEPLOY
1. Unzip the delivery archive on your device. Do NOT upload the ZIP as one file to GitHub.
2. In GitHub repo main branch at ROOT, upload/replace server.py (required).
3. Optionally also upload test_security.py, test_balance_v80bo.py, README_TH.txt,
   requirements.txt and render.yaml from this package to bring all root files up to date.
4. Commit changes. Render auto deploy tracks main; no separate Render upload required.
5. Confirm the new commit was deployed in Render and healthz responds.
6. Test join, movement, attacks and monster HP via web client (not confirmed yet).

Local tests: pip install -r requirements.txt; python test_balance_v80bo.py; python test_security.py
Note: server.py contains the project publishable Supabase key (safe to publish with correct RLS).
Never add Supabase service_role keys or database passwords to code / public GitHub.

KNOWN LIMITATIONS
- Online arena remains fixed Lv5 and uses earlier simplified server projectile/AI/monster HP.
- Offline v8.0BN monster AI and progression are NOT fully ported to Render.
- Full online player level, equipment state, PvP damage scaling and item persistence not ready.
- GitHub automatic code-writing from ChatGPT returned 403; browser upload required.
- Supabase reference records created earlier; live Render deploy not yet verified.
