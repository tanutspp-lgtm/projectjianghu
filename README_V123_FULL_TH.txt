Project Jianghu — Frontend V123 / Backend V123 (World V37)
ฐาน Frontend V122 + Backend V122
feature: world-maps-v123-terraced-fishing-village-v1
รวม 47 แมพ (เก็บแมพร่องห้วย V122 ไว้ตามเดิม พักการพัฒนา)

เพิ่ม fishing_village_9: หมู่บ้านชาวประมง · ท่าเรือทะเลตะวันออก กว้าง 2800
ชายหาดน้ำลึก deepwater_harbor_8 ขวาสุด ↔ หมู่บ้านฝั่งซ้าย
เลย์เอ้าอิงโครง Southperry: บ้านบนตลิ่งฝั่งซ้าย / ย่านร้านปลาชั้นล่าง /
ลานสูงกลางเมือง / ชานกระโดด 4 ช่วง / ท่าเรือฝั่งขวา
บ้าน 4 แบบยึดกับพื้นจริง บ้านบนลานสูงตั้งบน terrain platform y290
พื้นหลักมีหลายระดับ 580, 500, 620, 480
บันได x630 และ x1730; พื้นชานกระโดด y355,420,485,550
เรือสำเภาลำใหญ่เป็น BG จอดนิ่งตรงท่า ไม่ใช่ geometry ที่ผู้เล่นเดินบนเรือ
เตรียมตำแหน่งต่อเส้นทางเกาะหิมะไว้; รุ่นนี้ยังไม่มีแมพเกาะหิมะ/การเดินเรือ
หมู่บ้านไม่มีมอนสเตอร์; cap70 คนต่อแมพต่อช่อง ตามพื้นที่เมือง

กฎภาพ: พื้นเดิน/ดิน/ชาน/ท่าเรือวาดจาก terrain tileset แยกจาก BG และตรง collision
BG และ object บ้าน/เรือไม่มีพื้นเดินอบติดมา
asset ใหม่ assets/fishing_v123/; รายละเอียดและ prompt อยู่ ASSET_MANIFEST_V123.json
อ้างอิงเลย์เอ้า https://ms-classic.com/maps/southperry

ทดสอบ: เดินพื้นหลักไปกลับ, บันได 2 ชุดขึ้นลง, jump edges 10 ทิศทาง,
AUTO ครบทุกระดับไปกลับ, WebSocket วาร์ปหาด ↔ หมู่บ้าน,
frontend JS/JSON และ backend geometry ตรงกัน; 47 แมพ; cap70; มอนสเตอร์0
ภาพจริงตรวจด้วย cloud browser; browser ทดสอบจำกัด RAF ประมาณ1Hz
จึงใช้ server tick30Hz ยืนยันฟิสิกส์ และไม่ได้อ้างว่า browser นี้ยืนยัน60FPS
ผลทดสอบ qa/v123/results.json

FULL แตกแล้ว index.html/assets หรือ server.py/world_v56.json อยู่ root
CHANGED มี FRONTEND_CHANGED + BACKEND_CHANGED สำหรับทับฐาน V122
ต้องใช้ frontend/backend V123 คู่กันเพราะเพิ่ม geometry และ warp
