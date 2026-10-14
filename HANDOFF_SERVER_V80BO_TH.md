# Project Jianghu Server v8.0BO - Handoff
Date 2026-10-14 (Asia/Bangkok)

This ZIP is **SERVER ONLY**, not the Netlify client game. It contains current GitHub backend files with server.py patched for authoritative v8.0BN-style combat reference. To deploy, upload extracted files into the root of GitHub repo `tanutspp-lgtm/projectjianghu` on branch `main`. Render auto-deploys source from there.

### Source-of-truth / boundaries
- PvP first sets player HP. PvE raw mob attack derives from PvP HP and armor DEF/(250+DEF). `server.py` hardcodes pinned approved anchors plus a read-only lookup to Supabase, with local fallback if lookup fails.
- 60 HP reference records & 360 monster attack records were created in Supabase. These are not player account state.
- Rate control is server authoritative: per-action cool, monotonic 2nd check, packet/action rate limits, duplicate/replay rejection. Attack spam has no queued extra attacks.
- Guest Online remains demo Lv5, with original simple arena monster spawning, mob HP and AI; NOT complete online Lv1-60 level/map/gear progression. Offline main game remains separate Netlify ZIP.
- Do not overwrite a newer manually edited server.py in repo without comparing first. Last compared against GitHub main server.py from this turn (guest-only v7.6 era).
- Additional future implementation: full authoritative inventory/equip/skills/monster AI, PvP stats, dynamic zone levels, hit-frame validation, SP, attack-speed from weapon data, real browser QA, anti-cheat load testing.

### QA
- Run `python test_balance_v80bo.py` and `python test_security.py` after installing requirements.
- Check Render live version by inspecting deploy SHA + logs; /healthz existing text is not a version indicator.
- No claims of verified production deployment or end-to-end Netlify testing.
