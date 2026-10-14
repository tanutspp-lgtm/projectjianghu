# Project Jianghu v8.0CD — Projectile visuals + ladder geometry / protocol lock
Date: 2026-10-14. **Paired Netlify and GitHub/Render Backend required.** Based on v8.0CC frontend (server-first/no movement prediction) and v8.0CB backend (PvE-only, corrected ladder X1170). Read HANDOFF_PERFORMANCE_FIRST_V80BW_TH.md and HANDOFF_OFFLINE_ONLINE_PARITY_AUDIT_V80BR_TH.md before continuing.

## User-reported failures
1. Flute magic projectiles are visible only close to the caster, while the actual server shot remains active. Cause found: browser AOI/Delta `WorldAssembler.apply` skipped every `shots[]` entry whose `id` was a NUMBER, but backend sent numeric shot IDs. As a result only short cast-trace effects were drawn, not authoritative projectiles.
2. Middle ladder at X1170 still climbs into the sky even with client-only v8.0CC. Confirmed deployed GitHub `beast_map_common_v80bq.json` previously still had X1170 top Y235; visible frontend middle ladder top is Y390. Earlier CB server patch may not yet have been deployed to Render. This cannot be fixed with client smoothing or local prediction alone.

## Implemented fixes
- `online_delta_prediction_v80by.js` assembler: accepts numeric or string entity IDs, normalizes map keys, packet entries, and `removedShots` to canonical strings. Legacy numeric shot IDs and latest string IDs both work, and Delta patches retain the same projectile from one packet to the next. No change to hit logic, projectile lifetime, damage, range or server authority.
- `server.py`: publishes shot IDs and cast `shotId` as strings consistently on the network; server-internal shot ID remains original type. AOI remains server controlled. Publishes `mapClimbs` in the WebSocket welcome payload and updates `/healthz` marker to v8.0CD.
- `beast_map_common_v80bq.json` on the backend: all three climbs must be `(510,235,550)`, `(1170,390,550)`, `(1590,235,550)` (X, top, bottom). Correct geometry is ALREADY in packaged CB backend, but older deployed GitHub map showed `(1170,235,550)`. This paired server ZIP includes the correct JSON. No extra upward collision area is created.
- `index.html`: validates ALL three backend climb x/top/bottom definitions against its own hardcoded geometry before entering Online. On mismatch, disconnects with clear message **to deploy v8.0CD backend**, rather than silently allowing climb desync. Normal v8.0CC server-first position renderer remains; DO NOT re-enable visual movement prediction. Cast trace ID comparison is consistent with string shot ID.
- Player-versus-player damage remains DISABLED in Guest PvE, including AOE, AUTO, guard break. Server still resolves ALL combat, movement, monster AI, equipment, EXP, HP and rewards. No changes to sound source/gain, sprite assets, loot or Offline mode.

## Tests run in local container
- `python -m unittest discover -p 'test*.py' -q`: PASS (see existing suites and new protocol tests).
- `python -m unittest test_v80cd_protocol_regression test_v80cb_map_and_transitions test_v80cb_cast_trail -v`: 6/6 PASS: ladder geometry, no sky exit, PvE no friendly damage, shot/string ID and cast metadata.
- `node test_v80cd_projectile_snapshot.cjs`: PASS: legacy number IDs, new string IDs, full/delta persistence, numeric removedShots.
- `node test_v80cc_server_first.cjs`: PASS: no client-ahead movement or climb, confirmed-only rendering.
- `python test_v80by_30_delta_sockets.py`: PASS 30/30 WebSockets+server AUTO, approximately 645 snapshots / 2.22 MiB combined over ~2.2s **LOCAL**, not real production/Safari FPS.
- Validate JS syntax, ZIP CRC, immutable main images and locked SFX compared with v8.0CC before release.

## Important deployment and remaining QA
1. **Install SERVER v8.0CD first**: unpack GitHub Backend ZIP, upload contents to GitHub repo root including `server.py` AND `beast_map_common_v80bq.json`, commit and wait Render Live. The previous live GitHub map had wrong middle ladder, even if frontend CC was updated.
2. Open https://projectjianghu.onrender.com/healthz and confirm `v8.0CD`. The frontend CD intentionally refuses to join a server that doesn't publish matching geometry, to avoid sky-climb corruption.
3. Upload Netlify v8.0CD ZIP, clear old tab/cache if necessary and reload. Verify label `v8.0CD SERVER-FIRST PVE`.
4. Test X1170 ascending/descending from both lower and upper floor, X510 and X1590; shoot long distances and verify the visible authoritative projectile persists, not just a muzzle trace. Test 1/10/20/30 sockets FPS, Snap gap, Server Tick P95; test tab restore. Save screen recording/diagnostics.
5. NOT verified on deployed Render+Safari/iPad in this handoff. No claim that all stutter is fixed; server-first positional updates may still feel delayed due to 10Hz. True network AOI culling when shots go beyond AOI still exists by design. No prediction reintroduced. Future PvP lag compensation remains separately pending.

## Updated files
Backend: `server.py`, `test_v80cb_cast_trail.py` compatibility assertion, `test_v80cd_protocol_regression.py`, this handoff, `README_DEPLOY_V80CD_TH.md`; packaged ladder JSON correct as in CB.
Netlify: `index.html`, `online_delta_prediction_v80by.js`, `test_v80cd_projectile_snapshot.cjs`, this handoff, `HANDOFF_LATEST_TH.md`, `CHANGELOG_LATEST_TH.md`, `ASSET_MAP_TH.md`. Preserve all previous handoffs and assets.
