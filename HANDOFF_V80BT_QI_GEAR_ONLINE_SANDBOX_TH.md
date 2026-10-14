# PROJECT JIANGHU / WUXIA FLUTE ARENA — v8.0BT Handoff (14 ต.ค. 2026)

## จุดตั้งต้นที่ต้องทำต่อ
- ฐานก่อนหน้า = v8.0BS (EXP/Stats/Skill Mastery/Basic weapon loot + 20 Beast Online) และ v8.0BR (fix facing).
- **คำสั่งผู้ใช้หลัก:** เกม Offline และ Online ต้องใช้กฎ/Asset/FX/เสียงและความรู้สึกเล่นเหมือนกันให้มากที่สุด เป้าหมายระยะยาว 100%; ทุกแพตช์ต้องตรวจทั้ง Offline, Online Client, Online Python Server, Supabase; ห้ามอัปเดตด้านเดียวโดยไม่ตรวจอีกด้าน.
- ผู้ใช้ถามชัดให้ **ยกระบบทดลองสวมปราณและทดลองใส่ชุด/ปรับ DEF/ATK ออฟไลน์มาออนไลน์ทันที**. v8.0BT ย้ายระบบ **Sandbox ทดลอง** ทั้งสองอย่าง ไม่ใช่เปิดครอบครอง/Equip ไอเท็มถาวร.

## สิ่งที่ทำใน v8.0BT
- Online Guest UI `Inner Arts` ใช้ชุดปราณสามวิชาเดียวกับ Offline ผ่าน `qi_catalog_v1.js` และ `qi_test_system.js`; สวม/ถอดช่อง 1/2/3 เกณฑ์ Lv20/40/60; ฝึก 1–20 / ขั้นเสริม 0–5; เลือก *QA test level* Lv1–60 โดยไม่ปลอมเลเวล EXP จริง.
- Online Guest UI `Equipment / Gear Balance` เลือกชุดทดลองตัวละคร Lv10/20/30/40 (ไอเท็ม Required Lv5/15/30/40) พร้อมเกราะ 5 ชิ้น+ขลุ่ย 1 ชิ้น, +0/+5/+7, ปรับออป DEF สองแถว/เกราะ และ ATK สองแถว/ขลุ่ย. รูป/ชื่อจาก catalog เดิม.
- Python authoritative module `sandbox_loadouts_v80bt.py` โหลด `EQUIPMENT_BASE_STATS_117_V1.json` ของ Offline, mirror สูตรของ `gear_balance_v80bn.js` แบบตรงผล; mirror โบนัส/กลไก `qi_test_system.js`. ห้ามรับ HP, ATK, DEF และ item instances จาก Client; รับเฉพาะ selectors ที่ validate แล้ว.
- `combat_progression_v80bs.py` derive_stats รวมโบนัส Qi+Gear จริง: HP/SP/STA/STR/AGI/VIT/DEX/INT/ATK/DEF/crit/regen/speed, `preview_skill` ใช้ weaponAttack จริง; `roll_attack` ใช้ crit multiplier. เปลี่ยนชุดบน Guest server ส่งผลกับ `p.defense`, HP/SP, ความแรงสกิลทันที. ชุดทดลองยังไม่สร้าง item ใน Bag.
- Passive ที่อิมพลีเมนต์บน Python สำหรับ Beast common map: `flute_echo` J ตีชิ่งเป้าที่สองในระยะ 150 ที่ 20–35%; เกราะเมื่อ HP<35% 30s/CD120s เฉพาะขั้นเสริม; `flute_sustain` ฆ่ามอน 20→12 ตัว ฟื้น 5% MaxHP, J main มีโอกาสตัน 1s; `death_mark` ครบ 3 stack แล้วฮิตที่ 4 ระเบิดโบนัส 60–120%, สตัน 30% เมื่อขั้นเสริม 5.
- เพิ่ม server-confirmed visual events (`qi_echo`, `death_mark`, `qi_stun`, `qi_shield`, `heal`) ให้ Client แสดง FX. ความดังไฟล์เสียงเดิมไม่มีการแก้ไข.
- Private WebSocket snapshot ฝั่งเจ้าของเท่านั้นเพิ่ม `testLevel`, `effectiveLevel`, `qiEquipped`, `qiRanks`, `gear`, `qiRuntime`, `derived`. world public ไม่แนบโบนัส/private gear ของผู้เล่น. โปรโตคอล `sandbox_level`, `qi_equip`, `qi_unequip`, `qi_rank`, `gear_preset`, `gear_enhance`, `gear_affix`, `gear_clear`; malformed/ค่าข้ามข้อจำกัด rejected โดย server.
- อัปเกรด `qi_test_system.js` ด้วย `snapshotForServer` เพื่อวาด UI Online จากสถานะ server โดยไม่แก้ state Offline/localStorage และอัปเดตตัวเลือก UI เมื่อ server snapshot ยืนยันการเปลี่ยนแปลง.
- อัป `healthz`/feature banner เป็น `v8.0BT`, ให้ frontend ปิดตัวเลือก Sandbox หาก backend ยังเก่า.

