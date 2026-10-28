PROJECT JIANGHU — FRONTEND V64 / BACKEND WORLD V15

สิ่งที่เปลี่ยน
1. ใช้แมพหน้าผาใหม่ช่วงล่างเพียงแมพเดียว แทน granite_ascent_1 เดิมโดยใช้ ID/ตำแหน่งเมนูเดิม
   สูง 2400 หน่วย มีพื้น/แพลตฟอร์ม 11 ชุด และบันได 10 เส้น
   ถอด granite_ascent_lower / granite_ascent_upper ออกจากเมนูและ Backend เหลือรวม 34 แมพ
   Map11 ทางแยกบน -> ทางไต่ผาใหม่ -> ระเบียงผา เชื่อมไปกลับแล้ว
   วาปบนสุดเปลี่ยนจาก Y=-4250 เป็น Y=-1850; จุดคืนจากระเบียงผาอยู่ [1225,-1850]
2. บันไดทั้งโซนหน้าผา 40 เส้นใช้ชนิดไม้สีน้ำตาลหัวเรียบตามภาพอ้างอิง
   ครอบคลุมทางไต่ผา, ระเบียงผา, ผารอยแยก, ยอดเขา และหน้าผาฝั่งป่าใน
   ไม่เปลี่ยนเชือกของโซนป่า/ถ้ำ/แมพทางไปทะเล
3. แก้การเดินร่วงที่สะพานช่องเขา ด้วย Collision สะพานรับตัวละครก่อนพื้นลาดด้านล่าง
   จำกัดการเปลี่ยนพฤติกรรมไว้ที่แพลตฟอร์ม continuousDeck ของสะพานนี้เท่านั้น
   รูปสะพาน/พิกัด/พื้นใต้สะพานคงเดิม และยังลงไปพื้นที่ด้านล่างได้จากทางที่เข้าถึงได้
4. แมพ 30–34 ใช้เนื้อดินจาก tileset เดิม ประกอบ Texture แบบเหลื่อมและผสมขอบ
   ตัดกรอบจากบริเวณต้นทางที่ใช้วาดใน renderer; ไม่แก้/ครอปไฟล์ Asset ต้นฉบับ
   เชื่อมผิวใต้หญ้ากับเนื้อดินแบบไล่น้ำหนัก และเติมเงาตามแนวขอบ
   วาดแถบผิวตามรูปทรงลง Canvas ชั้นเดียวเพื่อลบรอยต่อย่อยจาก subpixel
   คำนวณแล้ว Cache ต่อแมพ; ไม่สร้าง Texture ใหม่ทุกเฟรม

ฐานไฟล์
Frontend ตัวเต็มมี Asset และสคริปต์จากชุด V63 เดิมทั้งหมด พร้อมเก็บภาพเก่า 3 ชื่อที่มี HD/ภาพแก้ถ้ำแทนไว้ด้วย
ไม่ได้ลบ Asset เดิมหรือแก้ไบต์ของไฟล์ Asset เดิม
ยังไม่มี ZIP ต้นฉบับพันกว่าไฟล์มาเทียบรายการทั้งหมด; ไม่อ้างว่ารวมไฟล์ที่ไม่ถูกอ้างอิงและไม่ทราบชื่อจากฐานเดิมได้ครบ
Backend ใช้ชุดเต็ม V63 ที่ดึงจาก GitHub เป็นฐาน ตรวจ server.py ล่าสุดยังเป็น blob d7f269f472cf9083ad0baee0970a7da7954bbc78 ก่อนแก้
server.py เปลี่ยนเฉพาะ geometry ทางไต่ผา, จุดวาปเชื่อมระเบียง และ Feature ที่บอก Geometry รุ่นใหม่
world_physics_v56.py เปลี่ยนเฉพาะลำดับรับพื้นของสะพานที่ติดธง continuousDeck
ไม่มีการเปลี่ยน Scheduler, Self 30Hz, AUTO, Combat, Inventory หรือการตั้งค่า Service

