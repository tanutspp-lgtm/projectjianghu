# PROJECT JIANGHU v7.9N — Account / Durable Character / EXP vertical slice

## เพิ่ม

- Supabase Auth สำหรับบัญชีแบบ email/password ใน static client โดยใช้เฉพาะ URL และ publishable key ฝั่ง browser
- ตรวจ access token ฝั่ง Game Server และรองรับ refresh ระหว่าง WebSocket session
- schema/migration เพิ่ม `characters` และ idempotent `character_exp_ledger` โดยไม่แก้ตาราง balance เดิม
- local SQLite adapter และ mock Auth integration test เพื่อทดสอบ create/load/relog/server restart โดยไม่ต้องใช้ secret จริง
- EXP จากการฆ่ามอนสเตอร์แบบ server-authoritative, level-gap rules, Lv60 cap, multi-level award และ contribution share ป้องกันการแตะมอนน้อย ๆ เพื่อ powerlevel
- Character EXP HUD และตำแหน่ง tracked Qi EXP HUD ที่คำนึงถึง safe area
- แยกโมดูล `protocol.py`, `auth.py`, `progression.py`, `persistence.py` ออกจากเกมลูปเดิมแบบ incremental

## คงเดิม

- Sprite และ preview ทั้ง 30 แบบ
- animation frame mapping, damage/cooldown/combat inputs, movement, collision, ladder/rope, AUTO PvE behavior
- forest tiles, backgrounds, parallax, FX, loading gates และ touch controls
- Guest online mode

## ไม่ได้ทำ

- ไม่ Deploy และไม่แก้ Supabase production
- ไม่เพิ่ม Qi progression, inventory, crafting, Skill Tree หรืออาชีพต่อสู้อื่น
- ไม่แก้ balance `exp_v1`
