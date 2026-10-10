WUXIA Guest-Only Authoritative Server v7.6

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

State exists in memory; 1 server process = 1 world. Guest-only, no login/persistent profile.
Security checks include strict input schema, cooldowns, sequence and packet rate checks, server-run monsters/HP/damage/positions. This is an early anti-cheat foundation, not a production security guarantee.

Run tests: python test_security.py
