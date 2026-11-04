Project Jianghu — V122 ทดลองร่องห้วยแห้ง (ฐาน Frontend V121 / Backend V121)
Frontend V122 / Backend World V36 — 46 แมพ
feature: world-maps-v122-dry-ravine-prototype-v1

เพิ่ม dry_ravine_5 ชื่อ ร่องห้วยแห้ง · สะพานไม้เก่า กว้าง 2060
ทางเลียบค่ายโจร bandit_road_4 ขวาสุด ↔ ร่องห้วยแห้ง ฝั่งซ้าย
เส้นบนเป็นสะพานไม้ y550 เส้นล่างเป็นก้นห้วย y760 มีพื้นลาดสองฝั่ง
บันไดไม้ x800 และ x1260 กดขึ้น/ลงเชื่อมสะพานกับก้นห้วย
ใช้ terrain tileset เดิมวาดพื้นให้ตรง collision; สะพาน/บันไดเป็นชิ้นแยกจาก BG
ยังไม่มีทางออกขวาไปพื้นที่ใหม่ ไม่มี NPC หรือมอนสเตอร์ใหม่

Frontend/Backend ต้องใช้คู่ V122 เพราะเพิ่ม geometry และ warp
world_v56.js, WORLD_V56_GEOMETRY.json และ backend world_v56.json ตรงกัน
server.py ไม่เปลี่ยนจาก V121
ทดสอบด้วย server tick จริง: เดินสะพาน/ก้นห้วยสองทิศ พื้นลาดขึ้นสองฝั่ง
บันไดสองชุดขึ้นลง AUTO สลับชั้น และ WebSocket portal ไปกลับ ผ่าน
เปิดภาพจริงด้วย browser แล้ว; อัตรา RAF ใน browser ทดสอบถูกจำกัดราว 1 Hz
จึงไม่ได้ยืนยันความลื่น 60 FPS จาก browser นี้

ไฟล์ FULL แตกแล้ว index.html/assets หรือ server.py/world_v56.json อยู่ root
ไฟล์ CHANGED มี FRONTEND_CHANGED และ BACKEND_CHANGED สำหรับทับฐาน V121
