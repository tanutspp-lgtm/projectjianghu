# Online Security Audit — v8.0BU (เฉพาะโค้ดและ local WebSocket)

## ที่แก้ทันที
- [FIX] เปิดคำสั่ง QA ระดับเลเวล/ปราณ/เซ็ตได้จาก Guest ทั่วไปเมื่อใช้ BT: ใน BU เปิดได้เฉพาะเมื่อตั้ง ENV ENABLE_GUEST_SANDBOX=1 (ค่าเริ่มต้น 0). Production ควรเก็บค่า 0 เสมอ.
- [FIX] Client ส่ง `auto` พร้อม x, y, damage, target, path ไม่ได้: strict key schema เหลือ enabled bool; ตัวเซิร์ฟเวอร์สร้างเป้าหมาย/คำนวณเคลื่อนที่เอง.
- [FIX] `input.pressed` ส่ง list/dict ซ้อนมาแล้วเกิด unhashable exception: ปฏิเสธเป็น protocol violation.
- [FIX] Monster HP/DEF อยู่บน Python และไม่รับ `monster_preset` จาก Client, ยิงมอนใช้ DEF K250 ของเซิร์ฟเวอร์, ไม่มีการแก้รางวัลเมื่อ Client แก้ภาพ.
- [EXISTING] Server คุมตำแหน่ง/คูลดาวน์, ความแรงสกิล/EXP/Drop จากมอนตายจริง, range/speed ของ projectile, rate limit packet 35/s actions 12/s, id sequence monotonic. ห้ามอ้างว่าโกงไม่ได้ 100% เพราะ threat model ยังไม่ครบ.

## ความเสี่ยงที่ต้องทำก่อนเปิด Public MMORPG
- **P0: No authenticated/persistent account** — Guest ใครก็สร้างตัวละครจำนวนมากได้; ต้องทำ auth+session binding, ใครเป็นเจ้าของ item/stats, authenticated rate limiting, server-side persistence/transaction atomicity, RLS.
- **High: Guest slot exhaustion / socket flood** — MAX_GUESTS=35 กันจำนวนต่อห้อง แต่ไม่กันแหล่งเดียวเปิดหลาย connection จนเต็ม, ไม่มี per-IP / account quotas หน้า proxy. เพิ่ม reverse-proxy WAF/quotas และ verified identity แล้วค่อยเปิด.
- **High (configuration): ENABLE_GUEST_SANDBOX=1** ให้ Guest ทดลอง Lv60/gear/qi แตะ stat จริงบนเซิร์ฟเวอร์ได้! ให้ใช้ QA เท่านั้น; public 0.
- **Medium: Open WebSocket Origin when ALLOWED_ORIGINS blank** — ตั้งรายการ Netlify Origin จริง; Origin ไม่ใช่ Auth: external bot ไม่ส่ง Origin ก็อาจเชื่อมได้. ต้องทำ identity และ anti-abuse ต่อ.
- **Medium: Offline/Online game-rule drift** — มอน Pounce ไม่ครบ; geometry Client/Server เป็นไฟล์ต่างกัน; PvP damage/LOS/knockdown mechanics ยังต้องออดิท. การยิงทะลุสิ่งกีดขวางหรือ packet ที่ timing ผิดต้องมี integration test เพิ่ม.
- **Medium: Logs/metrics** — ยังไม่มี anomaly telemetry สำหรับจำนวน packet, farm kills/minute, session churn, speed, quest/loot economics. เพิ่มก่อนผลิตจริง.
- **Medium: Economy** — ระบบตลาด/อุปกรณ์จริง/การบันทึกยังไม่ทำ, ควรบังคับ server transactions + idempotency keys, atomic ownership transfer กัน dupes.

## Regression ที่ทดสอบผ่าน
- malformed join/avatar/forged HP input/sequence replay/action flood เดิม,
- forged AUTO coords/damage/boolean/extra keys, malformed pressed nested objects/lists,
- QA gear command rejected in production default,
- 30 simultaneous real WebSocket Guests AUTO + authoritative 20 beasts, private snapshot and XP/loot regression,
- Monster HP/DEF/damage mirror Offline presets, no user-authored damage,
- Navigation on 4 platforms/rope and no-air goals on single-layer map.

**Scope limit:** ทดสอบเฉพาะ isolated localhost ไม่ใช่ pentest แบบ authenticated production deployment, database permission audit ทั้งระบบ, network/DDoS resilience หรือ performance ของ Render จริง. ห้ามประกาศปลอดภัย 100%.
