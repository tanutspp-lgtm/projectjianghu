# DEPLOY — v8.0CI Wall Dash Collision Fix

ต้อง Deploy ทั้งสองฝั่ง: **GitHub/Render Backend ก่อน** แล้ว Netlify frontend
1. แตก ZIP Backend; อัปไฟล์ภายในทั้งหมดเข้า root GitHub repo ทับชื่อเดิม; รอ Render `Live`; เช็ก `/healthz` แสดง `v8.0CI`
2. อัป ZIP Netlify ทั้งก้อน (เกมเต็ม). รีเฟรชหน้าเว็บเพื่อให้เห็น v8.0CI
3. ทดสอบ Dash ติดกำแพงทั้งซ้าย/ขวา กระโดดแล้ว Dash ติดกำแพง และเปลี่ยนชั้น. ใช้ตัวเลข FPS/Ping ที่ HUD หากยังมีอาการ
หมายเหตุ: แพตช์นี้แก้ collision ไม่อ้างว่าช่วย FPS. Asset/SFX ไม่มีการปรับเปลี่ยน
