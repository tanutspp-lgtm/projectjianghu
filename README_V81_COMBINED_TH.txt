JIANGHU V81 COMBINED — รวม V80 + V81 ลงครั้งเดียว

FRONTEND ตัวเต็มรวม assets ทั้งหมดจาก V80 และ index.html ของ V81
แตก ZIP แล้วอัปโฟลเดอร์ที่มี index.html + assets เข้า Vercel ตามเดิม
ไม่ต้องลงแพ็ก V80 หรือ V81 UPDATE แยกอีก

BACKEND รวม 3 ไฟล์ Runtime ที่เปลี่ยนทั้งหมด: server.py, world_v56.json, late_map_nav_v67.py
อัปทั้ง 3 ไฟล์นี้เข้า GitHub ทับของเดิม แล้ว git pull ที่ VPS
ไม่ต้องยก backend เก่าทั้งชุดขึ้นใหม่; ไฟล์ฐาน/ฐานข้อมูลใช้ของเดิม

รวมงานสุสาน V80: A/B/C + ห้องพระบรมศพ, พื้นสามมิติ, บันไดผุ, โลงเก่า,
ประตูมังกร, วาปเชื่อมจริง, ฉากหลังแยกเลเยอร์, ไฟเคลื่อนไหวและภาพย่อแมพ
รวม V81: มอนที่อยู่บนพื้นโดนตีรวมขลุ่ยแล้วถอย 60 หน่วยโลกใน .20 วินาที,
รวมมอนคน, หยุดก่อนขอบพื้น/ผนัง/ขอบเขตเดิน ไม่ผลักศพ/หุ่นซ้อม/การบล็อก
ค่า knockback นี้เป็นค่าของเกมเรา ไม่ใช่ตัวเลขระยะ MapleStory ที่วัดยืนยันแล้ว

World/Feature ต้องตรง: world-maps-v80-tomb-playable-v1 (WorldV23)
V81 ไม่เปลี่ยน geometry จึงคงชื่อ Feature V80 ไว้โดยตั้งใจ
ไม่เปลี่ยนอัตรา movement/network, ดาเมจ, สเตตัส หรือ authority ของเซิร์ฟเวอร์

หลังอัป backend เข้า GitHub รันบน VPS:
cd /opt/jianghu
git pull --ff-only
.venv/bin/python -m py_compile server.py late_map_nav_v67.py
.venv/bin/python -c "import json; print(json.load(open('world_v56.json'))['feature'])"
systemctl restart jianghu.service
systemctl status jianghu.service --no-pager

ตรวจแพ็ก: คงไฟล์ V80 ทุกไฟล์, geometry frontend/backend ตรงกัน, Python/JS syntax ผ่าน,
ZIP CRC ผ่าน, รวมข้อมูลผลทดสอบเดิม V80 และ V81 (ตรรกะ knockback parity 50 กรณี)
ยังไม่ได้ deploy/restart VPS หรือยืนยันการเล่นออนไลน์ของชุดรวมนี้
