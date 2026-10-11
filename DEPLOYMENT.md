# Deployment preparation (no deployment performed)

Repository นี้เตรียมเป็น monorepo สำหรับ Vercel + Render แต่การสร้าง/เชื่อม project และการ Deploy ต้องทำหลังได้รับอนุญาตแยกต่างหาก

## Vercel — static client

ตั้งค่าหลังได้รับอนุญาต:

1. Import GitHub repository `tanutspp-lgtm/projectjianghu`.
2. ตั้ง **Root Directory** เป็น `client`.
3. เลือก Framework Preset เป็น **Other** และไม่ต้องมี Build Command.
4. ใช้ `.` เป็น Output Directory หากหน้าตั้งค่าบังคับให้กรอก; โดยปกติปล่อยค่าเริ่มต้นสำหรับ static files ได้.
5. ก่อน Production ให้กรอกค่าฝั่ง browser ใน `client/online_config.js`:
   - `window.WUXIA_ONLINE_SERVER` = Render WebSocket URL แบบ `wss://.../ws`
   - `window.WUXIA_SUPABASE_URL` = Supabase project URL
   - `window.WUXIA_SUPABASE_PUBLISHABLE_KEY` = public/publishable key เท่านั้น

ห้ามใส่ `SUPABASE_SECRET_KEY` หรือ service-role key ใน Vercel/client. Repository นี้ไม่ได้ทำ build-time env injection ดังนั้น Vercel Environment Variables จะไม่แทนค่าใน `online_config.js` เอง.

## Render — Python WebSocket server

ใช้ `render.yaml` ที่ root หรือกำหนด service ด้วยค่าเดียวกัน:

- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `python server.py`
- Health Check: `/healthz`
- Auto Deploy: ปิด (`autoDeployTrigger: off`)

ตั้ง Environment Variables ใน Render Dashboard โดยไม่ commit ค่า secret:

- `ALLOWED_ORIGINS` — origin ของ Vercel ที่อนุญาต คั่นหลายค่าด้วย comma และต้องตรงแบบ exact origin
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY` — key ที่ server ใช้ตรวจ access token
- `SUPABASE_SECRET_KEY` — server-only secret สำหรับ durable persistence/RPC
- `MAX_GUESTS` — ค่าเริ่มต้น 35

อย่าตั้ง `LOCAL_DATABASE_PATH` ใน Production บน instance แบบ ephemeral; ใช้ Supabase persistence แทน. ก่อนเปิด account mode ต้อง apply migration `supabase/migrations/20261011090000_v7_9n_accounts_characters_exp.sql` กับ Supabase โดยตรวจทาน SQL ก่อนทุกครั้ง.

## Release gate

- รันชุดทดสอบ local ตาม `README.md` ให้ผ่าน; หากเพิ่ม GitHub Actions ภายหลังให้ตรวจ required checks ก่อน Merge
- ตรวจ Vercel preview/Render staging เฉพาะเมื่อได้รับอนุญาต
- Production ต้องได้รับอนุญาตก่อน Merge เข้า `main` หรือสั่ง Deploy/Promote
