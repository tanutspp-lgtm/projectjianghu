# PROJECT JIANGHU — v8.0BU ONLINE Monster HP/DEF + Player AUTO + Security Audit
วันที่ 14 ต.ค. 2026 · สืบต่อ v8.0BT (Offline ยังเป็นต้นฉบับ; Online = web client + Python server)

## ภาพรวมและการอัปเดตที่สำคัญ
**ทุกครั้งที่แก้เกม ต้องเช็กทั้ง Offline/Online Client/Online Server/Supabase และบันทึกความต่าง**. เนื้อหานี้คือแพตช์ฝั่ง Online เท่านั้น; ห้ามสรุป Online = Offline 100% เพราะระบบอื่นยังค้าง (pounce, PvP, inventory equip จริง, persist, multi-map).

### 1. Monster HP/DEF Online ใช้ต้นฉบับ Offline v8.0AO
- `monster_balance_v80ao.js` เป็นแหล่งค่าต้นฉบับ 60 ระดับ Lv1–60. สร้าง `monster_hp_def_v80bu.json` จาก `.TABLE` ด้วย Node (120 คู่ HP/DEF สัตว์ทั่วไป/มนุษย์) ไม่คิดสูตรใหม่เอง.
- `monster_hp_def_v80bu.py` โหลดค่าที่ตรง Offline. `server.py`: `spawn_mobs` ใช้ HP/DEF พรีเซ็ตของมอนระดับที่กำหนด, เก็บ `Monster.defense`, Snapshot ส่ง `defense` ของมอน, โจมตีผู้เล่น -> มอนใช้ `DEF/(250+DEF)` และยังป้องกันยิงซ้ำ/EXP ซ้ำตามเซิร์ฟเวอร์เดิม. Passive damage Echo/Death Mark บนมอนเป้าหมายรองถูกลดตาม DEF ของมอนนั้น.
- เซิร์ฟเวอร์ตั้ง `MONSTER_PRESET_LEVEL` จาก ENV: **default 5** ทุกหมาป่า/หมูป่า Lv5 (HP339, DEF4). 1..60 บังคับทุกตัวตามระดับพรีเซ็ต; `0` หมายถึงใช้ระดับประจำ Slot ตามแมพเดิม (1..5) แต่ยังใช้ HP/DEF ตาม v8.0AO ของแต่ละตัว. ไม่อนุญาต Guest เปลี่ยนค่านี้ผ่าน WebSocket เพราะส่งผลทั้งแมพ.
- Client `index.html`: หน้าข้อมูลมอนอ่าน HP/DEF/Level จาก Snapshot ที่เซิร์ฟเวอร์ส่ง, แสดงป้าย DEF ของมอนออนไลน์; ตัวแก้ HP/DEF/Level โดยผู้เล่น Online ยังเป็น read-only เพื่อป้องกันโกง/กวนผู้เล่นคนอื่น. Offline QA ยังคงปรับเองได้เช่นเดิม.
- ตาราง reference 2–5 hits เป็น target สำหรับผู้เล่นอ้างอิง Lv1–60 ตาม Offline ไม่ใช่ว่าทุก build ทุกเลเวลจะตีจำนวนฮิตเท่ากัน. หมาป่ากระโจนบน Server ยังไม่ครบ; อย่าอ้างเป็น 100% AI parity.

