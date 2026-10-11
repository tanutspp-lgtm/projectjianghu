# CODEX: initial development task for PROJECT JIANGHU

Read `README_START_HERE.md`, `docs/GAME_DESIGN_LOCKED.md`, `docs/TECHNICAL_CONSTRAINTS.md`, the original `client/` readmes, and the current `server/` code BEFORE changing code.

## Goal: v7.9N vertical slice
Safely evolve the existing web client and Python WebSocket authoritative game server, reusing every original working sprite, animation, combat input, map/parallax/tileset, loading gate, character selector and mobile controls.

1. Inventory the code and verify the static browser client/server protocol actually works locally. Identify mismatches and baseline failures. Do not guess that Render deployed code equals this server zip.
2. Establish a maintainable, **cross-platform-compatible boundary** between UI/render/input, shared message types/protocol, and server game logic. Avoid a risky full rewrite. Future targets: browsers, Windows/macOS desktop wrapper, iOS/iPadOS and Android. Core game state and protocol must remain platform-independent.
3. Add secure account identity (prefer Supabase Auth verified server-side; consider browser WebSocket authentication transport and token expiry) and permanent character create/load/save in Supabase, with SQL migrations committed to repo. Do not hardcode service-role keys/client secrets. Guest migration strategy can be phased. If credentials unavailable, implement runnable local mocks/tests and clear environment setup.
4. EXP kill rewards and level-up must be **server-authoritative**, sourced from existing Supabase `exp_v1` configuration; prevent reward duplication/packet injection, assisted-powerlevel abuse and ineligible monster awards. Max character Lv60; no PvP scaling from PvE level multiplier. Handle large EXP integers and level-up across multiple levels. Add tests for exact EXP boundary behavior, anti-cheat, relog and server restart persistence.
5. Render **Character EXP HUD** and a place for **active Qi EXP HUD** using layout/safe-area rules (Qi detail is future work). No need to implement Skill Tree, other combat professions, crafting or new artwork in this first task.
6. Propose incremental commits and run tests. Deliver change summary, pass/fail evidence and reproducible local commands.

## Must not do
- DO NOT DEPLOY to Render, Netlify, app stores or Supabase production without explicit approval.
- DO NOT destructively mutate active Supabase tables. Existing `game_balance_versions`, `character_level_exp`, `monster_level_base_exp`, `exp_level_gap_rules` are treated as read-only configs unless user specifically authorizes a balance change.
- DO NOT replace sprites/assets, change animations, collision/ladder mechanics or combat design spec without tests and approval.
- DO NOT design additional combat jobs, a full Skill Tree or overhaul abilities yet.
- DO NOT accept player-provided EXP, item count, HP, damage, currency, or level in network packets.
- DO NOT fix touchscreen layouts by uniform scaling that clips notch/safe areas or makes controls untappable.

## Delivery
- Source changes in coherent modules + optional migrations, tests, and exact commands. Make a clear distinction between WORKING code, a PROPOSAL, and UNTESTED integration. Call out any steps requiring credentials without requesting secrets in chat.
