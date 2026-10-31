Project Jianghu — Frontend V67 / Backend World V18
วันที่ 29 ตุลาคม 2026

ตัวเต็มสำหรับอัปโฟลเดอร์เข้า Vercel; index.html อยู่ Root
ต้องใช้ Backend V67 คู่กัน Feature: world-maps-v67-late-regions-v1

ปรับเลย์เอ้า 8 แมพ ใช้สเกลตัวละครและ Asset เดิม:
- ทุ่งหญ้าเลียบธาร: กว้าง 5,400; ชานเหลื่อมระดับและเกาะกระโดด
- ทางเกวียนร้าง: 6,200; ทางบนทแยง ชานรองและทางวน
- ด่านหินเก่า: 6,000; ชานซ้าย–ขวาเชื่อมด้วยกลุ่มเกาะ และชานบนกว้าง
- ป่าริมธาร: 6,400; ชานยาวสองระดับที่มีช่องกระโดดและทางปีนหลายจุด
- สะพานช่องเขา: 7,000; สะพานข้ามแอ่ง ทางบนและทางใต้สะพาน
- ทางเลียบสันเขา: 6,600; ขั้นกระโดดทแยง ทางขึ้นสันเขาและชานรอง
- ลำน้ำในช่องเขา: 6,800; พื้นแอ่งหลายช่วง ทางบนเหลื่อมและชานเชื่อมยาว
- อ่าวเรือเก่า: 7,200; สามระดับชานยาว ปรับจังหวะช่องเปิดให้ต่างกัน

วางต้นไม้/พุ่ม/กอพืชขนาดเล็กบนชานในพิกัดโลก พร้อมเงาสัมผัส
มวลดินประกอบจากวัสดุเดิม ขอบมีเงาและความหนา ไม่ขยายพิกเซลภาพทั้งก้อน
ฉากหลังรักษาสัดส่วนและครอบคลุม viewport; Terrain วาดเฉพาะส่วนเห็น
แคช Terrain ของตัววาดใหม่จำกัด 24 MiB ไม่สร้าง Canvas ใหญ่ทั้งโลก
ปรับตำแหน่งวาร์ปและจุดเกิดตามเลย์เอ้าใหม่ รักษาการเชื่อมแมพเดิม
AUTO เฉพาะ 8 แมพใช้พื้นตามเนิน เชือกจริงและระยะกระโดดที่ทดสอบได้

ภาพแผนผังจากพิกัดจริง: docs/map_design/v67/LAYOUT_OVERVIEW_V67.png
เป็นแผนผังเลย์เอ้า ไม่ใช่ภาพเล่นเกม ดูคู่มือและภาพอ้างอิงใน docs/map_design
แบบร่างเก่าใน studies เป็นประวัติการออกแบบ ไม่ใช่ข้อมูลที่โหลดเล่น

Frontend อัป Vercel ตัวเต็ม; Backend อัป GitHub แล้ว git pull ที่ Hostatom
ไม่ได้ Deploy ให้ในรอบนี้ ไม่มีการเปลี่ยนฟิสิกส์/การต่อสู้/อัตราส่งข้อมูลเดิม
บันทึกผลตรวจจริงและขอบเขตทดสอบอยู่ qa/v67 ไม่ยืนยันผลบน Hostatom หรือทุกอุปกรณ์

Backend ต้องมี server.py, world_v56.json และ late_map_nav_v67.py ที่ Root
ไฟล์ server.py เทียบกับ GitHub ก่อนแก้แล้ว blob:
4a5f29473c9e7443fe4e7e28624f9d958e4b4513
ส่วนที่เพิ่มเป็นการเลือก Navigation ของ 8 แมพ ไม่แก้ระบบเครือข่าย

หลังอัปไฟล์ขึ้น GitHub และ Commit แล้ว:
cd /opt/jianghu
backup_dir="/opt/jianghu-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
cp -a server.py world_v56.json "$backup_dir/"
git status --short
git pull --ff-only
.venv/bin/python CHECK_BEFORE_RESTART.py
.venv/bin/python CHECK_WORLD_V67.py

ต้องให้ git pull และคำสั่งตรวจทั้งหมดผ่านก่อน จึงสั่ง:
systemctl restart jianghu.service
systemctl status jianghu.service --no-pager -l
journalctl -u jianghu.service -n 50 --no-pager

หาก git pull แจ้ง conflict ให้หยุด ไม่ใช้ reset --hard หรือทับ .env/.venv/drop-ins