### 2. Player Online AUTO แบบสุ่ม Tile ใหม่ ไม่ใช่แค่ Stress Bot
- เพิ่ม `farm_auto_v80bu.py` (Navigation สร้างจาก Platforms/Climbs ที่มีอยู่บนเซิร์ฟเวอร์). ไม่มีการนับ Floor ID จาก Tile หรือภาพ; Tile เป็นจุดหมายที่ยืนได้จริง. ในแมพมีทั้งสองประเภท: โอกาสรวม **พื้นล่าง 25%, ชั้นลอยรวม 75%** ไม่ขึ้นกับจำนวน Tile สะสม; เลือก Tile สุ่มในกลุ่มที่ถูกเลือก. แมพพื้นเดียวสุ่มบนพื้น 100%; ไม่สุ่มในอากาศ. Tile มีระยะขอบปลอดภัยและขนาดย่อยราว 64 world units.
- **ทุก 120 วินาทีของบอทแต่ละตัวเอง** สุ่มจุดหมายใหม่ (x/y/platform). ระหว่างทาง ถ้าเจอมอนบนแพลตฟอร์มเดียวกันที่เข้าโจมตีได้ก่อน ให้ตีโดยใช้ cooldown/SP/shot server เดิม; ฆ่าแล้วเดินต่อ. มอนหายไม่ได้กระตุ้นให้เปลี่ยนจุดหมาย. ถูกผลักตกให้หาเส้นทางกลับเป้าหมายเดิมจนกว่าครบ 120 วินาที. ไปถึงก่อนเวลาเดินสุ่มลาดตระเวนใกล้จุดนั้น. ไม่ล็อกชั้นฟาร์ม.
- การเดินข้ามแพลตฟอร์มใช้ graph ที่เชื่อมด้วยเชือก/บันได, เส้นทาง shortest cost + seed ที่ต่างกันช่วยแตกเส้นทาง ไม่วาร์ป. Server คุม input, climb, jump, position, damage; ไม่รับ Client x/y, target, path, HP/DEF, damage.
- `server.py`: Guest มี `auto_state`, รับคำสั่ง `{'t':'auto','enabled':true|false}` ที่ตรวจโครงสร้างและ rate limit. ใน `game_loop` AUTO เลือก action แล้วส่งผ่าน combat code server เอง. ผู้เล่นขยับด้วยมือหรือกดโจมตี -> ยกเลิก AUTO; heartbeat input=0 ไม่ยกเลิก.
- `index.html` ปุ่ม AUTO เดิมใช้ได้เมื่อ Welcome feature มี `auto`, หน้าจอแสดง AUTO ON/OFF จาก server snapshot; Offline AUTO เดิมยัง unchanged (same-lane). Stress bots ใน `bot_stress_v80bp.js` ยังเป็นตัวทดสอบแยกต่างหาก แต่หลักการปลายทาง 120s, 25/75 เหมือนกัน.
- เมื่อทำแมพใหม่ต้อง **อัปเดตทั้ง geometry ฝั่ง Client และ `beast_map_common_v80bq.json` ฝั่ง Server** จนกว่าจะรวม Map Manifest source กลาง; navigation rebuild อัตโนมัติจากข้อมูลแพลตฟอร์ม/เชือกของแมพใหม่. แผนที่สูงพิเศษ/มีชั้นกลางต้องทำการทดสอบเส้นทางทุกระดับ.

### 3. Security fixes รอบ v8.0BU
- QA Commands `sandbox_level`, `gear_*`, `qi_*` **ปิดโดยค่าเริ่มต้น** ด้วย ENV `ENABLE_GUEST_SANDBOX=0` (ถ้าเปิดเป็น 1 Guest ทุกคนจะใช้ QA gear/level/qi ได้; ให้ใช้เฉพาะ QA server ชั่วคราวและห้ามผูกกับ progression ถาวร). Client ซ่อน/ปิดตัวแก้ QA เมื่อ server ไม่อนุญาต.
- Strict `auto` toggles ต้องมีเฉพาะ t/enabled (bool จริง); ห้ามส่งพิกัด, เป้าหมาย, damage; manual packet ยังคุมฝั่งเซิร์ฟเวอร์. Validate `pressed` element เป็น string ก่อนใช้ set ป้องกัน payload แบบ list/dict unhashable. `strict_message` รับมือ JSON recursion error.
- Current auth ยังเป็น Guest-only, ยังไม่มี account verification/ownership persistence. **ห้ามเปิดให้ใช้ตัวละครถาวรหรือไอเท็มเงินจริง** บน infrastructure test นี้ก่อนทำ Auth, RLS, ownership และ abuse controls.
- **Known risks / not yet fixed:** `ALLOWED_ORIGINS` หากไม่ได้ตั้งค่าจะยอมทุก Origin; ควรตั้ง Netlify domain จริงใน Render (ต้องทดสอบ WebSocket/Stress หลังตั้ง). Guest สมัครซ้ำจากคนเดียวได้จนเต็ม `MAX_GUESTS=35` (DoS/slot exhaustion); ควรใช้ API gateway, quotas per verified account/IP and monitoring ก่อนเปิดสาธารณะ; อย่าเปิด `ENABLE_GUEST_SANDBOX=1` กับห้องสาธารณะ; QI/gear QA มีค่า stat boost เป็นเจตนาไม่ใช่ item ownership. Guest session/loot/EXP ยัง ephemeral; PvP combo/pounce/LOS/physics มีงาน parity ที่ค้าง, ไม่ใช่ผลทดสอบ security ยืนยันแล้ว.
- บังคับ ALLOWED_ORIGINS อย่างเดียวไม่ได้ป้องกันสคริปต์นอกเบราว์เซอร์: ต้องทำ Auth/session binding, per-account rate limit และ server authoritative ต่อไป.

