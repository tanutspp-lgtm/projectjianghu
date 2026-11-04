Project Jianghu — BACKEND V108 FULL

ฐาน: Backend V103 FULL
เปลี่ยน world_v56.json เป็น World V28 / world-maps-v108-beach-platforms-v1
เพิ่ม platform + rope geometry ของหาดทั้งสาม ให้ตรงกับ Frontend V108
server.py, world_physics_v56.py และ late_map_nav_v67.py ใช้โค้ดเดิมทุกไบต์
ระบบเดิมโหลด platforms/climbs และ feature จาก world_v56.json ตอนเริ่มเซิร์ฟเวอร์

ชุดเต็มนี้มี server.py และ world_v56.json ที่ root
ใช้คู่กับ Frontend V108; เมื่อนำโลกใหม่ไปใช้ต้องให้ process โหลด world_v56.json ใหม่
ไม่เปลี่ยน HOST/PORT, systemd, environment, network cadence, combat หรือ balance
ดู HANDOFF_JIANGHU_V108_TH.md และ QA_V108_TH.txt
