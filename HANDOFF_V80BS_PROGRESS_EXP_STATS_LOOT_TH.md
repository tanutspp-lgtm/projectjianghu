# Project Jianghu — Handoff v8.0BS: Server-side XP / Stats / Flute Skills / Loot

วันที่ 14 ต.ค. 2026 | **ยังไม่ใช่ Offline ↔ Online 100% parity** | ทดสอบ Backend/สูตรในเครื่องแล้ว ยังไม่ผ่าน Browser Visual QA/Live Render Netlify

## เป้าหมายล็อกจากผู้ใช้
ทุกแพตช์หลังจากนี้ต้องอัปเดตทั้ง Offline และ Online ให้เป็นเวอร์ชันล่าสุดของระบบเดียวกัน ทั้งภาพ/เสียง/มอน/ดรอป/เลเวล/EXP/ปราณ/อุปกรณ์/สเตตัส/สกิล/ATK/HP/DEF/พฤติกรรม/ระบบบอท/แมพ. **Offline เป็นต้นฉบับของกติกาเกม** และ Python Online ต้อง server-authoritative; ห้ามให้ Client ส่ง HP, EXP, Level, Damage, Item Roll, Affix เอง. หากส่วนไหนยังไม่พอร์ตต้องระบุอย่างตรงไปตรงมา.

## ทำใน v8.0BS (ใช้งานจริงในแพตช์ถัดไปหลัง Deploy ทั้งสองชุด)
1. อ่านตาราง Supabase ที่มีอยู่แล้ว: `public.game_balance_versions`, `character_level_exp` (60), `monster_level_base_exp` (60), `exp_level_gap_rules` (7). **ไม่สร้าง/แก้ตาราง EXP**. ใช้ `exp_v1` active; Backend เรียก REST ผ่าน publishable key ที่ถูกจำกัดโดย RLS. ถ้าดึงไม่ได้ ใช้ `exp_balance_v1.json` สำเนาจาก Offline `exp_balance_v1.js` และแจ้ง `EXP balance: packaged-exp_v1` ใน Render Log. `combat_progression_v80bs.py` เป็นสูตรฝั่งเซิร์ฟเวอร์.
2. **Guest Online เริ่ม Lv1** แทน Lv5 ของสนามทดสอบเก่า; server ให้ EXP เฉพาะการฆ่ามอนที่ยืนยันด้วย projectile/hit จริง, เลเวลสูงสุด 60, โบนัส +3 Stat Point / +1 Skill Point ต่อเลเวล, EXP gap/overlevel cap ตรง Offline. เกิด event `exp`, `levelup`, Snapshot มีเลเวล/EXP/แต้มส่วนตัว. สถานะ Guest ยังไม่บันทึกหลังออกเกม.
3. `STR AGI VIT DEX INT` เริ่ม 0 อัปด้วยข้อความ `{t:'stat_add',stat:'vit',amount:1..10}` เฉพาะเมื่อมีแต้มจากเลเวล, cap100 ต่อช่อง; Backend คำนวณ HP/SP/STA/regen/crit/move/flee/hit จาก `derivedStats()` ที่ยกสูตรจาก Offline (zero Qi/zero gear). `JianghuStatSystem` เชื่อม UI Status ให้ใช้ server snapshot ไม่ใช่ 180 คะแนนทดลองของ Offline.
4. Skill Tree รับ `{t:'skill_up',skill:'mastery'|'aoe'|'break',amount:1..10}` server ตรวจแต้ม/rank. Rank J=1 ตลอด; K/U ≤9; Mastery≤10. `JianghuSkillMasteryTools` โหมด Online แสดง Rank, แต้ม, MIN/MAX ที่คำนวณจากข้อมูล Server; Offline ยังใช้ logic ทดลองเดิม. server projectile now rolls damage using actual Skill Mastery/INT/level with 5% base Crit +1%/3DEX, 150% Crit damage; SP K=16 U=12 J=0; dash costs STA 30. ค่าจริงจาก server ไม่ใช่ client input. ระบบ PvP rule บางส่วนยังคงเป็น test arena ไม่ parity 100%.
5. Loot อาวุธ 52 template ถูกดึงจาก `LOOT_WEAPONS` ของ Offline จริงเป็น `loot_templates_v80bs.json`. Kill หมู/หมาป่าระบบ common → สุ่มอาวุธตาม Tier เช่นเดียวกับ Offline createDeathLoot; 1 drop/kill; Owner 60 วินาที; TTL 180 วินาที; Pickup 130x75; Bag 48 ช่อง; event จากเซิร์ฟเวอร์ยิง pickup FX/SFX เดิม (ไม่ throttle pickup เสียง). ตัวละครอื่นไม่เห็น inventory ส่วนตัวใน network Snapshot; หน้า Bag ของ Online อ่านรายการของตัวเองจาก `snapshot.inventory` เท่านั้น. ยังไม่มี Persisted Bag / sealed equipment / Equipped armor.
6. Network: `snapshot()` ส่ง World/Players ข้อมูลส่วนรวมหนึ่งชุด; per-socket ส่ง `self` (EXP/stats/skills/derived) และ `inventory` เฉพาะเจ้าของ ไม่ broadcast ข้อมูล Bag ของผู้เล่นอื่น. Frontend `applyOnlineSnapshot` merge `m.self` into authoritative self. Snapshot 30 guest + 20 mobs จาก ~39KB ลดเหลือ ~21KB ใน local smoke test หลังทำ private payload. ค่าจริงแปรตาม loot/event/ตำแหน่ง.
7. ส่ง `cast` event สำหรับ J/K/U เมื่อ server ยอมรับการยิงแล้ว เพื่อเรียกเสียงขลุ่ยเหมือน Offline; ยึด gain/cooldown จาก audio mixer เดิม. หมาป่า/หมูป่า/Spawn/Facing fix BR อยู่ครบ.

