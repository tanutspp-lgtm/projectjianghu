# HANDOFF — Project Jianghu / WUXIA FLUTE ARENA v8.0CI

วันที่ 15 ต.ค. 2026 — Patch: DASH INTO WORLD WALL CAUSES FALL-THROUGH-FLOOR

## ข้อผิดพลาดที่รายงาน
ผู้เล่นยืนชิดขอบซ้าย/ขวาของแผนที่ แล้ว Dash เข้าหากำแพง ตัวละครทะลุลงไปใต้พื้น ทั้งในสถานการณ์ที่ไม่มีใครโจมตี เป็นบั๊กฟิสิกส์ ไม่ใช่ปัญหาเน็ตหรือ Client Prediction

## สาเหตุที่พิสูจน์ได้จากโค้ด
`server.py:physics()` และ `index.html:physics()` รับพิกัด X ที่ขยับแล้วด้วยความเร็ว Dash 650 units/s แต่เดิมเช็กพื้นด้วย `can_stand`/`canStand` **ก่อน clamp X เข้าเขต world 27..WORLD_W-27**. ขณะชนกำแพง x ที่ชั่วคราวออกนอกเขตทำให้ one-way-floor ไม่มี support; พอตัวละครตกต่ำกว่าพื้นเดิม 7 units ก็ไม่เข้าเงื่อนไข land จากด้านบนอีก แม้ x ถูก clamp กลับมาแล้ว

ก่อนแก้ ทดสอบ Server จาก X=27 หรือ X=2033 กด Dash เข้ากำแพง 35 ticks ที่ 30Hz: Y เริ่ม 550 → 788 และ ground=False **ทั้งสองข้าง**. หลังแก้: Y=550 ground=True ตลอด

## สิ่งที่แก้ใน v8.0CI
1. `server.py`: ใน `physics(actor,dt)` ย้าย `actor.x=clamp(actor.x,27,WORLD_W-27)` ไปทำก่อนคำนวณแรงโน้มถ่วงและ floor collision, ไม่ทำ clamp ซ้ำท้ายฟังก์ชัน
2. `index.html`: `physics(u,dt,isPlayer)` clamp X ก่อน `canStand` เหมือนฝั่ง Server; ไม่เพิ่มการทำนายตำแหน่ง Client และไม่เพิ่ม snapshot rate
3. เพิ่ม Regression Test สองฝั่ง: `test_v80ci_wall_dash.py` + `test_v80ci_wall_dash.cjs` สำหรับ Dash ติดขอบ, Knockback ติดขอบ, และ Jump+Dash ที่ขอบ (รวม 20, 30, 60 FPS)
4. Version HUD/profiler updated to v8.0CI; Backend `/healthz` updated `v8.0CI`

## ผลทดสอบในเครื่อง (ไม่ใช่ Safari จริง)
- ก่อนแก้ repro ได้: x=27 และ x=2033, หลัง Dash 35 tick y=788 ตกพื้น
- หลังแก้ repro เดิมผ่าน Server ที่ dt 1/20, 1/30, 1/60 (y=550 ตลอด)
- `python -m unittest discover -p 'test*.py' -q`: 31/31 PASS
- `node test_v80ci_wall_dash.cjs`: PASS, รวม 20/30/60FPS, อากาศ → พื้น
- `python test_v80ce_ping_ws.py`: PASS
- `python test_v80by_30_delta_sockets.py`: 30 Guest/AUTO ต่อ WebSocket สำเร็จ, ~2.34 MiB / 2.2 s localhost (ค่ารอบนี้เท่านั้น)
- `node --check` main inline JS: PASS
- Existing tests for Mana FX (CG), Server-first (CC), projectile snapshot (CD): PASS

## ขอบเขตเดิมที่ห้ามถอยกลับ
- สถานะ Offline และ Online ใช้ฟิสิกส์ขอบแมพแบบเดียวกัน; Server เป็นเจ้าของตำแหน่ง, damage, HP, combat, drops, XP, monster AI และ AUTO
- Renderer v8.0CC Server-first; ห้ามเติม speculative walk/jump/rope
- UI ของ v8.0CH: FPS/Ping มุม HUD ที่มองเห็นจริง และ mana-verified cast FX v8.0CG คงเดิม
- หัวบันได X=1170 top=390; ไม่ให้ปีนทะลุ; WebSocket RTT เป็น Ping จริง และยิงไม่โดนผู้เล่นอื่น (PvE PK OFF)
- คงฟิสิกส์แรงโน้มถ่วง 1400, ความเร็ว Dash 650, STA cost/cooldown และแนวทาง PvP-first balance เดิม
- ไม่แตะ Asset/Sprite/SFX, ความดังเสียงที่ล็อก, เซิร์ฟเวอร์ AOI/Delta/30Hz tick/10Hz snapshot, 120s AUTO และปริมาณข้อมูล snapshot
- Performance-first: โปรไฟล์ FPS/frametime/browser memory, server tick/CPU/RAM, จำนวนผู้ใช้ 1/10/20/30, data traffic และ security ทุกแพตช์ต่อเนื่อง

## วิธี Deploy (ต้องอัปทั้งสอง ZIP)
1. แตก `PROJECT_JIANGHU_SERVER_v8_0CI_DASH_WALL_COLLISION_GITHUB.zip` แล้วอัป **ไฟล์ข้างใน** ทับไฟล์ชื่อเดิมที่ GitHub repo root. อย่าลบไฟล์อื่นที่ไม่ได้อยู่ใน ZIP. Commit แล้วรอ Render Live
2. `/healthz` ที่ `https://projectjianghu.onrender.com/healthz` ต้องเห็น `v8.0CI`
3. อัป `WUXIA_FLUTE_ARENA_v8_0CI_DASH_WALL_COLLISION_NETLIFY.zip` ไป Netlify. หน้าเกมควรแสดง `v8.0CI SERVER-FIRST PVE`
4. QA เล่นจริง: ยืนชิดขอบแผนที่ซ้ายและขวาชั้นล่าง → Dash เข้ากำแพง 10-20 ครั้ง → Jump+Dash เข้าใส่กำแพง → Knockback เข้ากำแพง; ต้องไม่ตกใต้พื้นหรือเสีย HP จากการตก. แดชกลางแมพ ปลายแพลตฟอร์ม และปีนบันไดยังทำงานปกติ
5. หากยังผิดหลัง Deploy ทั้งคู่ ให้ส่งวิดีโอ/ภาพ FPS+Ping และตรวจ `?perf=1`; แยก physics จาก network. ยังไม่มี QA Safari/iPad จริงสำหรับรุ่นนี้

## Pending
- ตัวเกม Online ยังเป็น Guest / ไม่มี account persistence; PvP ปิด PK อย่างตั้งใจ. ต้องมี PvP time synchronization/lag compensation ก่อนเปิดจริง
- Renderer FPS iPad ยังต้องวัดในเครื่องจริง, ไม่อ้างว่า FPS ดีขึ้นจากแพตช์ฟิสิกส์นี้
- ประเมิน boundary collision ทุกประเภท (teleport, skill displacement, mob knockback) ในแพตช์ถัด ๆ ไป
