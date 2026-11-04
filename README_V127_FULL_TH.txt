JIANGHU FRONTEND V127 / BACKEND V127 / World V40
ฐาน Frontend + Backend V126
Feature: world-maps-v127-smooth-village-bank-v1

แก้เฉพาะ fishing_village_9 ตามคำติเรื่องขอบพื้น:
1. ทางเชื่อมลาน x880–1040 และ1640–1800 เป็นทางลาดต่อเนื่องแทนขั้นย่อย10ขั้น
   ลานกว้าง430/490/550ยังราบเหมือนเดิม ไม่คืนเนินยึกยักทั้งแมพ
   terrain cache วาด2เท่าและเปิด image smoothing เฉพาะพื้น/ท่าไม้ชุดนี้
2. ปลายตลิ่งข้างท่าไม้มีขอบโค้งและฐานเว้าถอยเข้า ใช้ขอบ alpha ของก้อนหินจาก tileset V125
   ไม่มีรอยตัดสี่เหลี่ยมแนวดิ่ง และไม่สร้าง asset ใหม่

ตำแหน่งวาร์ป spawn ความกว้าง landEnd บ้าน/props/แพลตฟอร์มลอย และแมพอื่นคงเดิม
sync world_v56.js, WORLD_V56_GEOMETRY.json และ backend world_v56.json
server.py และ Python อื่นไม่เปลี่ยน ต้องใช้ frontend/backend V127 คู่กัน

ตรวจ: JS syntax, frontend physics30Hzไปกลับ, backendเดินเต็มเส้นทางไปกลับ,
AUTOไปกลับ, WebSocket feature/วาร์ปหาด↔หมู่บ้าน, geometryตรงกัน,
ภาพรวมจาก rendererจริง มินิแมพ และตรวจแนวนอน/แนวตั้ง
Browser มีFPSต่ำ ไม่ใช้เป็นผลยืนยันประสิทธิภาพ60FPS

แพตช์ JIANGHU_V127_CHANGED_FROM_V126.zip แยก FRONTEND_CHANGED/BACKEND_CHANGED
หรือใช้ ZIP ตัวเต็มทั้งสองฝั่ง (index.html/assets และ server.py ที่ root)
