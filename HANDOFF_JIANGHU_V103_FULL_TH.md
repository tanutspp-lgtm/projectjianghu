# Project Jianghu — ส่งต่องานด้วยไฟล์ตัวเต็ม V103

## อ่านก่อนใช้

มี ZIP สองไฟล์แยกกัน: `JIANGHU_FRONTEND_V103_FULL.zip` และ `JIANGHU_BACKEND_V103_FULL.zip`. แต่ละ ZIP แตกแล้วได้ไฟล์ที่ root ทันที (`index.html`/`assets/` หรือ `server.py`/`world_v56.json`) ไม่มีโฟลเดอร์ `FRONTEND_CHANGED`/`BACKEND_CHANGED` ซ้อน. เป็นชุด source ตัวเต็มที่ประกอบขึ้นเพื่อส่งต่องาน ไม่ใช่แพตช์เดี่ยว. เนื่องจาก frontend ก้อนเดียวมีขนาดราว 430 MB จึงส่งเป็นไฟล์ `.001`, `.002`, `.003`; ดาวน์โหลดทั้งสามพาร์ตไว้ในโฟลเดอร์เดียวกันแล้วรวมกลับก่อนแตก ZIP.

Windows PowerShell (อยู่ในโฟลเดอร์ที่ดาวน์โหลดไฟล์ทั้งสามแล้ว):

```powershell
cmd /c 'copy /b JIANGHU_FRONTEND_V103_FULL.zip.001+JIANGHU_FRONTEND_V103_FULL.zip.002+JIANGHU_FRONTEND_V103_FULL.zip.003 JIANGHU_FRONTEND_V103_FULL.zip'
```

macOS/Linux: `cat JIANGHU_FRONTEND_V103_FULL.zip.00{1,2,3} > JIANGHU_FRONTEND_V103_FULL.zip`. หลังรวมแล้วจึงแตก ZIP; ถ้าโปรแกรมแตกไฟล์แจ้ง ZIP เสีย ให้เช็กว่าทั้งสามพาร์ตอยู่ครบและเรียงเลขถูก.

ที่มาเพื่อเทียบเวอร์ชัน: frontend V83 FULL + V86 UPDATE_FROM_V83 + แพตช์สะสม V103 (V87–V103); backend V67 FULL + V81 COMBINED_CHANGED (server.py, late_map_nav_v67.py) + world_v56.json จาก V103. V83 ระบุว่า backend เปลี่ยนเฉพาะ world; V86 เปลี่ยนเฉพาะ frontend. ไม่มี server.py ใหม่หลัง V81 ในแพตช์ที่ประกอบ. **ยังไม่ได้เทียบกับ repo/VPS หรือ deployment ที่กำลังรันจริง**; สำรองก่อนนำไปทับ.

## สถานะเวิลด์ล่าสุด

- `world_v56.json` ระบุ `world-maps-v101-beach-trilogy-v2`, `Frontend V101 / Backend World V27`; เลข V103 เป็นรุ่นงานภาพ frontend. `WORLD_V56_GEOMETRY.json` frontend กับ `world_v56.json` backend ตรงกันทุก byte และ `world_v56.js` ฝังข้อมูลแผนที่/จุดวาปเดียวกัน.
- หาดสามแมพเดินต่อกัน: `old_boat_cove_5` ↔ `open_sea_shore_6` ↔ `tidal_beach_7` ↔ `deepwater_harbor_8`. ทุกหาดกว้าง 3000 หน่วย; พื้นเดินชั้นล่างเป็น contour, ไม่มีแพลตฟอร์ม/เชือกใหม่.
- V103 เพิ่มมะพร้าว BG หาด 1 x≈380/1030/2630, หาด 2 x≈690/1780/2630, หาด 3 x≈530/1550. ท่าเรือกับเรือของหาด 3 เป็น BG โปร่งใสวาดช่วงขวาสุดที่ x=2100, y=190 ขนาด 950×330; ผู้เล่นเดินบนหาด ไม่เดินขึ้นท่าเรือ.
- ภาพเกาะไกลของสามหาดแยกกัน, ฟ้า/เมฆ/ทะเล/ทราย/คลื่นเป็นเลเยอร์, มินิแมพสามภาพอัปเดตตามฉาก. ตัวละครและ UI ใช้ source เดิมในชุดเต็ม.
- สุสาน A/B/C/ห้องพระบรมศพ, บันไดผุ, ประตูมังกร, ไฟ และแท่นโลงคงจากชุด V86/แพตช์สะสม V103; อย่าเอาภาพคอนเซปต์ใหม่มาทับเกมโดยไม่เทียบอ้างอิงที่ผู้ใช้เคยเลือก.

## ไฟล์สำคัญ

