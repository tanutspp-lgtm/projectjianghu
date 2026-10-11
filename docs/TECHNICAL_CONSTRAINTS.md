# Platform / runtime architecture requirements

## Existing
- `client/index.html` single large source with Canvas/web rendering and character creator; `client/online_config.js` is currently empty. All image filenames under `client/` must remain valid relative to this HTML.
- 30 full sprite sheets: `client/characters/`, each 6 columns by 4 rows (24 frames; source frame ~256x256; sheet 1536x1024). 30 two-frame small previews: `client/character_previews/`.
- Forest gameplay atlas: `client/assets/forest/forest_master_original.png` and sliced runtime tiles; collisions currently determined by code, not by generated image colors. Foreground parallax/backdrops in `client/assets/backgrounds/`.
- Python 3.11+ WebSocket server `/ws`, `websockets>=15,<17`. 30Hz world tick; Guest only, server owns mob HP/position/combat; no permanent profile yet. Code has world geometry, monster set, and current AUTO PvE.
- Browser hosts via static deployment (historically Netlify), runtime Game Server on Render, Supabase Postgres for future persistence. Do NOT equate Render build to database migrations.

## Future platform policy
- Shared protocol + authority: browser, Windows, macOS, iOS/iPadOS and Android use SAME accounts, shared assets/gameplay protocol, and same server authority. Never duplicate authoritative XP/damage/item logic per client platform.
- Separate gameplay model/network from rendering, user interaction, and host platform adapters incrementally. A desktop/mobile wrapper may be considered later; do not lock into packaging technology now.
- Responsive HUD anchored to normalized viewport/safe area; handle varying phone/tablet sizes, aspect ratios, notches, screen rotation, different DPI and touch-target sizes. Side-scroller gameplay prioritizes landscape; login/menus may support portrait separately.
- Preserve world units, collision and PvP fairness regardless of viewport; don't reveal unfair extra world for wider screens.
- Input abstraction handles keyboard/mouse and multi-touch; movable/sizable virtual joystick/buttons are long-term target. Touch multi-finger combinations must not trigger ladder/auto errors. Avoid adding 6-7 dedicated combat buttons on narrow screens.
- Handle slow first load: v7.9M loading screen preloads 30 previews before character creator; when entering world preloads selected full sheet and world assets before letting player play. Keep resource loading architecture and progress UX.
- Server uses durable DB for accounts, progression, inventory, transaction ledger, skill points, etc.; world physics/combat/snapshots remain primarily in memory. Never write position/HP to Postgres every tick. Plan idempotent reward awarding, retries, disconnections, rate limits and secure credential handling.
- Horizontal scaling will need map instances/channels/explicit session routing. Simply scaling the current single process will not automatically make one shared world.

## Security
- Client is NEVER trusted to award itself experience, gold, Qi, cards, items or skill points. Validate all kill rewards server-side.
- Do not store `SUPABASE_SERVICE_ROLE_KEY`, database connection URI or other secrets in JS, screenshots, ZIP or GitHub. Use server environment variables. Client can have intentionally PUBLIC Supabase URL/publishable key only if appropriate. Treat SQL RLS, auth token validation, service role separation seriously.
- Existing Supabase project `project jianghu` ref `uxxkyptoocbswedwizct` (public non-secret project identifier). The only created public schema tables as of this handoff are 4 EXP balance config tables. No player tables yet.
