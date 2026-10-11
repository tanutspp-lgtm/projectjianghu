WUXIA FLUTE ARENA v7.9G — FOREST PARALLAX BACKGROUND
====================================================
ต่อยอดจาก v7.9F FOREST TILESET IN GAME — ฝั่งเว็บเท่านั้น

ของใหม่:
- เพิ่มภาพ 5 ชั้นที่อยู่ใน assets/backgrounds:
  bg_00_sky.png             ท้องฟ้า (ภาพนิ่งฐาน)
  bg_01_clouds_source.png   เมฆจาก AI ต้นฉบับเก็บครบ
  bg_01_clouds_loop.png     เมฆที่ทำขอบ alpha ให้ค่อย ๆ จางสำหรับเลื่อนวน
  bg_02_far_mountains.png   แนวภูเขาไกล
  bg_03_mid_forest.png      แนวป่าไผ่และป่าภูเขาระยะกลาง
  bg_04_foreground_leaves.png ใบไม้ชั้นหน้า (แสดงเบา ๆ เฉพาะขอบบน)
- ภูเขา/ป่าขยับตามกล้องต่างความเร็ว (Parallax); ไม่วนภาพภูเขา/ป่าทั้งแผ่น เพราะต้นฉบับไม่ seamless
- เมฆลอยเองประมาณ 5.5 พิกเซลหน้าจอต่อวินาที (ขณะที่เกมรัน)
- เก็บพื้น ชั้นลอย เชือก บันได และข้อมูล collision ของ v7.9F ไว้เดิม
- ไม่เปลี่ยนโค้ดเซิร์ฟเวอร์ ไม่มีการ Deploy ออนไลน์

ตรวจสอบ:
- ตรวจใน Chromium แบบทดสอบ embedded-asset (เครื่องทดสอบบล็อก localhost/file://)
- BG 5/5 โหลดและวาดบน canvas ผ่าน, forest 34/34 โหลดผ่าน
- เปิดจอคอม 1280x720 และจอแนวนอนมือถือ 844x390 ได้โดยไม่พบ pageerror
- ทดสอบขยับกล้องจาก cam 0 ไป 833 และเก็บ screenshot จากเกม
- บันทึกภาพ QA/FOREST_PARALLAX_*.png

ข้อจำกัด:
- ภาพ AI ต้นฉบับกว้าง 2172x724; ไม่ใช่ขนาด 3072px ที่เคยร้องขอ
- ภูเขา/ป่ายังไม่ใช่ seamless; ในแผนที่นี้ใช้แบบ pan-clamp ไม่วนซ้ำ
- รูปต้นฉบับมี fringe alpha บางจุด; ปรับเฉพาะเมฆ loop ขอบจางไว้ก่อน
- ยังไม่ได้ทดสอบกับ Netlify/Render จริง และไม่มีการทดสอบ multi-player live server

วิธีเล่น:
- แตก ZIP และ Deploy โฟลเดอร์ที่มี index.html ขึ้น Netlify แบบ static
- เริ่มในโหมดฝึกออฟไลน์ (ไม่ต้องเปิดเซิร์ฟเวอร์)
- โหมดออนไลน์ใช้เซิร์ฟเวอร์แยกตามเวอร์ชันที่ Deploy อยู่; AUTO ออนไลน์อาจต้อง server v7.9

Debug status:
 window.__wuxiaBgVisualStatus  // การโหลด layer, cameraX, clockSeconds
 window.__wuxiaForestVisualStatus // การโหลด forest sprites
