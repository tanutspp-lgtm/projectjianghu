# Project Jianghu v8.0BZ — Performance Optimization Phase 2 (2026-10-14)

## IMPORTANT — definitive patch status
- **Pair both packages:** Netlify `WUXIA_FLUTE_ARENA_v8_0BZ_PERFORMANCE_PHASE2_NETLIFY.zip` and GitHub/Render `PROJECT_JIANGHU_SERVER_v8_0BZ_PERFORMANCE_PHASE2_GITHUB.zip`.
- Code baseline = v8.0BY, includes all v8.0BX navigation fixes, v8.0BW staggered snapshot, v8.0BY AOI+delta/visual-only horizontal prediction.
- This patch is NOT automatically deployed. Production Render and Safari FPS/latency tests remain pending; do not claim 30 real people can play smoothly just because 30 localhost sockets connected.
- **Performance-first review is mandatory on EVERY future change.** Before adding AI, monsters, FX, inventory, skills or maps, estimate (1) server tick CPU, (2) server peak RAM, (3) snapshot per-user bytes and frequency, (4) browser FPS/frame time/GPU pressure and decoded image memory, (5) security authority boundaries, (6) Offline↔Online parity. Regress 1/10/20/30 clients. Preserve all existing approved SFX gain and game formulas.

## Code modifications (v8.0BZ)
### Client Netlify index.html
1. **Input on change:** immediate packets when direction/guard/movement button changes or ability tapped; while a button is held, heartbeat every 220ms (server times out held inputs after 550ms); idle sends at most 1/s. Still uses monotonic sequence numbers. Payload has ONLY `t,seq,buttons,pressed`. Releasing on blur/tab-hidden is immediate; input no longer waits 60ms to respond.
2. **Forest terrain canvas caching:** renders 5 static platform/ground surfaces once after all source sprites are loaded, then blits them rather than re-tiling the rockface each animation frame. 12MiB hard decoded-cache budget and graceful direct-draw fallback. Dynamic clouds, monsters, particles, pickup effects and foreground background remain untouched. This TRADEOFF raises browser graphics memory by ~8MiB to lower frame CPU; use device profiling before increasing the budget.
3. `?perf=1` opt-in debug monitor: Browser FPS, smoothed frame ms, slow frames >32ms, Snap gap, WebSocket RX KiB/s, server tick P95/max, server Input/s & TX KiB/s, terrain cache MiB, JS heap if supported (Safari generally N/A). For combined bot stress use `?botstress=1&perf=1`. Tool is visual QA only, no authority / gameplay mutation.
4. `window.JianghuPerformance.current` exposes the same read-only diagnostics for browser QA.

### Backend server.py
1. **Spatial grid** indexed at 240 world-unit cells, built ONCE after 30Hz guest position updates. Monsters examine only candidate players in nearby cells, still apply original `reachable_player`, distance and attack conditions. Actual collision, server-derived damage, EXP, drops, PvP and AUTO are unchanged.
2. **Cached derived private attributes:** per-Guest signature of real level, sandbox level, STR/AGI/VIT/DEX/INT, equipped Qi and ranks and test gear. Recalculate `prog.derive_stats` for PRIVATE NET SNAPSHOT only when signature changes. Dynamic HP, SP, STA, input ACK, auto countdown and combat remain updated at original rates. Old-client full snapshot still supported; unchanged derived fields omitted by delta.
3. **Cheap bounded performance counters:** per-tick duration ring 180 samples, rollup each ~1s: tick P95/max ms, received Input/s, transmitted snapshot KiB/s, active players and mobs; private to each player's `self.performance` object (not shared as public player state).
4. `/healthz` updated to `v8.0BZ`. Protocol join name remains `aoi-delta-v80by` to avoid breaking new/old clients. No additional pip dependencies, no DB schema changes.

## Local regression evidence (2026-10-14)
- Syntax: Python compile and extracted Netlify inline JS parsed by Node.
- `test_v80bz_performance_regression.py`: 30 randomized player positions x 25 iterations, nearest reachable mob target match; derived cache hit/miss on stat/gear changes; self delta omits unchanged derived/performance; empty perf window safe.
- `test_v80bz_input_cadence.js`: instant input transitions, 220ms heartbeat, idle suppression, monotonic sequences, strict server packet shape.
- Passed preexisting security/protocol, Qi passive, 20 platform routes, 30 concurrent WebSocket delta guest test, 30 blocked-send regression, auto anti-cheat. Old sandbox protocol test requires `ENABLE_GUEST_SANDBOX=1` on the isolated test process, which remains disabled by default in production. All tests performed on localhost, NOT Render.
- Short in-process performance test on same local host (separate runs, ~2.35s each, different random state; CPU percentage of ONE core, indicative not precise benchmark):

| Connections | BY CPU/core | BZ CPU/core | BY TX received | BZ received |
|---|---:|---:|---:|---:|
|1|2.1%|2.1%|0.020 MiB|0.023 MiB|
|10|8.1%|6.4%|0.494 MiB|0.472 MiB|
|20|14.8%|10.2%|1.379 MiB|1.523 MiB|
|30|15.3%|14.0%|2.480 MiB|2.616 MiB|

Data variation is expected because monster movement, serialization and sampling differ. This patch targets server CPU/render work, NOT guaranteed bandwidth savings (AOI/delta did that in BY). At 30 connections BZ sent slightly MORE data in this run. Do not claim fps +X% or bandwidth reduced. Local server RSS roughly 100–102MiB over this short run; not comparable to Safari graphics memory.

## Real deployment instructions / QA
1. Extract backend ZIP and upload ALL files to GitHub repo `tanutspp-lgtm/projectjianghu` root main (replace same names). Wait Render Live, verify HTTP `/healthz` contains v8.0BZ.
2. Update paired Netlify ZIP, hard reload once. Test 1 browser client normal movement/guard/press-and-release and tab switch; do not test on 30 bots before single-client regression.
3. Open `https://YOUR-NETLIFY-SITE/?perf=1&botstress=1`; test 1/10/20/30 Guest sockets. Record Browser FPS/Frame ms/slow count, Snap gap, RX, Server Tick P95, TX and Render CPU/RAM. Use a second browser/device for independent viewer to separate browser load generator from server latency.
4. If **server tick P95 reaches/exceeds 33ms** or spikes strongly, investigate server CPU/IO/Render resource limits. If Server Tick fine but Browser FPS collapses, focus canvas/GPU or 30-socket driver. If Snap gap spikes yet CPU fine, investigate internet scheduling/queue stalls.
5. Guest account persistence, QoS 1000+ players, full Anti-cheat, true manual PvP rollback hit timing and multi-zone maps are NOT complete. QA guest sandbox remains disabled on public server by default.

## Notes / next tasks
- Spatial grid improves target candidate lookups, but 20 beasts/30 people still has a real cost. For more maps/mobs, add zone partition and profile actual durations before complex AI refactor.
- Dirty signature caching is NOT a fully event-driven dirty-bit ECS. Delta encoder still compares AOI entity fields per guest; converting to proper component-version counters needs reliable per-field invalidation and protocol tests.
- `performance.memory` is Chromium-specific; Safari can report unavailable. Canvas cache uses roughly 8MiB graphics backing; further cache budget must be device-adaptive and benchmarked.
- No restart/resume persistence; Guest resets are not solved in this patch.
- Runtime v8.0BZ changes have no impact on Offline formulas/approved audio assets; Offline remains canonical for gameplay values. Preserve locked 120s bot destinations and 25/75 tile weights.
