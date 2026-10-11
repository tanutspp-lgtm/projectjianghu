# v7.9N account, persistence and EXP boundary

## What is working locally

- The v7.9M browser game, sprites, combat inputs, movement, collision, ladder/rope logic, map, parallax, loading gates and mobile controls are preserved.
- Guest online mode remains compatible with the original `{t:"join", avatar}` handshake.
- Account mode sends a Supabase access token in the first WSS message, never in the URL. The server verifies it through Supabase Auth and requires refresh before expiry.
- One permanent character per account is created or loaded by the authoritative server. Avatar/name are immutable in this slice; a later character-management screen can add explicit rename/customize operations.
- Character EXP is computed only from server-observed monster deaths. The client cannot submit EXP, level, damage, HP, coordinates or reward events.
- Damage contribution must be recent and at least 10% of the monster's maximum HP. Each eligible character receives its proportional share; a kill cannot multiply its base reward across helpers.
- Reward event IDs are unique per server process/monster life. The persistence ledger makes retrying the same event idempotent.
- Level calculation uses `BIGINT`/Python integers, supports crossing multiple levels in one award and caps at Lv60 / 237,308,585 total EXP for `exp_v1`.
- The browser HUD shows Character EXP and reserves a safe-area-aware tracked Qi EXP location without implementing Qi progression.

## Boundaries

```text
Browser UI/render/input
  └─ exact JSON protocol (protocol.py)
       └─ authoritative world/combat (server.py)
            ├─ pure EXP rules (progression.py)
            ├─ token verification (auth.py)
            └─ durable adapters (persistence.py)
                 ├─ SQLite for local tests
                 └─ Supabase REST + transactional RPC for production
```

World position/HP are not written to Postgres every tick. Durable writes occur on character creation and validated EXP rewards.

## Supabase setup (not applied automatically)

1. Review `supabase/migrations/20261011090000_v7_9n_accounts_characters_exp.sql`.
2. Apply it to a development/staging project first. It creates only `characters`, `character_exp_ledger` and the server-only `award_character_exp` RPC. It does not alter the four existing `exp_v1` config tables.
3. Set server environment variables from `.env.example`. Use either a modern secret key or the legacy service-role key only on the server.
4. Put only the Supabase URL and publishable key in `client/online_config.js`.
5. Configure Auth redirect URLs/email confirmation and `ALLOWED_ORIGINS` for the intended client origin.

The migration enables RLS, permits authenticated users to select only their own character, provides no client write policies, and revokes the `SECURITY DEFINER` reward RPC from `public`, `anon` and `authenticated` before granting it only to `service_role`.

## Reproducible local checks

From the repository root, using Python 3.11+ with `server/requirements.txt` installed:

```text
python tools/verify_bundle.py
cd server
python test_protocol.py
python test_progression.py
python test_persistence.py
python test_account_mode.py
python test_security.py
python test_idle_resume.py
python test_auto_unit.py
python test_auto_mode.py
```

Serve the browser client through HTTP:

```text
cd client
python -m http.server 8000
```

## Not yet production-verified

- The supplied migration has not been applied to the live Supabase project.
- Real Supabase signup/email confirmation/token rotation and PostgREST persistence require project credentials and a staging run.
- Render/Netlify and live multi-device round trips were not run or deployed.
- Guest-to-account migration, multiple character slots, inventory, Qi progression, profession/crafting and Skill Tree remain later phases.
- Multi-instance world routing is unchanged; do not scale the current process horizontally without explicit session/channel routing.
