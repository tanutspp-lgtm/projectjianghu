# Project Jianghu V220 — หาปาร์ตี้

ใช้ Frontend V220 คู่กับ Backend V220 เข้า Online Guest แล้วเปิด สังคม → หาปาร์ตี้ หรือพิมพ์ /agency ในแชท หัวตี้กดประกาศรับสมาชิก และเลือกกิจกรรม แผนที่ เลเวล หรืออาชีพที่ต้องการได้ คนที่ยังไม่มีตี้สร้างตี้พร้อมลงประกาศได้ในการส่งครั้งเดียว เลเวลและอาชีพในประกาศใช้ช่วยค้นหา การรับอัตโนมัติอิงสมาชิกเลเวลต่ำสุดของปาร์ตี้เดิม ผู้สมัครที่เข้าอัตโนมัติไม่ได้ส่งคำขอให้หัวตี้พิจารณาได้ ปาร์ตี้เต็มที่หกคนจะหายจากรายชื่อให้สมัคร การปิดประกาศยังเก็บปาร์ตี้เดิมไว้ ประกาศอยู่ในหน่วยความจำของเซิร์ฟเวอร์ Guest รอบนั้น รายชื่ออัปเดตเฉพาะเมื่อเปิดแท็บนี้

รวม Frontend บน Windows วาง ZIP สามพาร์ตในโฟลเดอร์เดียวกัน แล้วเปิด PowerShell ที่โฟลเดอร์นั้น
```powershell
1..3 | ForEach-Object { Expand-Archive -LiteralPath "JIANGHU_FRONTEND_V220_FULL_PART_${_}_OF_3.zip" -DestinationPath ".\JIANGHU_FRONTEND_V220" -Force }
Compress-Archive -Path ".\JIANGHU_FRONTEND_V220\*" -DestinationPath ".\JIANGHU_FRONTEND_V220_FULL.zip" -Force
```

V219 ใช้ Frontend และ Backend V219 คู่กัน กระเป๋า/สวมใส่ใช้รายละเอียดและออปชันชุดเดียวกัน สเตตัสยืนยันครั้งเดียว ปราณทดสอบสามขั้น 10/25/40 แชร์ EXP เฉพาะแมพและแชนแนลเดียวกัน 0/10/20/35/55/75% เพื่อน/กิลด์/ตี้เป็นข้อมูล Guest ของเซิร์ฟเวอร์รอบนั้น ข้อมูลสังคมข้ามการรีสตาร์ตยังต้องมีระบบบัญชี หลัก UI สำหรับอาชีพต่อไปให้อิงไฟล์ SKILL_WHEEL_GUIDELINES_TH.md และใช้รูปเดิมของเกม มีที่ว่างแยกปุ่มจากเมฆ ชื่อยาวตัดเฉพาะในแถวและเปิดดูชื่อเต็มได้

# Project Jianghu — Backend V215 FULL

อ่าน README_V215_TH.txt และ HANDOFF_UI_V215_TH.md
ฐานเต็ม181 + cumulative184 +187.6 +213 lock fallback +215 owned equipment/social/Qi gates10/25/40
World52/geometry/30Hz self/10Hz peers unchanged. No account persistence or live deploy.
