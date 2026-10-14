# PROJECT JIANGHU v8.0BY — AOI / DELTA SNAPSHOTS + BOUNDED CLIENT PREDICTION
Date 2026-10-14 (Asia/Bangkok). Latest files: NETLIFY v8.0BY and BACKEND v8.0BY must be paired.

## Why this patch exists
User observed high solo online delay, tab-return delayed controls, bots freezing on ropes, 30 stress guests dropping, and own AUTO facing oscillation. v8.0BX fixed rope/AUTO/tab rendering + moved bot AI to server, but 30 connected Guest clients still got a full world JSON every 100ms. v8.0BY directly addresses the network serialization/bandwidth hotspot rather than deferring it.

## Code changes
Backend `server.py`:
- Simulation remains server-authoritative, 30Hz world / target 10Hz snapshots. Movement/collision/AUTO, HP/DEF, combat, EXP, loot and pickup remain server-owned. No trusting client x/y/hp/damage/level/equipment.
- Shared world state assembled ONCE per three ticks as an object. Each snapshot_writer has a 1-slot replacing queue and transmits on its staggered 10ms phase. JSON serialization, AOI filtering, and per-guest delta encoding now occur in that individual writer phase, avoiding N separate payload constructions inside the simulation tick.
- AOI per guest uses SERVER-derived p.x (default 950 world-space units, +200 for mobs/shots). Visual entities beyond AOI leave the replication view; they remain FULLY ACTIVE for physics, combat, loot, and other players. Can set `AOI_RADIUS` 700..6000 on QA server only after verifying viewport/ranged attacks.
- Delta encoding per player id/monster id/projectile id/loot id sends changed fields and removals; first frame and every 150 ticks (5s) sends a full AOI keyframe. The delta baseline advances ONLY after `ws.send()` succeeds; dropped mailbox frames cannot produce broken deltas. Private `self` fields and inventory only resend changed values, with a periodic full keyframe. Events are server-generated and area-filtered, owner/victim events always included. NOTE visual events are still not guaranteed if stale packet dropped under prolonged backpressure; persistent transactional event stream remains future work.
- Input acknowledgement `self.inputAck` is captured from the tick-consumed sequence. Client must treat it as an acknowledgment, NEVER position permission. Strict input schema/cooldowns/rate limits remain.
- **Backward compatibility:** a legacy client joining with only `{t:'join',avatar:'...'}` receives original full-world snapshots with no AOI or delta. New clients opt in with exact `protocol:'aoi-delta-v80by'`. Backend can be deployed before Netlify with old client still working; real bandwidth reduction applies only to updated clients.
Frontend `online_delta_prediction_v80by.js` (new):
- Bounded `WorldAssembler`: rebuild complete local render state from new full/delta packets; discard stale/out-of-order ticks; prune removed entities; cache private stats and inventory without copying world data into history every packet.
- Bounded `SelfPredictor`: visual-only input prediction for OWN ordinary horizontal ground movement (and rope y when already climbing); maximum 185ms lead, correction toward server coordinates, `inputAck` prunes consumed input history (24 command cap). It never transmits x/y/HP/damage and DOES NOT predict dash/jump/knockback/attacks or arbitrary collision. This is **not** fully deterministic client prediction + physics reconciliation, and cannot guarantee Offline-like response with high RTT.
- Other players and mobs continue v8.0BV interpolation. On tab focus/blur Bx reset behavior stays, predictor resets before new snapshot.
- Stress Bot `bot_stress_v80bp.js` joins using the new delta protocol, still uses server-owned AUTO and only counts incoming snapshot bytes without JSON.parse 30 streams. No browser-side bot navigation/combat loop.

## Local tests actually executed
- Legacy full protocol: `test_beast_parity_v80bq.py` (30 clients +20 beasts), `test_online_protocol_v80bs.py`, `test_v80bu_protocol_security.py`, `test_security.py` pass. Regression suite for EXP, Qi, equipment, monster balance, AUTO/rope, slow socket loop also pass.
- `test_v80by_delta_security.py` verifies AOI entities, removal/new entity, private data patch, and periodic full resynchronization.
- `test_v80by_30_delta_sockets.py`: 30 real local WebSocket connections + server AUTO: 638 packets / 2.2s, ~2.45 MiB aggregate. Same old full protocol BX-style: 669 packets / 2.2s, ~10.64 MiB; ~77% less bytes in this comparison. Beware slight packet count and process-scheduling differences; NOT a controlled identical tick exact comparison, and NOT proof of better real Safari FPS/Render CPU.
- Node `test_delta_prediction_v80by.cjs`: AOI deltas, removals, private fields/inventory, stale-drop, bounded own visual prediction + ack, passed. Inline JS `node --check` passed.
- Playwright Chromium graphical test attempted but sandbox forbade localhost (`ERR_BLOCKED_BY_ADMINISTRATOR`). NOT browser E2E tested. Safari, Render, mobile GPU/RAM not tested. Do not state fix verified on production.

## Remain incomplete/at risk
- Full deterministic movement/physics prediction + rollback and RTT adaptive buffer NOT implemented. Browser-only prediction must stay strictly visual, bounded and corrected from server.
- Full AOI can cull entities at viewport/ranged boundaries; test exact real camera dimensions and long shots. AOI does NOT decide hits.
- Network events can be lost if mailbox drops stale frames; combat/progression state continues in next authoritative snapshot, but 100% reliable event delivery still needed for important once-only visual effects and future transactional events.
- Still broadcasts 10Hz. If 30 users stand together, many constantly changing x/y values still transmit; delta doesn't eliminate all bandwidth/CPU; baseline full keyframe once ~5s.
- No persisted Guest account, no final PvP anti-cheat, no verified sustained concurrency, not full Offline/Online parity.

## PERMANENT PERFORMANCE-FIRST RULE (LOCKED)
For EVERY next patch measure / reason about server CPU, tick delay, heap & garbage collector pressure, traffic bytes and per-player snapshots, client FPS, JS heap and image/GPU memory (especially Safari and mobiles), API rate limits and cheating. Test 1/10/20/30 Guest, focus/blur, AUTO/manual, and 5-10 minutes sustained activity before deployment claims. Track before/after. Do not increase snapshot frequency or AI loops until profiling shows need. Never sacrifice server authority. Preserve all locked sounds, sprite atlas, item drops, Offline formulas and existing feature behavior. Update both Netlify and backend ZIP and handoffs every future protocol edit.

## Deploy / rollback
1. Extract GitHub SERVER v8.0BY ZIP, upload new and changed files into main repo ROOT; ensure `server.py` and all dependent modules/tests, not old `server(1).py`. Render must Deploy new main commit; check GET `/healthz` mentions v8.0BY. No production auto-edit by assistant.
2. Deploy matching Netlify v8.0BY ZIP. Old Netlify v8.0BX remains usable during Backend rollout (receives legacy full snapshots).
3. QA solo manual delay then own AUTO/rope and +10/+20/+30 stress; compare FPS, Snap gap, RX KB/s, disconnections, Render CPU/RSS, animation/loot/event correctness against BX. Mobile Safari manually required.
4. If unexpected regression, restore BOTH BX client/backend or redeploy earlier known-good matched pair; note that rendering smoother alone cannot solve Render-Thai RTT.
