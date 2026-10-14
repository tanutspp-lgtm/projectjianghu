# Deploy v8.0CE — Backend first
1. GitHub repo root: upload CONTENTS of server ZIP (not the ZIP); include `server.py`, `beast_map_common_v80bq.json`, and all changed modules/tests.
2. Wait Render Live, verify https://projectjianghu.onrender.com/healthz shows v8.0CE.
3. Upload Netlify ZIP, hard-reload Safari. Check title v8.0CE SERVER-FIRST PVE.
4. Test middle ladder hold UP at top, lower ladders/ropes, flute bullets throughout flight, tiny FPS & Ping. `?perf=1` shows detailed profiler.
Security: Do not enable `ENABLE_GUEST_SANDBOX=1` on public Render.
