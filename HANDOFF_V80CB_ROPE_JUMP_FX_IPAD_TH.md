# PROJECT JIANGHU — v8.0CB: Rope/Jump Sync, Visible Flute Wave, iPad Frame Budget

เวอร์ชันฐาน: v8.0CA — Responsive Walk + PvE-only (no PK). อัป Backend ก่อน แล้วอัป Netlify. **ยังไม่ Deploy ให้**

## สาเหตุจากคลิป 2026-10-14 และจุดแก้

1. **บันได/เชือกฝั่ง Server กับ Frontend ไม่ตรงกัน (ต้นเหตุเชิงข้อมูลจริง):** ตรง X=1170 Browser กำหนด `top=390` แต่ไฟล์ `beast_map_common_v80bq.json` บน Server เดิมใช้ `top=235` (ต่าง 155px) ทำให้ Server ปีนขึ้นเหนือหัวบันไดที่เห็นบนภาพได้. แก้ Server เป็น (x=1170, top=390, bottom=550) แล้วเพิ่มทดสอบ Geometry Parity ทั้ง 3 เส้น.
2. **กระโดดกระตุกจาก Snapshot 10Hz:** Client เดิมทำนายแกน X แต่ Y กระโดดตาม Snapshot; เพิ่ม visual-only jump anticipation จากปุ่มกระโดดทันที, ประมาณตำแหน่งจาก authoritative `vy` + `g=1400`, จำกัดระยะ ahead และ correction. Snap ในจังหวะเข้า/ออกเชือกหรือ landing (transition ไม่ใช่เส้นทาง Smooth) และไม่ทำนายต่อเมื่อ Snapshot เก่ากว่า 750ms. Server ยังคำนวณ hitbox, การชนพื้น, ตกพื้นและโจมตีทั้งหมด.
3. **คลื่นขลุ่ยหาย:** กระสุนอยู่ไม่ถึง Snapshot รอบต่อไป โดยเฉพาะยิงโดนมอนใกล้. เพิ่ม visual cast metadata ใน event (`owner`,`shotId`,`shotX`,`shotY`,`shotDir`,`shotSpeed`) และคลื่นภาพอายุสั้นที่ Client โดยไม่สร้างดาเมจ/Hit ปลอม. ดักภาพซ้ำระหว่างคลื่นชั่วคราวกับกระสุนที่ Server ยืนยัน. Asset `fx/shot_*.png`, `fx/aoe_travel_*.png`, `fx/break_travel_*.png` เดิมทั้งหมด ไม่เจนภาพใหม่.
4. **iPad FPS:** ปรับ Canvas DPR แบบ adaptive เฉพาะ Online: ถ้า FPS < 42 ติดต่อกัน 3 วินาที ลด DPR cap 1.5 → 1.25 → 1.0; ถ้า FPS >56 ติดต่อกัน 12 วินาที ค่อยเพิ่มกลับ (hysteresis). รักษาคุณภาพ/เฟรมของ sprite, ไม่ลด server tick 30Hz และไม่เพิ่ม snapshot 10Hz. การลด DPR อาจทำภาพเบลอขึ้นบนจอ Retina; ไม่รับประกัน FPS เพิ่มจนได้ลองเครื่องจริง. Cache พื้นแมพจาก v8.0BZ ยังอยู่.
5. **Performance:** Prediction ใช้เฉพาะตัวละครของผู้เล่น และภาพคลื่นจำกัด 16 ชิ้น ไม่รัน AI ซ้ำบน Browser. Packet event เพิ่มข้อมูลขนาดเล็กเฉพาะตอน cast, ไม่เพิ่ม snapshot frequency.

