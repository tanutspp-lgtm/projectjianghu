WUXIA FLUTE ARENA v7.9J – แก้ขอบใบไม้ถูกตัดราบ (เฉพาะฝั่งเว็บ)

- ต้นเหตุ: drawForestNearOverlay() มีคำสั่ง ctx.clip() เป็นสี่เหลี่ยมจบที่ H*0.58 จึงตัดล่างของใบไม้เป็นเส้นตรง
- แก้: ยกเลิก clip; ใช้ PNG เดิมแบบเต็มภาพและอัลฟาเดิม 100% ไม่ทำให้จาง
- เลื่อนการวาด foliage มาไว้หลังฉาก BG แต่ก่อนพื้น/ตัวละคร เพื่อไม่ให้พุ่มใบไม้ด้านล่างบัง gameplay
- เก็บ Parallax factor .37 และ drift ของเมฆ 11 px/sec ตามเดิม
- ไม่แตะ Sprite/Collision/Monster/Auto/Online/Server

ทดสอบ: Chromium หน้าจอ 1584x950 และ 844x390; โหลด background ครบ 5/5 และ terrain 34/34 ไม่พบ page errors