Feature ต้องตรงทั้ง Frontend/Backend
world-maps-v64-single-ascent-bridge-v1
granite-ascent-v64-single-map
granite-wall-chain-v64-single-ascent-link
Map11 คง forest-fork-map11-v21-clean-ropes ห้ามข้าม Feature check

Frontend ตัวเต็ม 3 พาร์ท
ดาวน์โหลด .001 .002 .003 ไว้โฟลเดอร์เดียวกัน
เปิด PowerShell ในโฟลเดอร์ไฟล์ แล้วรัน:
cmd /c copy /b "JIANGHU_FRONTEND_V64_FULL.zip.001+JIANGHU_FRONTEND_V64_FULL.zip.002+JIANGHU_FRONTEND_V64_FULL.zip.003" "JIANGHU_FRONTEND_V64_FULL.zip"
จะได้ ZIP ที่มี index.html ที่ Root พร้อม Asset โดยไม่ต้องใช้ ZIP ฐานเพิ่ม
Deploy Frontend V64 และ Backend V64 ให้ตรงกัน แล้วออก Guest และเชื่อมต่อใหม่

Backend: ใช้วิธีอัปผ่าน GitHub ตามเดิม
แตก JIANGHU_BACKEND_V64_FULL.zip แล้วอัปไฟล์ที่ Root เข้า repo เดิม และ Commit เข้า main
ตรวจว่า server.py, world_v56.json, world_physics_v56.py และ CHECK_WORLD_V64.py ขึ้นครบ
ไม่ย้าย .env/.venv/systemd drop-in ของ Hostatom และไม่รันทับเครื่องจริงก่อนเทียบ/สำรองไฟล์เดิม
เมื่ออัป GitHub แล้ว รันบนเซิร์ฟเวอร์:
cd /opt/jianghu || exit
tar -czf "/opt/jianghu-backup-$(date +%Y%m%d-%H%M%S).tar.gz" --exclude=.git --exclude=.venv --exclude=__pycache__ -C /opt jianghu &&
git pull --ff-only &&
.venv/bin/python CHECK_BEFORE_RESTART.py &&
.venv/bin/python CHECK_WORLD_V64.py &&
systemctl restart jianghu.service &&
systemctl status jianghu.service --no-pager
หาก Git แจ้ง conflict หรือ check ไม่ผ่าน ให้หยุดตรวจข้อความนั้นก่อน

ตรวจแล้ว
- Syntax, Asset, ZIP CRC และ root entry points
- ข้อมูล Frontend/Backend ตรงกัน; แมพอื่นไม่เปลี่ยน Geometry
- Frontend 34 แมพใน JSDOM/native Canvas, ไม่มีไฟล์ภาพอ้างอิงขาด
- ปีนบันไดแมพแทนที่ขึ้น/ลง 20 traversals ด้วย update() ของเกม
- ตรวจการวาดบันได 40 เส้นว่าทุกเส้นใช้ชนิดอ้างอิง
- Physics 174 กรณี (เดิน/ลงสะพาน 47, พื้นใต้สะพาน 7, Regression 120)
  JavaScript กับ Python ผลตรงกัน โดยไม่มีความต่างของพิกัด
- WebSocket บนเครื่องทดสอบ: Selector ครบ 34 แมพ, วาปเดิมที่เชื่อมแมพใหม่ไปกลับ,
  และปฏิเสธวาปที่ความสูงเก่า รวม 39 กรณี
  การทดสอบวาปตั้งตำแหน่งและล้าง cooldown/rate window ระหว่างเคสผ่าน fixture ฝั่งเซิร์ฟเวอร์
- รูปพรีวิวเป็นภาพจาก Asset/Renderer จริง ไม่ใช่ภาพยืนยันการเล่นเกมออนไลน์
ข้อจำกัด: ยังไม่ได้ทดสอบเบราว์เซอร์จริง, FPS/Live Online บน Hostatom หรือ Deploy
ชุด V64 นี้ยังไม่ได้ Push/Commit ให้บน GitHub และไม่ได้ Restart เครื่องจริง
