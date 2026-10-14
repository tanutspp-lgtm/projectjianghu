# v8.0BY LATEST: See HANDOFF_V80BY_AOI_DELTA_PREDICTION_PERFORMANCE_TH.md. AOI/delta now implemented for opt-in v80BY client; benchmark before production claims. Backward compatible full protocol for old clients.

# UPDATE v8.0BX: mandatory new handoff HANDOFF_V80BX_FIVE_QA_FIXES_TH.md. Snapshot payload remains heavy (~4.7MiB/s across 30 guests in local test); prioritize AOI/delta, FPS/heap, tab recovery and rope physics for future performance decisions.

# PROJECT JIANGHU — PERFORMANCE-FIRST ENGINEERING RULES (v8.0BW)
Date: 2026-10-14

## IMPORTANT PERMANENT RULE FOR EVERY FUTURE PATCH
- Offline and Online parity remains mandatory. ALL changes must be reviewed for performance, server CPU, tick stability, bandwidth, mobile/desktop FPS, browser memory, rendering/GC churn, and security. Do not introduce a correct-looking feature with unbounded loops, allocations, snapshots or timer drift.
- Update BOTH Netlify client ZIP and GitHub/Render backend whenever code changes affect their shared protocol or gameplay. Update HANDOFF_LATEST_TH.md, changelog and performance notes inside both packages. Preserve approved audio asset values and animations.
- Record before/after metrics under the SAME load; do not equate a 30-socket simulation in one browser with 30 independent browsers. Typical QA: 1, 10, 20, 30 players; online AUTO on/off; monitor server tick overrun p95/p99, CPU, RSS, outbound bytes/s, snapshot interval/jitter, websocket outbox drops, client FPS p5/p50, JS heap/DOM/canvas allocations and 5-10 minute sustained-play stability. On iPad/Safari, JS heap APIs can be limited: use device observations and remote profiling where possible.
- Keep all gameplay results server authoritative; optimize by AOI, batching, snapshot transport and allocation reduction, not by trusting client coordinates, HP, damage, exp, gear or item drops.

## WHAT v8.0BW ACTUALLY DOES
- Previous v8.0BV uses a per-guest maxsize=1 outgoing snapshot queue and a separate writer task. This prevents one slow connection from stalling the 30Hz simulation, dropping obsolete visual packets.
- v8.0BW additionally staggers network SNAPSHOT SENDS among ten phases, each 10ms apart during a 100ms window. Each guest retains TARGET 10Hz; shared world is still simulated at 30Hz, snapshot created at 10Hz. A server-side monotonic 0.1-second clock determines each slot and guests are assigned round-robin. Security, damage, AUTO behavior and assets are unchanged.
- This spreads network I/O bursts; it DOES NOT yet spread all CPU work: the shared JSON snapshot and 30 per-player private JSON payloads are still built together every 100ms. If 30-player spikes persist, profile and separately schedule serialize/encode work or implement AOI/delta snapshots.
- Added at most ~90ms intentional send offset for the latest available snapshot for a guest. This may improve burstiness but worsen latency/jitter in adverse conditions. Benchmark both v8.0BV and v8.0BW on real Render/iPad before keeping it as production default; rollback to BV if worse.
- Reusing the same round-robin slot among >10 clients is expected; 30 users should distribute roughly 3 per slot, not all thirty in one burst. This is not a proof of server capacity.

## IMPORTANT ONLINE/OFFLINE DIFFERENCES / LIMITATIONS
- Offline is still the golden reference for behavior, combat, art and sound. Online Guest is not a fully persistent MMORPG.
- AUTO goal selection 120s, ground vs raised tile weights 25%/75% where both exist, encounter monster en route, preserve goal after knockback; server controls AI actions.
- The 10Hz snapshot target is NOT the 30Hz physics tick. Do not mistake 10Hz for once every 10 seconds.
- Current AOI/delta compression, input prediction and mobile GPU memory optimization are NOT finished.
- Ensure front/back deployments match versions. Browser UI smoothness is not proof of authoritative positions being correct.

## DEPLOY / QA
1) Upload server package extracted files to GitHub root/main, wait Render live and confirm /healthz says v8.0BW.
2) Upload accompanying Netlify client ZIP (its runtime JS stays same as v8.0BV, docs updated only).
3) Test manual movement, AUTO, loot, skills, 30 Guest load. Compare FPS, Snap gap and Render CPU/memory against v8.0BV; if user-visible warping increases, restore prior stable build.
4) NEVER conclude lag is resolved without a client+server simultaneous benchmark.
