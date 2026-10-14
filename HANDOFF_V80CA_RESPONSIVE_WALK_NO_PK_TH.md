# Project Jianghu v8.0CA — Responsive Walk + Cooperative PvE (No Auto-PK)
Date: 2026-10-14

## Summary / user reports
- v8.0BZ online movement feels delayed specifically when beginning to walk (keyboard / joystick), despite improved 10Hz network and 30Hz server.
- Auto farming causes friendly-fire: projectiles hit Guest players even when no explicit PK command was issued.

## Actual changed code
- `index.html` (Netlify): `updateOnlineVisual()` now consumes `SelfPredictor` visual position directly each animation frame (removes old secondary `dt*22` position-smoothing lag), updates local facing & walk distance immediately. `frameForPlayer()` paints walk/idle immediately on local button transitions while preserving server-authoritative animation for attacks/stun/guard/rope. During manual walking, camera follows predicted avatar without an extra slow camera filter. `?perf=1` shows last Walk input->visual frame time. Input cadence and held heartbeats remain unchanged. No client positions or damage sent.
- `online_delta_prediction_v80by.js` (Netlify): replaced ONLY `SelfPredictor` implementation, kept existing AOI/Delta `WorldAssembler` compatible. Frame-integrated visual-only walking at original move speed, capped time-step and 280ms stale window. ACK-aware correcting avoids stale 10Hz snapshots making avatar jerk backward on immediate key release. Real server position takes priority on large correction, disabled movement states (AUTO, knockdown, stun, rope, jump, dash). No collision or combat authority transferred to browser. File name retained for backwards compatibility, cache buster changed to 8.0CA.
- `server.py` (Render): Guest world is cooperative PvE. All projectile victim lists contain only server-owned `Monster` entities; `apply_shot()` independently rejects non-monsters, including even if a caller incorrectly passes `is_mob=True`. No player damage/guard break/knockdown/stun from another player's shots; bullets pass through other players and still hit monsters. This also covers AUTO because it uses the same `update_shots()` path. Added server `welcome.features` and `/healthz` v8.0CA label.
- No new packet types / keys, no new environmental variables, no database migrations; preserve existing legacy client protocol handling, AOI/Delta, staggered 10Hz snapshots, 30Hz simulation, spatial grid, monster AI, server AUTO, buffs, progression and inventory.

## Regression and verification
- `python -m unittest -v test_v80ca_no_pk` explicitly covers guard, break, attack, AoE, thirty crowded Guests, monster penetration, projectiles remaining alive without monsters, manual/AUTO.
- `node test_v80ca_immediate_walking.cjs` covers first animation frame visual start, release, facing reversal, ACK correction, blocked movement, stale network freeze, visual-only result.
- `node test_delta_prediction_v80by.cjs` updated earlier now-stale test expecting an illegal backwards rewind on release; AOI/Delta reassembly remains identical.
- Verified in this build: Python unittest discovery 18/18 passed; `node test_v80ca_immediate_walking.cjs` and legacy AOI/delta test passed. Local server 30 independent real WebSocket clients with AUTO: delta 677 snapshots, 2.39 MiB in ~2.2s; legacy 666 snapshots, 10.82 MiB in ~2.2s. The original 356 assets under assets/ and characters/ were SHA256-identical to BZ. Server remains authoritative: no x/y/HP/DMG user messages accepted. Actual Safari/Render key-to-screen delay and 30-person stability NOT claimed until live QA.

## Instructions
1. Update the **entire Backend ZIP** at repo root and wait for Render Live. `/healthz` should mention `v8.0CA`.
2. Update the **entire Netlify ZIP** after Render (do not mix vCA frontend with old vBZ Backend if testing PvE safety).
3. Login Online and compare Offline ↔ Online walk starts using short taps (A/D, left/right, touch joystick), release, reverse. Test with 2 Guest accounts standing overlapping: shoot J/K/U across the other player toward a wolf. Other Guest HP/guard must not change; wolf must still take damage. Test player AUTO while multiple Guests stand on farming path.
4. Test switching tabs for >30s, manual collision with rope, jump/dash, knockback, and stress bot 1/10/20/30. With `?perf=1`, compare Walk input→visual, FPS, Tick P95 and RX. `Walk input→visual` is browser-side presentation timing, NOT network RTT or guaranteed real server command execution time.

## Performance-first (PERMANENT)
- Added no new recurring network messages and no extra server game loop passes. Removing Guests from the projectile collision candidate list reduces collision work in crowded rooms. Client predicts only one local avatar at RAF; no separate render loop or timers. Predicted movement stays bounded and stops if authoritative snapshots become stale. Does not increase avatar/sprite cache memory or audio voices.
- Browser in one-tab 30-stress simulation is not equivalent to 30 real devices; must measure CPU/RAM/tick on live Render before recommending paid upgrade. Server PvE guard avoids PK exploits and state desync rather than trusting modified client.

## Known limitations
- Local visual prediction is not exact physics replay: walk into an unexpected collision, get knocked back or attach a rope can cause necessary authoritative correction. For Safari with 10Hz snapshots, exact latency improvement requires a user-side measurement; no FPS promise.
- Instant combat animation/jump/dash are NOT part of this patch (not requested in final focus); server-owned events remain as in BZ.
- PvP disabled for every Guest in this map, deliberately, not merely for AUTO. No PK consent toggle exists. Design separate PvP modes with explicit opt-in and independent security policy before restoring.
- Other locked Online/Offline parity gaps and account persistence remain. Read `HANDOFF_OFFLINE_ONLINE_PARITY_AUDIT_V80BR_TH.md` and `HANDOFF_PERFORMANCE_FIRST_V80BW_TH.md` as well.
