Seven Wind Backend V235 — cumulative changed files from V219

ชุดนี้เทียบเนื้อหาไฟล์กับ JIANGHU_BACKEND_V219_FULL.zip จริง รวมไฟล์ใหม่และไฟล์ที่เปลี่ยนหลัง V219 จนถึง V235
มีระบบจากแพตช์ก่อนหน้า เช่น roster progress / mail / medicine / social / party / flute contact และป่าไผ่ใหม่
แตก ZIP แล้วได้ server.py และไฟล์ที่เกี่ยวข้องที่ root ไม่มีโฟลเดอร์ backend ซ้อน

1. อัปโหลดทุกไฟล์ใน ZIP เข้าราก repository Backend เดิมบน GitHub โดยรักษาโฟลเดอร์ database/ และ archived_maps/ แล้ว Commit
2. ที่ Hostatom:
   cd /opt/jianghu
   git pull --ff-only
   bash RESTART_AND_VERIFY_V235.sh
3. ต้องเห็น PASS: running backend V235 + roster progress

ไม่มีการเปลี่ยนคีย์หรือ systemd environment; ถ้าตั้ง roster-progress.env จนบันทึก EXP ได้แล้ว ไม่ต้องตั้งซ้ำ
ห้ามทับไฟล์ .env หรือ data/ ของเซิร์ฟเวอร์ด้วยไฟล์จากที่อื่น ชุดนี้ไม่มีคีย์ ไม่มีฐานข้อมูลผู้เล่น และไม่มี data/
SQL เป็นแพตช์สะสมเดิม: เครื่องที่ทำ roster_progress.sql แล้วไม่ต้องรันซ้ำเพื่ออัปเดตแมพ V235
ถ้าเริ่มจาก V219 ที่ยังไม่เคยเปิดระบบบัญชี/EXP ต้องทำขั้นตอนบัญชีและฐานข้อมูลเดิมก่อน ตาม ACTIVATE_ACCOUNTS_TH.md
อย่ารัน SQL ทุกไฟล์แบบสุ่มหรือเรียงชื่อ เพราะแต่ละไฟล์เป็นการเปลี่ยนคนละช่วง

ป่าไผ่ใหม่ BAM_START_01–04 แทน bamboo_1–4 ใน active world
ตัวละครใหม่/ไม่มีตำแหน่งเซฟเริ่ม BAM_START_01 (70,655)
ตัวละครที่มีตำแหน่งใหม่อยู่แล้วกลับจุดเดิม ตัวละครที่เซฟใน bamboo_1–4 ย้ายไปแมพใหม่ลำดับเดียวกันที่จุดเริ่มปลอดภัย
เลเวล EXP และเงินไม่ถูกรีเซ็ตจากการย้ายแมพ
หน่อเซียนทุกแมพ: 9/11/10/9 ตัวต่อแชนแนล อยู่บนพื้นและแพลตฟอร์มจริง ระดับ 1–5
เส้นทาง: ป่าภูเขาเดิม ↔ ป่าไผ่ใหม่ 1 ↔ 2 ↔ 3 ↔ 4 ↔ ชานเมือง
ป่าไผ่เก่าเก็บใน archived_maps/bamboo_legacy.json ไม่เปิดเป็น active room

ตรวจแล้วด้วย local WebSocket: first entry, saved-location migration, EXP/level preservation, portals, CH switch, mob spawn/respawn
เดิน/กระโดด/เชือกด้วยฟิสิกส์จริง JS และ Python ผ่านทั้ง 4 แมพ
ยังไม่ได้ติดตั้งหรือทดสอบบน Hostatom ของผู้ใช้ ต้อง pull และ restart ตามด้านบน
