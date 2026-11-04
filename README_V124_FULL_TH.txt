Project Jianghu — V124 พื้นหมู่บ้านชาวประมง (ฐาน V123)
Frontend V124 / Backend World V38; 47 maps
feature: world-maps-v124-fishing-bank-groundwork-v1

รอบนี้ทำเฉพาะพื้นตลิ่ง ฉากหลัง และทางลาดไปท่าเรือ
fishing_village_9 กว้าง 2400; ตลิ่งดินอัดสีเทาน้ำตาลปนหิน
แทรกหินปูบนลาน และกำแพงกันดินตามหน้าตลิ่ง
เอาลานลอย ชานกระโดด บันได และบ้านออกจากการวางทั้งหมด
มี terrain ต่อเนื่องชิ้นเดียวตาม profile; platforms[0] เป็นข้อมูลพื้นหลัก
พื้นไม้ท่าเรือเริ่ม x1950 ต่อจากฝั่ง y550 เดินได้ตาม collision
เรือเป็น BG จอดนิ่ง; ยังไม่เปิดระบบเดินเรือไปเกาะหิมะ
ไม่ใช้ sand BG หรือ sand terrain ของหาดในการวาดหมู่บ้าน
พื้นเดินและเนื้อดินทั้งหมดใช้ material tiles แยกจาก BG และตรง collision

แก้ geometry ให้ frontend world_v56.js / WORLD_V56_GEOMETRY.json / backend world_v56.json ตรงกัน
ต้องใช้ frontend/backend V124 คู่กัน
server.py เดิมจาก V123; cap70 ของหมู่บ้านคงเดิม
วาร์ปหาด↔หมู่บ้านทดสอบทั้งสองทิศ; เดินจาก入口ถึงท่าแล้วกลับผ่าน
แมพอื่นและร่องห้วยพักไว้ตามเดิม
ผลทดสอบ qa/v124/results.json
ภาพตรวจจริงใน cloud browser; ไม่อ้างผล60FPSจากเครื่องทดสอบนี้

FULL แตกแล้ว index.html/assets หรือ server.py/world_v56.json อยู่ root
CHANGED มี FRONTEND_CHANGED และ BACKEND_CHANGED สำหรับฐาน V123
