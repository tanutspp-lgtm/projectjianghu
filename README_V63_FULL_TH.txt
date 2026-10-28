PROJECT JIANGHU — BACKEND V63 ตัวเต็ม / Backend World V14

ฐาน: GitHub tanutspp-lgtm/projectjianghu, main
Commit: d01bc59b945441dd70f64a86da3acdc9bc89cbd0
ประกอบจากไฟล์ข้อความ 90 ไฟล์ใน commit นี้ ไม่รวม ZIP/แพตช์เก่าและ server_REFERENCE_FROM_V20_TO_V21.py
มี server.py, requirements.txt, โมดูล Python, ข้อมูล JSON และไฟล์ตรวจสอบครบตามฐาน GitHub
server.py และไฟล์เดิมทั้งหมดคงไบต์ตรงกับ GitHub ยกเว้น world_v56.json ที่เปลี่ยนเป็นข้อมูล V63
เพิ่ม CHECK_GRANITE_V63.py, เอกสารฉบับนี้ และรายงาน QA/แหล่งที่มา
ไม่รวม .env, .venv, ข้อมูลจากเครื่องจริง หรือ systemd drop-in ของ Hostatom

ใช้คู่กับ Frontend V63 ตัวเต็มที่แบ่ง 3 พาร์ท
Feature: world-maps-v63-granite-pair-connected-v1
Map11: forest-fork-map11-v21-clean-ropes
แมพคู่ใหม่เลือกผ่านเมนูแมพได้ และวาปเชื่อมกันไปกลับ
ยังไม่เปลี่ยนเส้นทางวาปของหน้าผาเดิม
คงโค้ด Self 30Hz, snapshot 10Hz, AUTO, Combat และ Inventory ตาม GitHub

ก่อนใช้งานที่ /opt/jianghu
ตรวจและสำรองไฟล์ที่เครื่องจริงก่อน โดยเฉพาะ server.py, world_v56.json, .env และโมดูลที่มีการแก้เอง
ชุดนี้ไม่ได้ยืนยันว่า Hostatom ใช้ commit เดียวกับ GitHub จึงต้องเทียบก่อนเขียนทับ
เก็บ .env, .venv และ systemd drop-in เดิมไว้
ใช้ Python 3.11 ขึ้นไป และ dependencies ตาม requirements.txt
หลังแตกไฟล์ในตำแหน่งที่ตรวจและสำรองแล้ว รัน:
.venv/bin/python CHECK_BEFORE_RESTART.py
.venv/bin/python CHECK_GRANITE_V63.py
จากนั้นจึง restart ตามขั้นตอนเดิม:
systemctl restart jianghu.service
systemctl status jianghu.service --no-pager
journalctl -u jianghu.service -n 60 --no-pager

ตรวจแล้ว
- Git blob ของไฟล์ฐาน 90 ไฟล์ตรงกับ GitHub
- Syntax ของ Python 41 ไฟล์
- โมดูลที่ต้องใช้ โหลด runtime และตัวตรวจสอบเดิม/V63 ผ่าน
- ข้อมูล world ของ Frontend V63 และ Backend ตรงกันทั้งหมด
- WebSocket จริงบน loopback: welcome features/rates/caps, เข้าแมพใหม่จาก selector,
  ปฏิเสธวาปผิดตำแหน่ง, วาปคู่ใหม่ไปกลับ และ ping/pong
  การทดสอบวาปตั้งตำแหน่งด้วย fixture ฝั่งเซิร์ฟเวอร์ ไม่ได้ทดสอบเดิน/ปีนออนไลน์ครบเส้นทาง
- ZIP เปิดได้และมี server.py ที่ Root
ยังไม่ได้ตรวจ Hostatom, ทดสอบ Live Online/FPS, Push Git หรือ Deploy