## ทดสอบที่รัน
- `python test_sandbox_parity_v80bt.py`: 108 presets ของ JS Offline = Python online, 48 rank/enhance sets โบนัส/กลไกปราณตรงทุกค่า, validate forged inputs; ผ่าน.
- `python test_sandbox_protocol_v80bt.py`: 2 concurrent Online Guest, เลือกปราณ/ชุดเซิร์ฟเวอร์จริง, DEF/ATK เปลี่ยน, ไม่มี private leaked, malformed server refused, clear ใช้จริง; ผ่าน.
- `python test_qi_effects_v80bt.py`: Echo, low HP shield, Death Mark 4th hit, Sustain heal; ผ่าน.
- เทสต์เดิม `test_online_parity_v80bs.py`, `test_online_protocol_v80bs.py`, `test_security.py`, `test_beast_parity_v80bq.py`, `test_balance_v80bo.py`; ผ่าน.
- `node --check` ของ `index.html` inline JS, `qi_test_system.js`, `jianghu-ui.js`; ผ่าน.
- **ยังไม่ผ่าน Visual QA บนเบราว์เซอร์จริง:** Chromium สภาพแวดล้อมนี้บล็อก `file://` และ localhost; ผู้ใช้ต้องลอง Netlify + Render แล้ว feedback.

## การลงแพตช์
1. อัปเดตทุกไฟล์ใน ZIP Backend ไป GitHub repo `tanutspp-lgtm/projectjianghu` แล้วรอ Render (`projectjianghu.onrender.com`) Auto Deploy Live.
2. เช็ก `https://projectjianghu.onrender.com/healthz` ต้องบอก `v8.0BT`.
3. Deploy Netlify ด้วย ZIP frontend v8.0BT (ZIP layout มี `index.html` ที่ root).
4. Online Guest → เปิดเมนู Qi เลือก Lv60 ทดลอง แล้วสวม 3 ปราณ ปรับฝึก/เสริม; เปิด Equipment เลือก Lv40 +7 แล้วลองยิง/ให้หมูกัด ดู ATK, HP, DEF. **เลเวลทดลองไม่เพิ่ม EXP, ไม่มี item จริงถูกใส่ Bag จากการเลือกชุด**.
5. ไฟล์ Test และ Handoff อยู่ใน ZIP backend, Handoff และ Asset Map อัปเดตอยู่ใน frontend.

## ข้อจำกัด/งานค้าง — ห้ามอ้าง Online = Offline 100% แล้ว
- นี่คือ `Online Guest TEST SANDBOX` มี **โปรโตคอล QA ที่อนุญาตให้เลือก Test Lv/ปราณ/ชุดได้เอง** เฉพาะ Guest ชั่วคราว, **ห้ามเปิดสิทธิ์แบบนี้ในเซิร์ฟเวอร์บัญชีจริง** (ต้องแยก admin/test permissions); ไม่มี persistent character/equipment/qi inventory/ownership/bound/affix roll.
- ระบบไอเท็มเกราะดรอปจริงและสวมจาก Bag, Qi book/drop/progression, +8..+10 HP% จาก gear enhancement, random affixes, ดัน premium/manual, RPG ทุกอาชีพ, PvP เต็มระบบ, แผนที่หลายแห่ง, ตลาด ยังไม่พอร์ตครบ.
- ระบบ Echo/DeathMark/Sustain บน **Common Beast online arena** พอร์ตเอฟเฟกต์หลักแล้ว แต่ visual fidelity/จังหวะ Animation, knockback ในหลายสภาพ, hit collaboration, EXP assisted kills และ PvP ต้อง QA เทียบ Offline เพิ่ม; ไม่รับรอง parity เต็ม 100%.
- On Guest QA การเลือก testLv / kit เปลี่ยนความแรงได้จริงโดยเจตนา; เมื่อจะเปิดบัญชีจริง ต้องห้าม EXP/ของรางวัลที่เก็บด้วยสถานะ QA เพื่อไม่ให้ปั๊ม progression จริง. ตอนนี้ Guest progress ยังชั่วคราวอยู่.
- Supabase **มีตาราง EXP แล้ว** `game_balance_versions` exp_v1, `character_level_exp` 60, `monster_level_base_exp` 60, `exp_level_gap_rules` 7; ตาราง PvP HP/Monster damage v80bo ยังคงเดิม; v8.0BT ไม่แก้ Supabase schema/data.
- Audio locked gains: hit .78, flute .24, boar death .66, wolf death .67, jump .52, pickup .42(no cooldown), BGM70%/SFX80%. อย่าเปลี่ยนโดยพลการ.
- User bot random target design locked: every 120s choose walkable tile; total ground chance 25%, floating chance75% when both; any monster nearby fight first then resume same target; independent timers; no floor-ID dependency; these rules preserved in `HANDOFF_BOT_DESTINATION_DESIGN_LOCKED_TH.md`.

## Source/Asset map
- Frontend: `index.html` (runtime Offline + Online), `qi_test_system.js` + `qi_catalog_v1.js` (inner arts prototype), `gear_balance_v80bn.js`, `EQUIPMENT_BASE_STATS_117_V1.json`, `jianghu-ui.js` (inner arts and gear panels), `skill_mastery_v1.js`, `assets/audio/sfx/`, `assets/monsters/`.
- Backend: `server.py` (authoritative websocket/snapshot/combat), `combat_progression_v80bs.py`, `sandbox_loadouts_v80bt.py` (NEW), `EQUIPMENT_BASE_STATS_117_V1.json` (same reference data as Offline), `exp_balance_v1.json` (fallback), `loot_templates_v80bs.json`, `beast_map_common_v80bq.json`.
- Tests: `test_sandbox_parity_v80bt.py`, `test_sandbox_protocol_v80bt.py`, `test_qi_effects_v80bt.py` + previous tests.
