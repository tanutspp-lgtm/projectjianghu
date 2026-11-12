# Project Jianghu — HUD V215

ต่อจาก Frontend V213 พร้อมตัวแก้ V214 ที่รอแพ็ก และ Backend V213 บนฐานเต็ม V181 + cumulative V184/V187.6

## คำสั่งรอบนี้

งาน HUD/UI เป็นหลัก ใช้ธีมมิ้นท์/ครีมของหน้าสกิลและ Itim เดิม อาร์ตหน้าต่างใหม่ต้องเป็น imagegen EDIT อาร์ตเดิม ไม่วาดลวดลายด้วย CSS/Canvas ไม่ปรับบาลานซ์ดาเมจหรือสกิลใหม่

## ระบบที่เชื่อม

- กระบี่: แท็บปราณเป็นแท็บที่ 4 ใน skill_panel_v188 ทั้ง PC และ mobile C สลับโดยรักษาร่างพรสวรรค์เดิม ไม่ออกจากหน้าต่างไปหน้า sandbox เก่า
- อาชีพอื่นคงตัวจัดวิชา V186 เดิม เพิ่มทางเข้าปราณจากเครื่องมือของหน้านั้น ปราณใช้แผงมิ้นท์เดียวกัน
- ปราณเดิม 3 ID เท่านั้น: flute_echo เสียงสะท้อน, flute_sustain ทำนองหล่อเลี้ยงชีพ, death_mark ตรามรณะ
- เลเวลสวมใหม่ 10/25/40 แทน 20/40/60 แก้ JS/Python คู่กัน ปุ่มผู้เล่นใช้เลเวลตัวละครจริงตรวจสิทธิ์ ไม่เสนอช่องเปลี่ยน QA level/rank ในหน้าปกติ ไม่เพิ่มระบบดรอป/ครอบครอง/คัมภีร์/EXP ปราณใหม่
- ฝึก 1–20 และขั้นเสริม 0–5 เป็นค่าทดสอบเดิม รายละเอียด/โบนัสมาจาก catalog/engine เดิม ไม่สร้างดาเมจใหม่จากภาพหรือ tooltip
- I กระเป๋า: Consumable / Equip / Misc / Scroll ใช้ความจุรวม 100 ชิ้น ทุกแท็บร่วมกัน ของสวมไม่นับเป็นของในกระเป๋า ไม่มี stack ที่ทำให้ 100 ชิ้นกลายเป็น 100 กอง ส่วนที่ไม่มีไอเท็มจริงแสดงว่าง ไม่มีของตัวอย่างปลอม
- ใช้ไอคอน pixel ต้นฉบับ 36×36 และช่องอาร์ต 38px; hit target 42px หน้าเล็กแบ่งหน้า/เลื่อนภายใน ไม่ขยายภาพจนเบลอ
- C สเตตัส: + ทีละแต้มผ่าน JianghuStatSystem เดิม สูงสุด100 ต่อค่า แสดงพลังตีธรรมดาปัจจุบัน พลังอาวุธ DEF/การลดดาเมจ HP/SP/STA คริ ตัวคูณ ความเร็ว HIT/FLEE การฟื้นและโบนัสสเตตัส แสดงสูตรที่มีจริง ไม่อ้าง INT เพิ่มฮีลหมอ เพราะ engine ปัจจุบันไม่ได้ใช้ตัวเลข healPowerBonus นั้น
- Offline ยังคง pool ทดลอง180 เดิมและระบุบนหน้า; Online ใช้แต้มที่ server ได้มาจริงตามเลเวล ไม่แจกแต้ม180ให้ Online
- Q สวมใส่: weapon/head/top/bottom/wrist/shoes ตาม117 templatesเดิม + costume ช่องใหม่ ไม่มี costume item ถูกแต่งเพิ่ม
- ชุดเริ่มต้นใช้ NPC row1 Lv.5 อาวุธตามอาชีพ jian/dual_knives/flute/acupuncture + เกราะ5ชิ้น +0 ไม่มีออปสุ่ม แจกสวมเพียงครั้งแรก ไม่เพิ่มฟรีทุกเปิด/รีโหลด/ถอด มี starter-only level waiver จึงใช้ได้ตั้งแต่ตัวละคร Lv.1 โดยไม่เปลี่ยน required Lv.5 ของ template หรือเพิ่ม EXP/เลเวลฟรี
- สวม/ถอดจาก owned UID จริง เปลี่ยน ATK/DEF/HP/SP ผ่านสูตรเดิม; การเปลี่ยนของไม่เติม HP/SP/STA ฟรี สลับของตอนกระเป๋าเต็ม100ได้โดยใช้ช่องของใหม่ที่ถูกนำออก แต่ถอดเปล่าเมื่อเต็มถูกปฏิเสธ
- อาวุธผิดอาชีพ/เลเวลไม่ถึง/UID ไม่ได้ครอบครองถูกปฏิเสธที่ server ห้ามส่ง item stats จาก client
- สวมอุปกรณ์ยังไม่เปลี่ยนภาพเสื้อผ้าใน atlas ตัวละครที่วาดรวมไว้แล้ว ไม่อ้างว่าทำระบบ rig/เปลี่ยนชุด sprite
- K Social: party6 / guild24 / friends50; search ผู้เล่นออนไลน์ตามชื่อ; กดชื่อเปิด actions ภายในแถว เพิ่ม/ลบเพื่อน กระซิบ เชิญกลุ่ม หัวหน้าเป็นผู้เชิญและผู้รับต้องกดรับ; ออกจากกลุ่มได้ โอนหัวหน้าอัตโนมัติในชุด Guest นี้
- เชื่อม party_id จริงกับกฎฮีลปาร์ตี้เดิม ไม่เปลี่ยน40%/60s หรือระยะ/สถานะของสกิล
- แชทมีแท็บกระซิบและชื่อผู้รับ กดกระซิบจากรายชื่อเปิดแท็บนั้นให้ แยกข้อความส่วนตัวออกจากแท็บรวม Server route เฉพาะผู้ส่ง/ผู้รับ; party/guild ตรวจสมาชิกจริงก่อนส่ง ไม่ทำ local echo ปลอมว่า Online สำเร็จ
- Guest social/inventory/equipment เป็นข้อมูล session ในหน่วยความจำ server ไม่ใช่ account persistence; disconnect แสดงสถานะเพื่อน offline แต่การรีสตาร์ต server/Guestใหม่ไม่รับรองรายชื่อหรือของเดิม ไม่มีการเปลี่ยน Supabase schema/RLS

