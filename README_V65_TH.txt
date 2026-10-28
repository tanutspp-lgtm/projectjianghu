PROJECT JIANGHU — FRONTEND V65 / BACKEND WORLD V16

รวมแก้ในชุดเดียว
1. ถ้ำเซียนกระบี่ชั้นบน: แก้เดินข้ามรอยต่อพื้นหิน/สะพานแล้วถูกผลักไปไกลจนกลับทางเข้า
   ขยาย Collision สะพานทับพื้นหิน 12 หน่วย และแยกการชนผนังด้านข้างจากการรับพื้น
   แก้ฟิสิกส์เดียวกันทั้ง JavaScript และ Python; ไม่เปลี่ยนรูปถ้ำ/เส้นทางเดิน
2. แมพ 28 หน้าผาฝั่งป่าใน: ยกเลิก downOnly ทำให้บันไดทั้ง 20 เส้นปีนขึ้นและลงได้
   ไม่เพิ่มทางวาร์ปกลับเข้าถ้ำ จุดเชื่อมแมพยังเหมือนเดิม
3. แมพ 28: ใช้ภาพหินคู่ต่อจากหน้าผาด้านหน้าชุดที่อนุมัติ ณ สเกลเดียวกัน
   เปลี่ยนวิวฝั่งซ้ายเป็นป่าและภูเขาด้านใน ไม่มีทะเล
   ขนาดภาพวิวตามจอ ไม่ขยายภาพให้สูงเท่าแมพ 5400 หน่วย
   ปากถ้ำแยกชิ้นเล็กยึดกับพิกัดโลก ไม่เลื่อนกับวิวหลัง
4. คืน HUD เลือด HP / SP / STA / EXP: คืน hud.css และภาพ 5 ไฟล์ที่หายไปในชุดก่อน
   ไม่เปลี่ยนสูตรค่าสถานะหรือค่าจากเซิร์ฟเวอร์
5. แมพ 30–34: เอาใบไม้โปร่งซ้ายบนออก โดยเก็บด้านขวาและฉากหลักไว้

เก็บงาน V64 เดิม: แมพไต่เขาแมพเดียวแทนของเดิม, บันไดไม้สีน้ำตาล,
แก้สะพานช่องเขาเดินร่วง และปรับรอยต่อดินแมพ 30–34
ไม่เปลี่ยน Scheduler / Self 30Hz / AUTO / Combat / Inventory

ชุด Frontend ตัวเต็ม
ดาวน์โหลด .001 .002 .003 ไว้ในโฟลเดอร์เดียวกัน แล้วเปิด PowerShell รัน:
cmd /c copy /b "JIANGHU_FRONTEND_V65_FULL.zip.001+JIANGHU_FRONTEND_V65_FULL.zip.002+JIANGHU_FRONTEND_V65_FULL.zip.003" "JIANGHU_FRONTEND_V65_FULL.zip"
แตก JIANGHU_FRONTEND_V65_FULL.zip จะเห็น index.html ที่ Root
อัป Frontend ทั้งโฟลเดอร์เข้า Vercel ตามวิธีเดิม ไม่ต้องใช้ GitHub สำหรับ Frontend
ไม่ใช้ ZIP แพตช์ใบไม้เดี่ยว ๆ; ชุดตัวเต็มนี้รวมตัวแก้แล้ว
หลัง Deploy ให้ Ctrl+F5 แล้วออก Guest/เชื่อมต่อใหม่

Backend ใช้ GitHub ตามเดิม
แตก JIANGHU_BACKEND_V65_FULL.zip แล้วอัปเนื้อหาทั้งชุดเข้า Root ของ repo เดิม และ Commit
มี server.py ตัวเต็มและ dependency เดิมอยู่ด้วย; server.py ไม่เปลี่ยนจาก V64 ที่ตรวจ GitHub แล้ว
ไฟล์หลักที่เปลี่ยนการทำงานคือ world_v56.json และ world_physics_v56.py
อย่าอัปโฟลเดอร์ซ้อน ต้องอยู่ระดับเดียวกับ server.py เดิม
ตรวจ GitHub และไฟล์เครื่องจริงก่อนอัปเดต ไม่แตะ .env / .venv / systemd drop-in

เมื่ออัป GitHub แล้ว รันบนเซิร์ฟเวอร์:
cd /opt/jianghu || exit
tar -czf "/opt/jianghu-backup-$(date +%Y%m%d-%H%M%S).tar.gz" --exclude=.git --exclude=.venv --exclude=__pycache__ -C /opt jianghu &&
git pull --ff-only &&
.venv/bin/python CHECK_BEFORE_RESTART.py &&
.venv/bin/python CHECK_WORLD_V65.py &&
systemctl restart jianghu.service &&
systemctl status jianghu.service --no-pager

Feature ต้องตรง
world-maps-v65-cave-seams-inland-climb-v1
granite-ascent-v64-single-map
granite-wall-chain-v64-single-ascent-link
Map11 คง forest-fork-map11-v21-clean-ropes ห้ามปิด Feature check เพื่อฝืนเข้าแมพ
Frontend/Backend ต้องเป็นชุดตรงกัน จึงควรอัปในรอบเดียวกัน

ข้อจำกัดการตรวจ
ทดสอบในเครื่องงาน ไม่ได้ Deploy Vercel หรือ Hostatom ให้
ไม่ได้ยืนยัน FPS/เครือข่ายของเครื่องผู้เล่นหรือภาระบน Hostatom
เก็บไฟล์เดิมทั้งหมดจากชุดตัวเต็ม V64 และคืนไฟล์ HUD ที่ตรวจพบว่าหาย
ไม่มี ZIP เก่าพันกว่าไฟล์ให้เทียบรายการทั้งหมด จึงไม่อ้างว่าได้คืนไฟล์ที่ไม่ทราบชื่อทุกไฟล์แล้ว
เอกสาร V63/V64 ที่เก็บไว้เป็นประวัติ ให้ยึด README_V65_TH.txt และ CHECK_WORLD_V65.py สำหรับชุดนี้

ผลตรวจชุดนี้
- JavaScript Syntax 34 สคริปต์ผ่าน; Python Syntax/Imports ผ่าน
- ภาพต้นฉบับในชุด 638 ไฟล์เปิดถอดรหัสได้; Geometry Frontend/Backend เท่ากัน
- ฟิสิกส์ 238 กรณี 54,620 เฟรม: JS/Python ให้ผลตรงกัน
- เบราว์เซอร์กดปุ่มจริง: บันไดแมพ 28 ขึ้น/ลง 40 เที่ยว และเดินข้ามรอยต่อถ้ำ 6 รอบผ่าน
- Backend update_guest: บันได 40 เที่ยวผ่าน
- Online Guest ทดสอบในเครื่องผ่านเบราว์เซอร์และ Backend จริง: วาร์ปครบ 34 แมพ
  ไม่พบ JavaScript error หรือ HTTP request หาไฟล์ไม่เจอระหว่างทดสอบ
- ZIP ตรวจ CRC และ index.html / server.py อยู่ที่ Root; พาร์ทรวมได้ SHA256 ตรงตัวเต็ม
