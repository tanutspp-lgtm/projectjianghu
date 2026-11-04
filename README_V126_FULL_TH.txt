JIANGHU FRONTEND V126 / BACKEND V126 / World V39
ฐาน Frontend V125 + Backend V124
Feature: world-maps-v126-fishing-courtyards-v1

เปลี่ยนเฉพาะหมู่บ้านชาวประมง fishing_village_9:
- ลานหมู่บ้านราบ x0–880, y430
- บันไดหินสั้น x880–1040 ลง60หน่วย (10ขั้น ขั้นละ6หน่วย)
- ลานกลางราบ x1040–1640, y490
- บันไดหินสั้น x1640–1800 ลง60หน่วย
- ลานท่าเรือ x1800–2400, y550; ดินจบ1950แล้วต่อท่าไม้เดิม
- ใช้ tileset เดิมที่แปลงธีมใน V125 และวาดให้ตรง collision
- ยังไม่เพิ่มบ้าน แพลตฟอร์มลอย พร็อพ หรือระบบขึ้นเรือ
- ฉากหลัง เรือ ความกว้าง2400 และแมพอื่นคงเดิม
- ย้าย spawn/จุดกลับหาดให้ตรงลานใหม่ทั้งสองทิศ อัปเดตมินิแมพ

ต้องใช้ frontend/backend ชุดนี้คู่กัน เพราะ geometry เปลี่ยน
Sync world_v56.js, WORLD_V56_GEOMETRY.json และ backend world_v56.json แล้ว
server.py และโค้ด Python อื่นไม่เปลี่ยน

ตรวจผ่าน: frontend physics 30Hz เดินเต็มเส้นทางไปกลับ, backend update_guest เดินเต็มเส้นทาง,
AUTO เดินขึ้นลงบันไดทั้งสองทิศ, WebSocket handshake/วาร์ปหาด↔หมู่บ้าน,
ข้อมูล47แมพตรงกัน และแมพอื่นคงเดิม
ตรวจภาพจาก renderer จริงและมินิแมพ; browser มี FPS ต่ำ ไม่ได้ใช้ยืนยันประสิทธิภาพ60FPS

ติดตั้ง: ใช้ ZIP ตัวเต็ม แยก frontend และ backend; index.html/assets และ server.py อยู่ที่root
หรือใช้ JIANGHU_V126_CHANGED_FROM_FE125_BE124.zip ซึ่งแยก FRONTEND_CHANGED/BACKEND_CHANGED
คัดลอกแต่ละโฟลเดอร์ทับชุดฐานที่ถูกต้อง อย่านำโฟลเดอร์ครอบไปเป็นrootของเว็บไซต์