| ฝั่ง | ไฟล์ | หน้าที่ |
|---|---|---|
| Frontend | `index.html` | เกมหลักและโหลดสคริปต์; cache param V103 |
| Frontend | `late_maps_v67.js` | renderer หาด `beachScenery()` และชั้น terrain |
| Frontend | `world_v56.js`, `WORLD_V56_GEOMETRY.json` | ข้อมูลแผนที่, collision, warp สำหรับ client |
| Frontend | `tomb_v76.js`, `assets/tomb_restore_v82/` | สุสาน/แท่นพระบรมศพที่คงไว้ |
| Frontend | `minimap_v69.js`, `assets/minimap_v70/` | minimap artwork/marker |
| Backend | `server.py` | WebSocket server รุ่น V81 รวม knockback มอน |
| Backend | `world_v56.json` | World V27 ของ V103; ต้องตรง frontend |
| Backend | `late_map_nav_v67.py`, `world_physics_v56.py` | AUTO navigation และการเคลื่อนที่/geometry |

ไฟล์ใน ZIP ตัวเต็มที่ชื่อ README/CHECK/QA รุ่นเก่าคือประวัติจากฐาน V67/V83; **อย่ารัน CHECK_WORLD_V67.py เพื่อรับรอง World V27**. ให้อ่านเอกสารนี้เป็นสถานะล่าสุดของแพ็ก V103.

## ข้อกำหนดภาพที่ห้ามหลุด

- ฉากหาดต่อกันเป็นชายฝั่งเดียว แต่เกาะไกลและตำแหน่งมะพร้าวต้องต่างกัน; ไม่รก. ท้องฟ้าสดใส, เมฆแยกชั้น, คลื่นติดแนวรอยต่อทะเล/หาดแบบโค้งธรรมชาติ.
- ภาพฉากหลังมีเฉพาะสิ่งที่เดินไม่ได้. พื้นเดิน/ชั้นดิน/แพลตฟอร์มต้องประกอบจาก terrain tileset ที่ตรง collision ห้ามฝังทางเดินไว้ใน BG แล้ว trace collision ทับ.
- หาด 3 ท่าเรือทอดเข้าไปในทะเลทางขวาสุดและเรือสำเภาอยู่ปลายท่า; เป็นองค์ประกอบ BG เพื่อบอกว่าอาจเดินทางไปทวีปอื่นในอนาคต. ยังไม่มี NPC บนหาดหรือระบบขึ้นเรือจริงใน V103; ผู้ใช้เคยขอ NPC บนหาด.
- อย่าใช้แคร่ขวาบนของ tileset อ้างอิง, หญ้าสีทองแทนทราย, shell ใน tile ที่ทำให้ซ้ำทุกช่อง, หรือ props ที่ resolution/style ไม่กลืน.

## วิธีติดตั้งและตรวจ

Frontend: แตก ZIP แล้วให้นำ **เนื้อหาทั้งหมด** (เห็น `index.html` ที่ root) ขึ้น frontend hosting ที่ใช้; การส่ง ZIP ไป deploy ต้องตรวจรูปแบบที่ hosting รับ. Backend: ZIP ตัวเต็มเป็น snapshot/source สำหรับตรวจและส่งต่อ; หากอัปผ่าน GitHub ให้เปรียบเทียบกับ repo ปัจจุบันและลงเฉพาะไฟล์ที่เปลี่ยนจริง อย่าทับ `.env`, `.venv`, database, config local หรือ systemd. อัป frontend/backend ให้ feature geometry ตรงกันก่อนทดสอบออนไลน์.

ตรวจระหว่างแพ็ก: ZIP ต้นทาง/ปลายทาง CRC, JS syntax 38 ไฟล์, Python syntax ของ `server.py`, `late_map_nav_v67.py`, `world_physics_v56.py`, script tags ของ `index.html`, equality JSON frontend/backend. ผลเรนเดอร์ V103 ตรวจฉากสามหาดแล้ว. **ยังไม่ได้เล่นใน browser จริงหรือเชื่อม VPS** หลังประกอบชุดตัวเต็มนี้; ต้องตรวจวาปไปกลับ, minimap/cache, สเกลมะพร้าวกับตัวละคร, collider และท่าเรือที่ viewport ต่าง ๆ.

## งานถัดไป

เริ่มจากเปิดแพ็กเต็มทั้งสองและอ่าน `AGENTS.md` กับเอกสารนี้; แคปภาพในเกมสามหาดเพื่อเทียบภาพตรวจฉาก. หากทำ NPC หาด 3 หรือจุดเดินทาง ให้กำหนด gameplay/UX ก่อน, อัป world frontend/backend พร้อมกัน, ตรวจทางเข้าออกและตำแหน่งเกิดทั้งคู่. เมื่อแก้ต่อ ส่งแพตช์เฉพาะไฟล์เปลี่ยนพร้อมระบุฐาน V103 และอย่าเรียกภาพ renderer ว่า screenshot เกมสด.
