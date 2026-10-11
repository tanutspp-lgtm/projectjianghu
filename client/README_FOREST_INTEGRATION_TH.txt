WUXIA FLUTE ARENA v7.9F — FOREST TILESET IN GAME (visual test)
============================================================

นี่คือไฟล์เกมเว็บตัวเต็ม v7.9 ที่เปลี่ยนภาพแมพเป็น Tileset ป่าเขียวชอุ่มจากภาพล่าสุดของผู้ใช้
ไม่ใช่ภาพม็อกอัพและไม่ใช่ไฟล์อัปเดตเซิร์ฟเวอร์

ใช้งาน: นำไฟล์ ZIP นี้ไปแตกหรืออัปโหลด Netlify แบบ manual deploy โดยให้ index.html อยู่ระดับ root
เปิด index.html จากเว็บแล้วเลือกตัวละคร -> เล่นออฟไลน์ ได้ทันที
ออนไลน์: ยังใช้เซิร์ฟเวอร์เดิม และต้องทำตามคู่มือ ONLINE_SETUP_TH.txt; ไม่มีการ deploy/แก้เซิร์ฟเวอร์
AUTO ออนไลน์ยังต้องรออัปเดตเซิร์ฟเวอร์ v7.9 ตามเงื่อนไขเดิม

สิ่งที่เปลี่ยน
- พื้นหลักเดิม 0–2060, y=550 วาดจาก Grass/Cliff ของ PNG ล่าสุด
- ชั้นลอย 4 ช่วง วาดจาก Rock/Timber floating platforms ของ PNG ล่าสุด
- เชือก 2 จุด และบันได 1 จุด วาดด้วยชิ้นส่วนจาก PNG ล่าสุด
- ภูเขา/ป่าไผ่ Parallax สร้างด้วย Canvas แยกจาก Terrain ไม่มีน้ำตกหรือน้ำเคลื่อนไหวที่ถูกแช่แข็งในภาพ
- คง collision, foothold, climbs, spawn, skill, offline AUTO, character creation, guest online logic เดิม
- ป้อน URL ?debugtiles=1 ต่อท้ายหน้าเว็บเพื่อดูเส้น collision และแนวปีนซ้อนบนภาพ

ไฟล์สำคัญ
- index.html : เกมแก้ renderer แล้ว
- assets/forest/forest_master_original.png : ไฟล์ Tileset AI เดิม ไม่แก้ขนาดหรือจำนวนพิกเซล
- assets/forest/forest_atlas_regions.json : พิกัด source crop แต่ละชิ้น
- assets/forest/*.png : รันไทม์คัตจาก Master / หน้าหินอนุพันธ์แบบต่อเนียน
- tools/build_runtime_tiles.py : โปรแกรมตัดชิ้นส่วนใหม่จาก Atlas ที่มี layout ตรงเดิม (requires pillow/numpy)
- QA/FOREST_GAME_QA_DESKTOP.png และ QA/FOREST_GAME_QA_MOBILE.png : ภาพจาก Chromium ที่รันเกมจริง

สิ่งที่ยังเป็นข้อจำกัด
- ภาพ AI เดิมไม่ได้สร้างจาก Master Geometry ที่รับประกันรอยต่อและ shape mask ทุกชิ้น จึงมีรอยต่อเล็กน้อย
- การตัดเฉพาะตำแหน่งนี้อ้างอิง PNG ขนาด 1774×887; ถ้า AI edit แล้วเปลี่ยนขนาด/จัดช่อง จะใช้ตัดเดิมไม่ได้
- ยังไม่ได้ลงโซนนี้เป็นเซิร์ฟเวอร์จริง และยังไม่ได้เปลี่ยนตัวแผนที่/physics 3 ชั้น
- ฉาก Parallax ปัจจุบันเป็นแบบ procedural ต้นแบบ ไม่ใช่ PNG Background pack แยกแต่ละชั้น

ทดสอบ Chromium Desktop 1280×720 และ Mobile 390×844: assets ภาพที่โหลด 34/34, ไม่พบ runtime JavaScript error
เก็บ ZIP v7.9 ต้นฉบับไว้เสมอ เพื่อย้อนกลับได้
