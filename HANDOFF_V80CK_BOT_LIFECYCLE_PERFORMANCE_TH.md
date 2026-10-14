# Project Jianghu v8.0CK — Bot Stress Lifecycle & Latency Diagnostics (15 Oct 2026)

## ปัญหาที่ผู้ใช้รายงาน
- เมื่อเพิ่ม Guest Bot Stress 10/20/30 ตัว เกม Online หน่วงและสั่น แม้มอนตาย/ผู้เล่นดูเหมือนยืนเฉย
- กดล้างทั้งหมดแล้วรู้สึกแลคค้างต่อ; ก่อนหน้านี้ตัวนับ Local ถูกล้างทันที โดยไม่รอ WebSocket close / server cleanup
- สลับแท็บไปคุยแล้วบอทหายหมด: **เดิมมี code ตั้งใจ stop() เมื่อ document.hidden**, ไม่ใช่การตัดโดย OS เสมอไป
- Snapshot Gap ~105–197ms, Browser FPS บางช่วง ~165; Server Tick P95 ต่ำไม่ได้พิสูจน์ว่า Event Loop ไม่ติดขัด

## แก้จริงในเวอร์ชันนี้
1) `bot_stress_v80bp.js` (คงชื่อไฟล์เดิม, bump query asset version): เมื่อซ่อนแท็บไม่สั่งลบบอทอีก; หาก WS หลุดโดยไม่ตั้งใจเมื่อกลับมา foreground พยายาม reconnect ทีละ socket ทุก 500ms สูงสุด 3 ครั้ง/slot. Browser/OS อาจ discard tab หรือระงับ network ได้อยู่.
2) กด Clear: ยกเลิกรายชื่อ/คำสั่งใหม่ แล้วส่ง WS close ให้แต่ละ socket, **นับจำนวนที่ยังรอ close event** ใน UI จนได้รับการปิดจริง; ไม่หลอกว่า Local=0 แล้ว Server ต้อง=0. แสดง `Server N คน` จากข้อมูลทาง Server ทุก ~1s ซึ่งนับคนอื่นด้วย (บอท 30 + tester =31).
3) แสดง `Loop lag P95` เมื่อ Backend CK ส่งข้อมูล, เพิ่ม `Snapshot encode P95` และ `Server guests` ใน `?perf=1` overlay; ตัวเลขไม่ใช่ CPU-percent.
4) `online.netSmooth.forget('peer:'+id)` เมื่อ peer ออกจาก AOI — ไม่สะสมประวัติของบอทหลาย generation. ไม่เปลี่ยนตำแหน่ง/physics.
5) Backend `server.py`: แยก scheduler event-loop lag และการ encode snapshot เพื่อจับ CPU stalls ที่ตัวนับ tickP95 ตัวเก่ามองไม่เห็น. `perf_data.playerCount` มีอยู่แล้ว, คง protocol AOI/delta เดิม.
6) Server AUTO: ยังคำนวณฟิสิกส์/Hit/Guard ที่ 30Hz, แต่ Navigation.choose ทำสูงสุด ~10 ครั้ง/วินาที/Guest แทน 30, คงเป้าหมายอิสระทุก120วินาที, สูตรทำดาเมจ, ค่า Stat, Sprite, Sound ไม่เปลี่ยน.

## ทดสอบในสภาพแวดล้อมนี้
- Python/Node Syntax, old regressions: `test_v80bu_monster_auto.py`, `test_v80bx_live_navigation.py` routes 20/20, `test_v80ce_ladder_rtt.py`, `test_v80bz_performance_regression.py`, `test_v80cd_protocol_regression.py`, `test_v80ci_wall_dash.py`, `test_v80by_delta_security.py`, `test_v80ce_ping_ws.py`, test stress tile selection. PASS.
- `test_v80ck_30_clear_cleanup.py`: 30 clients real WebSocket with server AUTO, observer counted 31 online, client close all -> serverCount 1 in ~1.00s on localhost; no ghost guests on that run.
- `test_v80ck_bot_lifecycle.js`: hidden tab does not intentionally stop bots; Clear tracks pending close and server count, no rejoin after explicit Clear. PASS (mock DOM/socket).
- 30 sockets 2.2s: ~673 snapshots / 2.34 MiB total received. No full Safari/PC real UI test.
- Benchmark CI vs CK (short isolated localhost runs, NOT Render and not repeatability-certified): 30 Guest CPU use of one core 16.9% -> 15.7%. Improvement small and results vary by load; do NOT claim 30 guests are fixed. RSS local ~102MiB, separate from free Render.
- Render sample during user's 20/30 test CPU 0.10–0.12 of 0.15 vCPU capacity (~67–80% one-minute average); RAM ~50 MiB of ~512 MiB limit; minute averages cannot prove all spikes/throttling.

## Deployment
1. Upload contents of Backend `PROJECT_JIANGHU_SERVER_v8_0CK_BOT_LIFECYCLE_PERFORMANCE_GITHUB.zip` into GitHub root (not ZIP itself), ensure Render `/healthz` says `v8.0CK`.
2. Upload Frontend `WUXIA_FLUTE_ARENA_v8_0CK_BOT_LIFECYCLE_PERFORMANCE_NETLIFY.zip` to Netlify.
3. Open `?botstress=1&perf=1`, connect Guest, add 10/20/30. Record `FPS`, `Snap gap`, `Loop lag P95`, `Snapshot encode P95`, `Server guests`, `Bot N`, and `ปิดค้าง N` before and 10 seconds AFTER Clear. Compare against 0 bot baseline.
4. If after Clear Local Bot 0 / Closing 0 / Server players 1, but still lag: stop attributing it to ghost connections. Compare FPS/JS Heap/SnapshotGap. Browser refresh temporarily resets frontend allocations; do not claim it fixes backend.
5. If Server players stays >1 after 10 seconds and you're alone, inspect Render connection logs; if multiple real users present, Server count includes them.

## Limitations / do NOT overclaim
- Browser tab discard/OS WebSocket suspension may still break 30 bot connections. Retries are capped at 3, and only when tab visible.
- This test starts 30 WS in ONE Browser; it tests Render network/server but adds extra local browser WS load unlike 30 independent computers. Benchmark on separate clients for production scaling.
- The test doesn't prove smoothness under 30 simultaneous actual players; Render's free 0.15vCPU can become bottleneck. More optimization likely needed: snapshot serialization and bandwidth; use new Event-loop lag to verify before patching.
- No PK, no Client Prediction, no altered locked sounds/sprite/loot/drop balance. Old docs preserved.
- Keep latest handoffs and version changelog in each ZIP. Do not delete known legacy files from the repository without dependency check.
