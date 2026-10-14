# Deploy order for v8.0CD
1. Extract contents of PROJECT_JIANGHU_SERVER_v8_0CD_SHOTS_LADDER_PROTOCOL_GITHUB.zip and upload all files to root of GitHub repository `tanutspp-lgtm/projectjianghu` (not the ZIP archive). Overwrite server.py and beast_map_common_v80bq.json. Commit.
2. Wait for Render to show Live; `https://projectjianghu.onrender.com/healthz` MUST contain `v8.0CD`.
3. Upload Netlify package WUXIA_FLUTE_ARENA_v8_0CD_SHOTS_LADDER_FIX_NETLIFY.zip. This frontend checks `mapClimbs` and refuses to run on old mismatched server. This is intentional for safety.
4. Refresh Safari, test middle ladder and magic projectile range. New local test scripts included. Do not enable Guest sandbox on public Render.
