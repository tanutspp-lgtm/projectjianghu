# Jianghu v8.0CM: CPU cache optimization — เตรียมทดสอบ (ยังไม่ Deploy)

**ฐาน**: GitHub `tanutspp-lgtm/projectjianghu` main `server.py` blob SHA `48050cfde4fa1d3421da373258b2c3cbc20e13ec` (ตรวจรูปแบบก่อนแก้ 3 จุดครบแล้ว)

## สรุปการแก้

เดิม `update_guest()` เรียก `prog.derive_stats()` ทุก 30Hz/คน และเรียกซ้ำเมื่อผู้เล่นเดิน ขณะที่ระบบมี `derived_for_snapshot(p)` ซึ่งสร้าง signature จากเลเวล สเตตัส ปราณ และเกียร์ แล้ว Cache ค่า derived อยู่แล้ว

แพตช์นี้เปลี่ยน 3 จุดใน `server.py`:

1. ใน `update_guest`: `derived=prog.derive_stats(p,hp_reference)` → `derived=derived_for_snapshot(p)`
2. ในการคำนวณความเร็วเดิน: ใช้ `derived['moveSpeedMultiplier']` จากค่าเดียวกันใน Tick นั้น
3. ใน `update_mob` ตอนตรวจหลบมอน: `prog.derive_stats(...)` → `derived_for_snapshot(p)`

**ไม่เปลี่ยน** สูตร Damage, Regen, Skill, Gear, HP, Physics 30Hz, Snapshot 10Hz, ระบบตีมอน, AUTO decision 10Hz, หรือ Anti-cheat. จุดเปลี่ยนคือ Cache ค่า derived จนกว่า signature ที่ประกอบด้วยเลเวล/สเตตัส/ปราณ/เกียร์จะเปลี่ยน

## ใช้กับ repo อย่างไร

วาง `apply_perf_cache_v80cm.py` ไว้ใน Root ของ repo ร่วมกับ `server.py` แล้วรัน:

```sh
python apply_perf_cache_v80cm.py --check
python apply_perf_cache_v80cm.py --apply
python -m py_compile server.py
```

เมื่อทดสอบแล้วพบ Regression สามารถคืนค่าจาก Back-up ได้ด้วย `python apply_perf_cache_v80cm.py --restore`

> ยังไม่ได้รันเกมจริงหรือ Deploy แพตช์นี้ เพราะ GitHub connector ตอบ 403 ตอนสร้าง Branch และเครื่องมือท้องถิ่นไม่สามารถเข้าถึง Repository ข้างนอกได้. Script จะไม่แก้ไฟล์หากรูปแบบไม่ตรงต้นฉบับ.

## QA ก่อน Merge/Deploy

- เทียบสูตร HP/SP/Stamina Regen, ความเร็วเดิน, ดาเมจโจมตี/คริติคอล ก่อน–หลังแพตช์
- เปลี่ยน Level, เพิ่ม STR/AGI/VIT/INT, เปลี่ยน Gear Preset, อัปเกรดปราณ แล้วตรวจว่าค่า Derived อัปเดตทันที
- เปรียบเทียบ Bot Test 0, 10 และ 30 ตัว ระยะ 2–3 นาทีต่อชุดใน Render staging หรือ VPS เดียวกัน ไม่รัน Production พร้อมกัน
- ดูค่า CPU core usage, tickP95Ms, loopP95Ms, snapOverwritten, Snapshot Gap P95, Ping และ FPS
- อย่าสรุป % เร็วขึ้นจนกว่าจะทดสอบก่อน–หลังในสภาพแวดล้อมเดียวกัน

## ขั้นต่อไปที่ควร Profile หลังแพตช์

- `aoi_view`: ปัจจุบันไล่หา entity จาก shared world สำหรับ **ผู้รับแต่ละคน** ทุก Snapshot; ถ้าขยายเป็น 60 คน/Channel ควรทดลอง Spatial Buckets / Per-map index
- `encode_aoi_delta`: สร้าง diff/JSON และ private stats ต่อ Guest ทุก 100ms; ปรับเฉพาะหลังวัด Profiler
- `advance_loot`: ไล่ตรวจ Player สำหรับ Loot แต่ละรายการทุก Tick; ควรสร้าง spatial lookup เมื่อจำนวน Loot สูง
- `update_shots`: ตรวจ Monster ทั้งหมดต่อ Projectile ทุก Tick; อาจใช้ spatial index ถ้าจำนวนมอน/กระสุนสูง

**ระวัง:** ไม่มีหลักฐานรองรับว่าจะได้ตัวเลข FPS/Ping ดีขึ้นกี่ %; Ping ที่สูงขึ้นจาก Render CPU Throttle จะตอบได้ด้วยการวัดก่อน–หลังเท่านั้น
