# Project Jianghu — v7.9N

เวอร์ชันนี้พัฒนาต่อจากเกมเดิม โดยเพิ่มบัญชีผู้เล่น การบันทึกตัวละครถาวร และ EXP แบบ server-authoritative โดยไม่เปลี่ยน Sprite หรือระบบต่อสู้เดิมโดยไม่จำเป็น

## โครงสร้าง Repository

- `client/` — Static browser game สำหรับตั้ง Vercel Root Directory
- `server/` — Python WebSocket server, persistence/auth/progression modules และ tests
- `server.py` + `requirements.txt` — Root entrypoint เดิมสำหรับ Render
- `database/` — EXP balance snapshots ที่เกมใช้
- `supabase/migrations/` — Schema/RPC สำหรับ durable characters และ idempotent EXP
- `render.yaml` — Render Blueprint ที่ปิด auto-deploy ไว้

อ่าน [README_START_HERE.md](README_START_HERE.md), [CHANGELOG_V7_9N_TH.md](CHANGELOG_V7_9N_TH.md) และ [DEPLOYMENT.md](DEPLOYMENT.md) ก่อนรันหรือเชื่อมบริการจริง

## ทดสอบในเครื่อง

```powershell
python -m pip install -r requirements.txt
python tools/verify_bundle.py
python -m compileall -q server.py server
python test_render_entrypoint.py
python server/test_protocol.py
python server/test_progression.py
python server/test_persistence.py
python server/test_account_mode.py
python server/test_security.py
python server/test_idle_resume.py
python server/test_auto_unit.py
python server/test_auto_mode.py
node client/test_account_client.js
```

โปรเจกต์นี้ยังไม่อนุญาตให้ Deploy Production หรือ Merge เข้า `main` โดยอัตโนมัติ