## แบบทดสอบที่ผ่านในเครื่อง
- `python test_online_parity_v80bs.py`: อ่าน JS Offline ต้นฉบับมาสร้าง 90 case EXP + 10 HP + 1400 Skill Damage MIN/MAX เทียบ Python ผ่าน; EXP เพิ่มจากฆ่ามอน/ไม่จ่ายซ้ำ; LV Up +แต้ม, Stat Vit HP, Skill Mastery, Owner loot ป้องกัน 60 วิ, pickup/inventory isolation.
- `python test_online_protocol_v80bs.py`: 2 Guest World & private self/bag, reject unearned Stat/Skill and server-confirmed J flute cast.
- `python test_security.py`: 2 Guest join, Lv1 HP1200, ปฏิเสธ HP/Damage/Level injection, packet spam, 20 beasts.
- `python test_beast_parity_v80bq.py`: 30 WebSockets และ 20 mobs server, respawn/hit recoil.
- `python test_balance_v80bo.py`: 5 formula/back-end security checks.
- `node tests/test_bot_stress_selection_v80bp.js`, `test_pvp_hp_pve_zone_v80bn.js`, `test_skill_tree_v80am.js`, `test_loot_rules_v80ab.js`, `TEST_WOLF_DIRECTION_V80BR.js` ผ่าน.
- Node `--check` สำหรับ Inline `index.html` และ `jianghu-ui.js` ผ่าน.
- **ไม่ผ่าน browser visual QA** เพราะ Chromium ใน environment ถูกบล็อก HTTP localhost (net::ERR_BLOCKED_BY_ADMINISTRATOR), ไม่ใช่ JS error. ยังไม่มีผล Performance Netlify/Render/Safari จริง. เทสต์เสียง legacy v80BJ บางตัวอ้าง script BJ เก่าไม่ตรงกับฐานล่าสุด BM; ไม่ให้นำมาอ้างว่าเสียงเสียโดยไม่มี runtime repro. เทสต์ pickup_sound_BM อ้าง original file outside ZIP, เลยรันไม่ได้ใน environment นี้.

