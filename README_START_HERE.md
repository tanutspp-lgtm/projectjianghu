# PROJECT JIANGHU / WUXIA FLUTE ARENA — Codex Handoff

This is a single, self-contained **source and asset handoff**, compiled 2026-10-11.

## v7.9N development result

This working copy now contains the local v7.9N account / durable character / authoritative EXP vertical slice. Start with `CHANGELOG_V7_9N_TH.md` and `docs/V7_9N_ARCHITECTURE.md` for implemented, untested and credential-dependent boundaries. No deployment or live Supabase migration has been performed.

## Source of truth
- `client/`: **v7.9M** exact runtime browser release extracted from `WUXIA_FLUTE_ARENA_v7_9M_LOADING_SCREEN.zip`. Includes all 30 character full sheets, 30 fast previews, all current forest/platform/ladder/rope pieces, sky/cloud/mountain/parallax backgrounds, FX sheets and data, loading gate and responsive/touch controls. Keep relative paths intact.
- `server/`: **v7.9N WebSocket AUTO PvE + account persistence/EXP** developed from the v7.9 Guest server. Guest behavior and authoritative combat remain available; account joins add Supabase token verification and durable progression. **Do not assume this server matches the deployed Render instance.**
- `database/`: **read-only EXP v1 reference snapshots** of the current Supabase database `project jianghu`; not a personal-data dump and **not** a replacement migration. Only EXP configuration tables exist currently; there is no character persistence schema yet.
- `references/map01_non_runtime/`: optional old map blockout documents, **NOT currently implemented in the client**. Never replace the runtime tileset with concept draft artwork.
- `docs/`: binding game decisions, UX constraints, asset inventory and limitations.
- `CODEX_TASK.md`: initial assignment and acceptance criteria for Codex.

## Run locally
Server (`Python 3.11+`):
```
cd server
python -m pip install -r requirements.txt
python server.py
```
The server listens on `http://localhost:8765/healthz` and `ws://localhost:8765/ws` by default. Without Supabase variables it remains Guest-only; with the documented Supabase variables and migration it enables account persistence and authoritative EXP. Render may alternatively start the root wrapper with `python server.py`.

Browser client: serve `client/` as a static web folder, not via `file://`:
```
cd client
python -m http.server 8000
```
Then open `http://localhost:8000/`. Change `client/online_config.js` to point to a local `ws://localhost:8765/ws` ONLY for local testing (or use the in-game connection UI if present). When using HTTPS production client, WebSocket must be WSS. Do not ship a local-test URL in production. Do not put database secrets in client files.

## Validation
```
python tools/verify_bundle.py
cd server
python test_security.py
python test_idle_resume.py
python test_auto_unit.py
python test_auto_mode.py
```
`test_auto_mode.py` currently starts a local test server and waits only 0.65 seconds; it may have a startup race (connection refused). Do not treat this timing failure as a combat success or silently skip. Run server integration checks and fix flaky harness separately from gameplay.

## Important status
- Authentication, durable character save/load, and server-authoritative EXP from PvE kills are implemented for v7.9N and covered by local tests. Inventory, Profession/Crafting, spendable Qi progression, and cross-map portal persistence remain out of scope.
- Supabase EXP config snapshots are referenced under `database/`, and the required character/EXP migration is under `supabase/migrations/`. Connection credentials are not present and no live migration has been applied.
- No production deployment and no live Render integration test were performed by this bundle creation.
- Game code is primarily monolithic HTML/JS + Python server; progressively modularize rather than rewrite the working game.
- Code/assets are supplied for development; no new generated art was substituted.
