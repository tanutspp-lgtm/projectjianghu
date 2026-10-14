# HANDOFF — Project Jianghu / WUXIA FLUTE ARENA v8.0CE

Date: 2026-10-14. **Current candidate latest, after v8.0CC frontend + v8.0CD pending backend/client patches**. This package supersedes the unshipped CD ZIP. Upload BOTH Netlify & Backend v8.0CE, backend first.

## User QA reports and changes
1. **The middle ladder does not merely appear desynchronized; the actor can continue CLIMBING IN THE AIR above the physical top of the ladder.** Previous explanations relying only on a prediction/renderer bug were insufficient. Real server climb geometry is `(1170,390,550)` (x, top, bottom). Earlier deployed GitHub map had `(1170,235,550)`, 155px above the visible ladder. v8.0CD already corrected the map and blocks mismatched client/server maps at welcome. v8.0CE adds a SECOND authoritative rule: when at the upper landing with UP held, no re-grab is permitted. The actor must exit climb at top and remain supported by the upper floor. Both server and Offline movement enforce no regrab at upper landing; DOWN can still descend. Server hard validates all three ladder configurations at startup, fails closed if map regresses. Physics never accepts client coordinates.
2. **Magic-wave projectile disappears visually even though server still has a live projectile**: v8.0CD fix included in this version. Browser `WorldAssembler` previously ignored numeric projectile IDs in AOI/Delta and drew only short cast trail. Wire IDs now canonical strings, including `removedShots`, cast shot IDs; server uses IDs internally unchanged. No projectile lifetime, speed, hit logic, damage, or AOI geometry change.
3. **Always-on small FPS + Ping display**: one unobtrusive transparent ~10px HUD label at top-left of gameplay (`FPS 60 · Ping 42ms` illustration). `measuredFps` from real RAF, sampled once per second. True app-level WebSocket RTT: nonce+client `performance.now()` -> server echo -> client monotonic elapsed. One ping per 2000ms while connected & tab visible; only one outstanding probe, 6.5s timeout, latency smoothed 70% previous+30% current; stale >8s/Offline shows '—'. Browser never sends time or position that server trusts. Client requires `rtt-probe-v80ce` feature in welcome before ping (backward safe; CD map version mismatch still fails intentionally). Server validates integer nonce, rate limits 35/s shared with input, echoes only nonce. Additional bandwidth is approximately two tiny WebSocket messages per 2s per connected player. `?perf=1` remains optional for big profiler; small label is always shown in-game.

## Files changed
Frontend `index.html` (small FPS Ping, v8.0CE marker, receiver/scheduler and offline top-ladder guard, main module cache bust), backend `server.py` (hard ladder ceiling/top regrab blocker, strict map geometry guard, RTT echo feature and `/healthz` v8.0CE). New `test_v80ce_ladder_rtt.py`, `test_v80ce_ping_ws.py`. Existing CD `online_delta_prediction_v80by.js` and existing project assets included verbatim. `beast_map_common_v80bq.json` top at X1170 is 390.

## Locked specs — NO changes
- Offline remains mechanical reference, Online server authoritatively owns movement, damage, status, XP, loot, AUTO targets, map and NPCs. Client remains SERVER-FIRST, no speculative position or early jump/rope.
- AUTO 120s destination, ground 25%/floating 75% for mixed floors, navigation; monster physics/sounds, drop, EXP and derived stat formulas unchanged.
- Guest PvE: no friendly-fire PK, including AOE, guard break, AUTO.
- Snapshot sim 30Hz, transfer ~10Hz, staggered network, AOI/Delta unchanged; no extra snapshot bandwidth.
- Approved sound gain values unchanged (hit 0.78, flute 0.24, boar death 0.66, wolf death 0.67, jump 0.52, pickup 0.42 without cooldown). Existing sprites, BGM, drop sprites unchanged.
- Performance-first: consider CPU/RAM server, browser FPS/RAM/iPad canvas, network bytes, allocations, 1/10/20/30 guests, and keep security and offline/online parity; do not claim live success without production QA.

## Test evidence in current container
- `python -m unittest discover -p 'test*.py' -q`: 28 tests PASS incl. authoritative hold-UP from bottom for 10 seconds (300 server ticks), no sky climb/re-grab, ropes X510/X1590 and CD projectile/pve tests.
- `python test_v80ce_ping_ws.py`: actual local WebSocket join, ping nonce echo, manual input interoperability, invalid ping -> 1008 PASS.
- `python test_v80by_30_delta_sockets.py`: 30/30 websocket AUTO guests, 663 snapshots, ~2.48MiB delivered in 2.2s in LOCAL environment (not production and not iPad).
- `node --check` on main inline JS; existing `test_v80cd_projectile_snapshot.cjs` and `test_v80cc_server_first.cjs` both PASS.
- Re-verify ZIP content and CRC before distribution.

## Deploy & QA
1. Unzip **Backend v8.0CE** and upload all root files into GitHub `tanutspp-lgtm/projectjianghu` branch main; specifically ensure `server.py` AND `beast_map_common_v80bq.json` updated. Do not upload ZIP as one file.
2. Wait for Render Live. Check `https://projectjianghu.onrender.com/healthz` contains `v8.0CE`. Old Backend is NOT compatible with new client ladder guard; intentional safety failure.
3. Upload full **Netlify v8.0CE ZIP**. Force Safari reload if old JS is cached. Verify title `v8.0CE SERVER-FIRST PVE`.
4. First test alone (1 Guest), hold UP at **middle ladder X1170** for several seconds after reaching upper platform, re-approach upper end and press UP, then descend DOWN; ropes X510/X1590 also. Shoot into empty space and toward far monsters; projectile artwork must persist while server projectile lives. Verify tiny FPS/Ping label updates and shows `—` on offline, remains small. Test 10/20/30 guests + tab switch.
5. If ladder still climbs above physical top despite `/healthz v8.0CE`, record video showing coordinates (`?debugtiles=1`) and browser version label and check server logs—only then revisit geometry. This release is NOT yet verified by live Safari/iPad QA.

## Next blockers & general state
Persisting real account/inventory, PvP fairness (currently PK intentionally OFF), optimization, long-distance AOI projectile visibility, and true external monitoring remain pending. Never infer server capacity from 30 bots running on one browser. HANDOFF_LATEST_TH.md should point to this release.