## ช่องว่างสำคัญที่ต้องทำต่อ (เรียงลำดับ)
1. **ตัวละครและการบันทึก**: Guest ยัง ephemeral ไม่ใช่ account; ต้องออกแบบ Auth + Supabase persistent character rows/RLS/Secure reconnect; ห้ามเอา Offline localStorage ไปเชื่อว่าเป็นข้อมูลผู้เล่นออนไลน์.
2. **อุปกรณ์จริง/เกราะ**: มี item template/weapon drops และ Bag ชั่วคราวแล้ว แต่ยังไม่มี equip/unequip/enhance/affix server-authoritative, gear bonus DEF/MaxHP/ATK/MaxSP; PvP gear & 0/+5/+7 test presets ไม่ใช่ Owned Equipment. ต้องพอร์ตจาก equipment catalogs/games specs แล้วทดสอบ DEF K=250 ครบ.
3. **ปราณ/ชั้นปราณ/โบนัส/Skill passive**: ยังไม่มี server-owned active equip books/ranks/inner-art effects (`flute_echo`, `flute_sustain`, `death_mark`); ไม่ควรเปิดปุ่ม Offline Qi ให้แก้ค่าบน Server โดยตรง. หมายเหตุผู้ใช้ล็อก Qi ช่อง Lv20/40/60.
4. **EXP assist / kill credit**: Patch นี้ให้ Last Hit Killer เท่านั้น; ต้องออกแบบ party/assist contributor โดย server เพื่อกัน steal/infinite exploits.
5. **มอนแมพ Premium/Manual/Humanoid และโหมด AI เพิ่มเติม** ยังไม่ได้พอร์ต, รวมถึง level-specific HP/DEF monster test controls, telegraphs/heal/challenge.
6. **เกมต่อสู้เต็ม/PvP** combo3 hit, knockdown, guard-break, skill cost/proc/crit/hit/flee/AGI จูนครบ ไม่ใช่แค่ projectile สูตรฐาน.
7. **แผนที่ใหม่ / warp / บอท 120s weighted random tiles**. v80BP Bot Stress อยู่และใช้งานต่อได้ แต่แพตช์นี้ไม่ได้แทนระบบ AUTO ดั้งเดิมของผู้เล่น Offline. Vertical Map/Navigation link ยังต้องทำ.
8. **เสียง/ภาพ** ตรวจ event-by-event บน browser จริง / iPad, latency/performance ~30 viewers; SFX gain locked ห้ามเปลี่ยน.
9. **โคลน 100% ต้องตรวจ diff ต่อ subsystem และ visual/gameplay playtests** จึงจะกล่าวว่าเสร็จได้. ส่วน Offline balance lab มีปุ่ม sandbox, ไม่จำเป็นต้องเอาปุ่มโกงทดลองเหล่านั้นไปลง Online ผู้เล่นจริง.

## วิธี Deploy (ห้ามสลับลำดับ)
1. แตกไฟล์ Backend v8.0BS แล้วแทน `server.py`, `combat_progression_v80bs.py`, `exp_balance_v1.json`, `loot_templates_v80bs.json` และ Test/Handoff ที่แนบไป **ใน Root ของ GitHub**. Render ต้องมีไฟล์ JSON ทั้งสองข้างไฟล์ Python.
2. รอ Render Auto Deploy Live; `/healthz` ต้องแสดง `wuxia-online v8.0BS progression + beast-map common`. Render Logs ต้องมี `EXP balance: supabase-exp_v1` หรือ fallback message ที่อธิบาย.
3. อัปโหลด Netlify ZIP v8.0BS; ในหน้าเลือกตัวละครเลือก Guest Online. ลองตีฆ่ามอนและดู EXP +, ถ้าขึ้นเลเวล 2 ลองอัป VIT/INT/Flute Mastery; เดินเก็บของ ดู Bag และฟังเสียง pickup; เทส 30 Bot/ประสิทธิภาพ.
4. Backend v8.0BQ เก่ายังส่ง `welcome` และ Snapshots แบบเก่าได้ แต่ Netlify v8.0BS จะไม่เปิด Stat/Skill Server ถ้าไม่มี `self`. เทสให้ตรงเวอร์ชันทั้งคู่.

## กฎ Handoff ทุกแพตช์
ต้องทำและบันทึก impact assessment ระหว่าง: Offline JS, Online client index/UI, Online authoritative Python server, data manifest, Supabase tables & RLS, assets/audio, bot/map, tests + deployment docs. Version/handoff/changelog และ asset map ต้องอัปเดตทั้งสอง ZIP. **ห้ามบอกว่าออนไลน์เหมือนออฟไลน์ 100% จนตรวจครบทุกระบบ.**