## Hotkey

I=กระเป๋า C=สเตตัส K=Social Q=สวมใส่ ปุ่มเดิมที่ชนย้าย aoe K→H และ lock I→T รักษาคีย์ส่วนตัวอื่นที่ไม่ชน ไม่เปิดการโจมตีจากการพิมพ์ในช่องข้อความ ไม่ทำ assignment UI บน Android/iOS เพิ่ม

## Art/layout

assets/ui_hud_v215/window_source.png และ window.webp เป็น imagegen EDIT จาก assets/ui_art_v189/window.webp + button-cream.webp ใช้เป็น skin ร่วมของหน้าต่างใหม่ มี true alpha รอบนอก ปุ่มครีมมาจากอาร์ตเดิม ปุ่มมิ้นท์ของแผงใหม่เป็นimagegen EDITแยกที่ไม่มีลวดลายในพื้นกด; ไม่เปลี่ยนภาพเมฆของกรอบเดิม ฟอนต์เป็น JHItimLocal

หัวเว้นซ้าย58px และท้ายเว้นขวา76–100px ไม่วางข้อความ/ปุ่มบนเมฆ ใช้พื้นที่ภายในแผงเท่านั้น รูปอาวุธใช้ contain ไม่มีวงกลมตัดด้าม/ปลาย ภาพ pixel ไม่มีการย่อทั้งหน้าให้ตัวหนังสือเล็ก หัว/ปิดคงอยู่ รายการ/รายละเอียดเลื่อนภายในกรอบ มือถือแคบหน้าสเตตัสแยกแผงอัพ/ค่าคำนวณ และอุปกรณ์เหลือหนึ่งคอลัมน์

V214 ปุ่มหน้า1/2 width:max-content + nowrap และแถว context สูงตามข้อความรวมอยู่ใน skill_mobile_c_v211.css แล้ว ห้ามย้อนกลับไป64px fixed ที่เหลือเนื้อข้อความ40px

## แหล่งกฎเดิมที่อ่าน

- HANDOFF_V80BT_QI_GEAR_ONLINE_SANDBOX_TH.md / HANDOFF_V80BS_PROGRESS_EXP_STATS_LOOT_TH.md จาก Backend V181 Full
- qi_catalog_v1.js / qi_test_system.js / sandbox_loadouts_v80bt.py
- COMBAT_QI_AUDIT_2026_11_09_TH.md / SKILL_WHEEL_GUIDELINES_TH.md
- EQUIPMENT_BASE_STATS_117_V1.json / gear_balance_v80bn.js / combat_progression_v80bs.py / index.html derivedStats
- คู่มือ Ragnarok ทางการใช้ดูรูปแบบหน้าต่างและรายการเท่านั้น ไม่คัดลอก artwork/formula/จำนวนสมาชิก: https://ragnarokonline.gungho.jp/playmanual/operation/window.html และ https://ragnarokonline.gungho.jp/gameguide/system/party.html

## ทดสอบและการส่ง

ดู QA_V215_TH.txt สำหรับหลักฐานจริงและขอบเขต แยก simulated Chromium / Node/Python / local WebSockets ออกจากการทดสอบมือถือจริง ไม่รับรองมือถือทุกรุ่นจาก viewport จำลอง

ส่ง Full Frontend3 ZIP อิสระ แตกทับโฟลเดอร์ว่างเดียวกันหรือใช้ MERGE_V215.ps1 เพื่อสร้างโฟลเดอร์พร้อม FULL.zip ไม่ต่อไบต์ ZIP ส่ง Full Backend ที่รวม dependencies จริง ไม่ใช่เพียง changed files ไม่ได้ push Git/deploy VPS ให้อัตโนมัติ

ก่อนแพ็กตัด __qa__, .openai, tools/tests/probes, runtime test saves และ preview server ออก เก็บรายงานภาพ/ผลตรวจแยกจากตัวเกม