### 4. ทดสอบผ่านในเครื่อง (ไม่ใช่ Render live)
- `test_v80bu_monster_auto.py`: mirror Offline 60 levels / 120 HP-DEF, mitigation, random sample 10k (ground≈25%), mapพื้นเดียว, ออโต้ปีนเชือกจริงถึงชั้นลอยทั้ง 4 จุด, ไม่ reset goal เมื่อ knockback ก่อนครบเวลา.
- `test_v80bu_protocol_security.py`: WebSocket 30 Guests + 20 mobs, AUTO 30 ตัว; packet fake x/damage, bad bool, malformed unhashable actions, unauthorized QA rejected; manual action หยุด AUTO ได้.
- `test_security.py`, `test_beast_parity_v80bq.py`, `test_online_protocol_v80bs.py`, `test_online_parity_v80bs.py`, `test_sandbox_parity_v80bt.py`, `test_sandbox_protocol_v80bt.py`, `test_qi_effects_v80bt.py`, `test_balance_v80bo.py` ผ่านเมื่อรัน QA tests ด้วย `ENABLE_GUEST_SANDBOX=1` ตามความตั้งใจในชุดเทสต์เดิม.
- Frontend `node --check` ผ่าน; Offline `test_monster_level_presets_v80ao.js`, `test_bot_stress_selection_v80bp.js` ผ่าน.
- **ยังไม่ได้ visual QA หรือ FPS บน Render/Netlify/iPad จริง, ยังไม่ได้ load test 30 คนบน Render Live**. ไม่มีสิทธิ์การยืนยัน Performance จากทดสอบ local.

### 5. อัปโหลด
1. Deploy ZIP GitHub/Render ฝั่ง Server v8.0BU ก่อน; อย่า deploy Netlify ใหม่ร่วมกับ Backend เก่าที่ไม่รองรับ feature `auto`. ตรวจ `/healthz` ตอบ `v8.0BU`.
2. Render ENV: `MONSTER_PRESET_LEVEL=5` (เปลี่ยน 1..60 เมื่อต้องทดสอบระดับต่าง ๆ); `ENABLE_GUEST_SANDBOX=0` ป้องกันค่าทดสอบ QA บนเว็บสาธารณะ; ตั้ง `ALLOWED_ORIGINS=https://YOUR-NETLIFY-DOMAIN` เมื่อทราบโดเมน. ถ้าต้องเทสสวมปราณ/ชุดเดิมควรใช้ *QA server แยก* ตั้ง `ENABLE_GUEST_SANDBOX=1` และไม่ใช้บัญชีจริง.
3. Deploy ZIP Frontend v8.0BU ใน Netlify; Online Guest -> ปุ่ม AUTO ON, เช็กว่าเดินขึ้นลงเชือก ตีมอนแล้วเดินต่อ, แสดง Lv5 / HP339 / DEF4 มอน. ถ้ามีมอนระดับอื่นจาก ENV ให้ดู Snapshot.
4. หากเปิด botstress เพิ่ม ให้ทดสอบกับแยก QA server + มอน 20 ตัว และ 30 bots; อย่าใช้ข้อมูล FPS บนเครื่อง local แทน FPS Render จริง.

## Handoff ถัดไป
- เดินหน้า parity ของ AI หมาป่า Pounce, Humanoid mobs & manual zones, ข้ามแมพและ Map Manifest source เดียว, ไอเท็มเกราะ/สวมจากกระเป๋าจริง, persistence+auth, ปราณเลื่อนจาก QA ไป gameplay, PvP + LOS/server collision; เพิ่ม Load Test จริง, per-account quotas, security logging and fuzzing.
- Audio LOCKED: hit 0.78, flute .24, boar death .66, wolf death .67, jump .52, pickup .42 (no cooldown), BGM70% SFX80%. ไฟล์ Audio ไม่ถูกแก้.
- สำคัญ: อย่านำ Sandbox เลเวล/ชุด/ปราณของ Guest กลับมาเปิดโดยไม่มี permission แค่เพราะลูกค้าอยากลอง; เสนอ QA server แยก.