## Files ที่แก้
- Server: `server.py`, `beast_map_common_v80bq.json`, `test_v80cb_cast_trail.py`, `test_v80cb_map_and_transitions.py`.
- Frontend: `index.html`, `online_delta_prediction_v80by.js`, `test_v80cb_client_prediction.cjs`.
- Handoffs ใน ZIP ทั้งสอง: `HANDOFF_V80CB_ROPE_JUMP_FX_IPAD_TH.md`, `HANDOFF_LATEST_TH.md`(front), `CHANGELOG_LATEST_TH.md`(front), `HANDOFF_PERFORMANCE_FIRST_V80BW_TH.md`(ไม่ลบ).

## Validation executed locally
- Node syntax: inline `<script>` (main classic script) and `online_delta_prediction_v80by.js` passed `node --check`.
- JS predictor test: immediate jump first frame, finite jump, rope vertical clamp, entry/exit snap, >750ms stale snapshot freeze — PASS.
- Python unittest 17 cases — PASS (map geometry, real ladder top 390 exit, unchanged no-PK, attack event visual-only, security/balance/auto).
- AUTO route regression 20/20 platform pairs — PASS, no teleport.
- 30 independent real WebSocket + server-authoritative AUTO, AOI/Delta: 30/30 clients, 653 snapshots, 2.39 MiB received in about 2.2s (local machine, not Render/Safari) — PASS.
- Audio files preserved byte-for-byte from CA; existing monster and movement sprites untouched.
- Browser end-to-end: Attempted Chromium Playwright but local web navigation returned `ERR_BLOCKED_BY_ADMINISTRATOR`; NOT verified visually on browser or Safari.

## Security and PvE invariants
- No PK / PvP auto-hit; server ignores all other player bodies for projectile hitchecks. Physical projectile collisions only with monsters; no friendly stun/guardbreak.
- Client may only send input state/buttons/actions, never player coordinate, HP, damage, frame, cast result. Server authoritative remains on.
- AUTO owner is server; 120s destination; floor distribution as locked; rope navigation and hitstun remain.
- No sound gain changes: hit .78, flute .24, boarDeath .66, wolfDeath .67, jump .52, pickup .42; pickup unlimited no throttling.

## Deployment
1. Extract `PROJECT_JIANGHU_SERVER_v8_0CB_ROPE_JUMP_FX_IPAD_GITHUB.zip` to repo root `tanutspp-lgtm/projectjianghu` and commit (do NOT upload zip as one file). Wait Render live.
2. Check `https://projectjianghu.onrender.com/healthz` contains `v8.0CB`.
3. Deploy full `WUXIA_FLUTE_ARENA_v8_0CB_ROPE_JUMP_FX_IPAD_NETLIFY.zip` to Netlify. Refresh with cache bypass/new tab.
4. Test solo: jump near monsters, up/down X1170 ladder, other X510/X1590 ropes, flute wave on near hits. Repeat AUTO, tabs background/resume, 10/20/30 stress bots. `?perf=1&botstress=1` shows actual FPS and Tick P95. Do not extrapolate from local WebSocket results to iPad FPS.

## Known limitations / next steps
- Visual jump is speculative; if server rejects it due stun/cooldown/landing, Client will correct its image. Server positions remain definitive. A network jitter spike can still trigger corrections.
- This version addresses a proven rope data mismatch, but does not guarantee all network interpolation artifacts resolved. Need real Safari recordings of jump/rope and FPS before/after.
- iPad 2D Canvas adaptive quality may trade resolution for responsiveness. Requires field validation across 1/10/20/30 users and monitoring memory/CPU/RTT.
- Server Render Free limits, connection failures, or older deploy still need separate diagnosis. Frontend/Backend v8.0CB pair recommended.
- PvP deliberately remains disabled; no lag compensation for future PvP implemented.

## Performance-first permanent checklist
For every future change, compare client FPS/frame time/heap/GPU pressure/audio and server tick P95/P99/CPU/RAM/WebSocket/Snapshot KB/s at 1,10,20,30 Guest; maintain Offline source parity and server anti-cheat; avoid unnecessary allocations, extra AI on client, overproduced particles, and hidden stale-position queues.
