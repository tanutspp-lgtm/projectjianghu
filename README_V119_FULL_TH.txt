Project Jianghu — Frontend V119 FULL + Backend V119 FULL
ฐาน V118 / World V34 / world-maps-v119-bandit-ground-homes-v1 / รวม44แมพ

ตามคำสั่งผู้ใช้:
- เอาแพลตฟอร์มยกระดับ8แผ่นและเชือก8เส้นออกจากสามแมพค่ายโจรทั้งหมด
- คงเฉพาะพื้นหลักแบบslopeเดิม บ้านทุกหลังยึดกับพื้นจริง
- กำแพงรั้วไม้และป้อมอยู่ในrear scenery pass สีหม่นอยู่หลังบ้าน
- เพิ่มบ้านพักโจร4แบบใหม่: เพิงหลังคาลาด บ้านฝาดิน กระท่อมไม้ไผ่ เรือนนอนไม้
- ประตูค่ายใหม่เป็นPNGช่องเปิดโปร่งใสจริง มองเห็นบ้านค่ายด้านในผ่านช่องประตู
- คงพื้นเดิม ความกว้างแมพ จุดspawn จุดwarpทุกจุด และแมพอื่นทั้งหมด
- ไม่เพิ่มสำนัก ศัตรู บอสหรือเควสต์ รอบนี้ทำฉากพื้นบ้านกำแพง

ใช้Frontend119คู่Backend119เพราะถอดplatform/climbจากgeometry
world_v56.js/WORLD_V56_GEOMETRY.json/backend world_v56.jsonตรงกัน
server.pyและPythonอื่นตรงBackend118ทุกbyte ไม่เปลี่ยนphysics/netcode/combat

QA: browserและbackendเดินพื้นสามแมพไปกลับ, วาร์ป6ทิศทางผ่าน
server AUTOบนพื้นผ่านทุกแมพ, ไม่มีแพลตฟอร์มหรือclimbค้างในข้อมูล
ภาพเกมจริง2ขนาดจอ ภาพoverview3แมพ และมินิแมพ44ภาพdecodeผ่าน
ตรวจalphaช่องประตู=0 และบ้านทุกหลังอยู่ที่groundYจริง; ZIP CRCผ่าน
ไม่ได้deployหรือทดสอบVPSจริง

แตกตัวเต็มได้index.html/assets หรือserver.py/world_v56.jsonที่root ไม่ต้องลงแพตช์เพิ่ม
