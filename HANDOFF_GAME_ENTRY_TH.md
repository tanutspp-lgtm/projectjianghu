# นำตัวละคร Seven Wind เข้าเซิร์ฟเวอร์เกมจริง

ใช้ชุดนี้กับเกมตัวเต็มที่มีหน้า character.html และ Backend V223 (healthz มี gm-announce-v223) หากมีการแก้ไฟล์เกมหลังรุ่นนั้น ให้เทียบความต่างก่อนรวมแพตช์เพื่อรักษางานที่เพิ่มเข้ามา

**Frontend** ลงไฟล์หน้าเว็บและบัญชีจากแพตช์หลักที่ root ของเกมตัวเต็ม แล้วทับ character.html และเพิ่ม sw-game-runtime.json จาก frontend/ ที่ root เดียวกัน หน้าเว็บ หน้าเลือกตัวละคร และหน้าเกมต้องใช้ origin เดียวกัน ผู้เล่นเริ่มที่ index.html เลือกตัวละครที่ roster.html แล้วเข้าผ่าน character.html ตัวเกมต่อ wss://147-50-231-61.sslip.io/ws อัตโนมัติ ไฟล์ sw-game-runtime.json ใช้ระบุว่าชุดเกมเต็มถูกติดตั้ง ให้ลงไฟล์นี้พร้อม runtime เท่านั้น

**Hostatom** วาง backend/server.py และ backend/roster_admission.py ข้างไฟล์เกมเดิมใน repository ของ backend แล้ว commit และ push ก่อนรันบน host

```sh
cd /opt/jianghu
git pull --ff-only
.venv/bin/python CHECK_BEFORE_RESTART.py
.venv/bin/python -c 'import server, roster_admission; assert roster_admission.TERMS_VERSION == "sw-3"; print("roster-v1 ready")'
bash RESTART_AND_VERIFY_V187_6.sh
curl -fsS http://127.0.0.1:8765/healthz
```

ผล healthz ของโปรเซสใหม่ต้องมี JIANGHU_BACKEND_ROSTER_V1 และ roster-v1 หากตั้ง ALLOWED_ORIGINS อยู่ ให้รวม origin ของโดเมน frontend ที่ใช้จริงไว้ในค่าของบริการก่อน restart เซิร์ฟเวอร์ต้องเชื่อมต่อ HTTPS ออกไปยัง uxxkyptoocbswedwizct.supabase.co ได้ แพตช์ใช้ publishable key ของโปรเจกต์เดียวกับ frontend และตรวจผู้ใช้กับ auth/v1/user ตรวจการยอมรับ sw-3 และอ่านตัวละครผ่านสิทธิ์ RLS ของผู้เล่น

สำหรับผู้เล่นที่ยังไม่ได้ล็อกอินหรือยอมรับข้อตกลง เซิร์ฟเวอร์ปฏิเสธการเข้าโลกโดยตรง การตัดการเชื่อมต่อจะปล่อยช่องให้ตัวละครเดิมเข้าใหม่ได้ ตัวละครหนึ่งตัวเข้าโลกได้ครั้งละหนึ่งการเชื่อมต่อในโปรเซส Hostatom ปัจจุบัน ระบบทดสอบเก่าเปิดเฉพาะกรณีที่ผู้ดูแลตั้งใจตั้ง SW_ALLOW_LEGACY_GUESTS=1 หรือเปิด ENABLE_CHANNEL_STRESS ในสภาพแวดล้อมทดสอบ ให้ใช้ค่าเริ่มต้นเมื่อเปิดให้ผู้เล่น

ฐานข้อมูลรอบนี้เก็บตัวตนและรูปลักษณ์ของตัวละคร การต่อสู้ ค่าประสบการณ์ อุปกรณ์และกระเป๋าระหว่างเล่นยังใช้กลไกเดิมของ Backend V223 ที่เก็บในหน่วยความจำระหว่างเซสชัน
