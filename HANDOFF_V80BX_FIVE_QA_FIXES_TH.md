# PROJECT JIANGHU v8.0BX — USER QA 5-POINT FIXES + NETWORK LOAD HANDOFF
Date: 2026-10-14 Asia/Bangkok

## USER'S ACTUAL FIVE REPORTS / FIXES
1. Online manual movement with only 1 person feels laggy versus Offline. Client own avatar now visually uses the LATEST authoritative sample (`sampleNewest`) instead of buffered 4.5 ticks intended for remote peers, capped 30ms extrapolation plus visual-only 16px manual input lead and smoothing. DOES NOT yet implement full client-side prediction/reconciliation. Render RTT, server 10Hz, and per-socket stagger can still cause delay; no false promise of Offline-like latency.
2. Switching browser tab and returning caused avatar moving in stale directions and apparent inability to control. Browser now clears held keys, wheel, press queue, resets drawing state on tab blur/visibility/focus and accepts next actual snapshot as a fresh baseline. No historical physics re-run in Client. Server remains authoritative and background damage can still occur as expected. Manual input should regain control, provided no stun/down/death effects. Verify Safari tab suspension.
3. Stress bots freeze at middle/end of rope. `farm_auto_v80bu.py` now supports intermediate platform jump-off both ascending AND descending (old code only jumping on ascent). Full directed navigation regression covers 5 x 4 = 20 paths (includes downward starts on upper platforms), 20/20 reached in deterministic local test. Routes follow physics (no teleport).
4. Browser freezes at 30 stress bots, some sockets close (reported surviving ~14). Old stress clients did 30 JS navigation/combat loops every 100ms + 30 full JSON.parse streams. In v8.0BX each Stress Guest joins and sends `{'t':'auto','enabled':true}` ONCE, using the real authoritative server AUTO already used by the player. Each connection still receives full 10Hz snapshots for network/serialization load measurements, but browser fast-path counts snapshot bytes without JSON.parse for all bots. No per-bot movement input loop, no extra fake coordinates. Display last disconnect code and reason for diagnosis. 30 guest sockets locally received 663 snapshots / ~2.2 seconds, 10.32 MiB total (~4.7 MiB/s) with AUTO on. This is NOT proof that Render/Safari can run 30 without lag.
5. Own player AUTO twitches facing back/forth. Root cause: server's previous `if distance<90: move away` reversed facing; next tick `if face!=target_direction: move toward`, ping-pong at 30Hz. Remove backing off; server faces target without walking, attacks with existing cooldown; retains short stable target id (0.75s). Tested 120 ticks with close mob -> no forced left/right movement.

## TESTS ACTUALLY RUN (LOCAL, NOT DEPLOYED)
- `python test_v80bx_live_navigation.py`: all 20 directed map platform source/destination routes pass with server physics, plus close-range face stability.
- `python test_v80bx_30_real_sockets.py`: 30 connected WebSockets, server AUTO enabled, all receive >=22 snapshots in ~2.2 seconds in machine (full server snapshot send still consumes bandwidth).
- Existing: `test_v80bu_monster_auto.py`, `test_network_stability_v80bv.py`, `test_online_parity_v80bs.py`, `test_qi_effects_v80bt.py`, `test_security.py`, `test_online_protocol_v80bs.py`, `test_v80bu_protocol_security.py`, `ENABLE_GUEST_SANDBOX=1 python test_sandbox_protocol_v80bt.py` pass.
- Node: `node --check bot_stress_v80bp.js`, `online_snapshot_smoothing_v80bv.js`, extracted index inline JS; `node test_snapshot_smoothing_v80bv.cjs` passes. Live Netlify/Safari/Render gameplay has NOT been verified by this patch.

## IMPORTANT PERFORMANCE-FIRST RULE REMAINS PERMANENT
Read `HANDOFF_PERFORMANCE_FIRST_V80BW_TH.md` on EACH patch. Must evaluate server CPU, tick time, memory, network outbound, client FPS, DOM/JS heap/canvas costs and mobile/Safari. Preserve Offline↔Online parity, authoritative attacks/items/position, all audio gains/asset paths. NEVER claim client stress-bot runs in one tab are equivalent to 30 real remote players. Monitor independent 1/10/20/30 tests and long-running 5-10 minute trials. No extra client-side AI per bot unless explicit separate workload requested.

## KNOWN LIMITATIONS AND NEXT PERF PRIORITY
- The full world JSON snapshot still serializes all players + 20 monsters + loot and is sent to EVERY guest 10Hz (with per-socket private state). 30 guests used ~4.7MiB/s combined in local 2.2sec test. Must implement AOI and/or delta replication after measuring, with reliable event transport for EXP, loot, cast and deaths; no silent dropping of gameplay events.
- v8.0BW stagger can add up to ~90ms send offset and cause higher perceived local delay. Benchmark against an optional un-staggered mode BEFORE further optimizing; avoid guessing.
- Client self-render lead 16px is VISUAL-ONLY, not a hitbox change nor server rewind. Do not trust any input of x/y/HP/damage from browser. Implement full client prediction only with bounded input/sequence reconciliation if later requested and benchmarked; avoid security regressions.
- No persistent accounts yet. No claim full 100% Offline/Online parity, PvP anti-cheat guarantee, 30-player production capacity, or Safari memory stability.
- Stress Bot counters reflect server-owned AUTO simulation and FULL snapshot network load, but not 30 real independent player INPUT streams. Need another load tool for human input flood and 30 separate browsers for client FPS.

## DEPLOY
1. Extract BACKEND v8.0BX ZIP, upload its root files to GitHub main, not old server(1).py. Wait Render status Live; check `/healthz` contains v8.0BX.
2. Deploy paired Netlify v8.0BX ZIP.
3. Test Online manual solo, switch away for >=30 seconds return and immediately steer, own AUTO near wolf, +10/+20/+30 stress with FPS, RX, Snap and disconnect code. Note Render CPU/tick and Safari memory. Stop if instability.
4. Keep prior v8.0BW ZIP as rollback if production shows regression. DO NOT claim deployed or fixed in live until the user tests it.
