WUXIA Authoritative Server v7.9N — Guest + Account/EXP vertical slice

Python 3.11+ | websockets>=15,<17
Start locally: pip install -r requirements.txt && python server.py
Health endpoint: http://localhost:8765/healthz
WebSocket endpoint: ws://localhost:8765/ws

For Render.com:
- New > Web Service, Python, repo root containing this server.py
- build: pip install -r requirements.txt
- start: python server.py
- health: /healthz
- env PORT is provided by Render
- env ALLOWED_ORIGINS (optional but recommended) = https://your-site.netlify.app
- env MAX_GUESTS = 20 to 35
- Public URL is wss://<your-service>.onrender.com/ws

World physics remains in memory; 1 server process = 1 world. Guest mode remains available.
With SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY + SUPABASE_SECRET_KEY configured,
the server verifies Supabase Auth tokens and loads/saves one durable character per account.
For local persistence tests, set LOCAL_DATABASE_PATH without Supabase credentials.

The server loads live exp_v1 balance tables when Supabase server credentials are present;
otherwise it loads the read-only CSV snapshots for local tests. EXP rewards are calculated
from server-observed monster deaths and damage contributions. Clients cannot send EXP.

Before enabling accounts, review and apply the additive migration under
supabase/migrations/. Never expose the secret/service-role key to client files.

Security checks include exact message schemas, token verification/expiry refresh,
idempotent reward ledger, ownership checks, cooldowns, sequence/rate checks and
server-owned monsters/HP/damage/positions. This is a vertical slice, not a complete MMO backend.

Run tests from this directory:
python test_protocol.py
python test_progression.py
python test_persistence.py
python test_account_mode.py
python test_security.py
python test_idle_resume.py
python test_auto_unit.py
python test_auto_mode.py
