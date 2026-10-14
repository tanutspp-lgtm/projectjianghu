# PROJECT JIANGHU — v8.0BV ONLINE RUBBERBANDING / NETWORK STABILITY

Base: v8.0BU. This patch addresses online visible snapping when server snapshots arrive late or a slow guest WS applies network backpressure. This is NOT a claim that 30 users are lag-free on Render or Safari. No player/monster stats, SFX volume, sprite, Qi, gear, XP, anti-cheat movement authority, AUTO destination and weighted tile rules were altered.

## Server source of truth
- `server.py` still simulates at 30Hz and broadcasts snapshots at 10Hz.
- Previous `await asyncio.gather(ws.send(...) for all clients)` held the game tick hostage if one browser couldn't consume TCP data. Now each Guest has an independent `snapshot_writer` async task and a maxsize=1 snapshot outbox; the game loop never awaits other players' sends. Older snapshots are replaced with newest world state if a client cannot keep up. For connection stall >1.5s, slow websocket is closed/reconnected. Server remains authoritative for movement, HP, DEF, AUTO AI, hits, drops, EXP, Qi and equipment.
- Game snapshots/events sent to slow clients might be skipped under extreme congestion. This is intentional prioritization for world progress; a future reliably delivered combat-event channel is recommended if strictly guaranteed VFX/audio events are required.
- `/healthz` version reports `v8.0BV` after Render deployment.
- Backend and Netlify need deploying as a PAIR for full update. v8.0BV backend remains compatible with v8.0BU client; code changes intentionally narrow.

## Netlify rendering / diagnostics
- New `online_snapshot_smoothing_v80bv.js` buffers authoritative coordinates against server tick indexes. World draw tick moves only forward; it interpolates position history, with bounded (<=33ms) visual extrapolation. No client position is ever sent to server.
- Camera follows a softly filtered visible player position instead of jumping instantly to each new snapshot correction. Genuine huge server relocation/death reset clears the visual buffer.
- Online HUD now displays `Snap gap XXXms`: largest time between the most recent ~24 received world snapshots. Typical cadence 100ms. This is NOT Ping/RTT; it is the client-observed snapshot arrival interval. Compare against FPS and count of enabled stress bots. e.g. 100-160ms with high FPS probably fine, spikes >300ms indicate network/backend/device scheduling. These are diagnostic guides, not hard limits.
- Both normal player and all peer/monster sprites use the same buffered positioning. Wolf visual facing follows visible movement, preserving v8.0BR fix.

## Security and locked design
- `farm_auto_v80bu.py` retained: server selects a tile goal every 120s; 25% chance ground/75% upper when both exist; attacks locally encountered mobs; knockback doesn't clear goal; ropes are traversed. Normal Guest player AUTO stays server authoritative.
- Input validation / seq replay / packet rate / action cooldowns / Sandbox QA-only permissions unchanged. No client destination/damage injection.
- SFX locked: Hit 0.78, Flute 0.24, Boar death .66, Wolf death .67, Jump .52, Pickup .42 unlimited voices; BGM 70%, SFX 80%.
- This is still a Guest demo with no persistent character and not a 100%-finished MMORPG.

## Test commands
- `node --check online_snapshot_smoothing_v80bv.js`, `node --check <extracted inline index script>`.
- `node test_snapshot_smoothing_v80bv.cjs`: randomized irregular packet arrivals, no visible backtracking, valid interpolation and respawn.
- `python test_network_stability_v80bv.py`: 30 intentionally stalled outbound sockets, >=11 simulation ticks in .55s, 1 queued world state per client.
- `python test_v80bu_protocol_security.py`, `python test_v80bu_monster_auto.py`, `python test_security.py`, `python test_online_protocol_v80bs.py`, `python test_balance_v80bo.py` pass.
- `ENABLE_GUEST_SANDBOX=1 python test_sandbox_protocol_v80bt.py` only in isolated QA; never set QA flag on production.

## Before concluding the bug is solved
1. Deploy Backend via GitHub root on branch main, verify Render latest Live and `/healthz` says v8.0BV.
2. Deploy Netlify ZIP and force reload/cache refresh.
3. Test **without** `?botstress=1` first. Measure FPS and `Snap gap` with normal walking vs AUTO separately. Add 10/20/30 stress guests after baseline.
4. On actual iPad/mobile Safari, if world still warps report FPS + Snap gap and whether only own character, all other characters, or screen camera moves. Confirm if character died/fell below map and was server-respawned.
5. Separate real latency/packet loss effects from GPU FPS drops. Remote Thailand <-> Render location latency can require further client-side prediction/reconciliation, testing and infrastructure choices. The v8.0BV interpolation prioritizes stable visuals over minimal input delay.
