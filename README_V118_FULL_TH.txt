Project Jianghu — Frontend V118 FULL + Backend V118 FULL
ฐาน Frontend V117 + Backend V114; World V33
feature: world-maps-v118-dry-bandit-camp-v1

เพิ่มค่ายโจรสามแมพ รวมโลก44แมพ:
ด่านหินเก่า ↔ ค่ายโจร · หน้ากำแพงไม้ ↔ ค่ายโจร · ลานชั้นใน ↔ ค่ายโจร · เรือนหัวหน้าค่าย
bandit_palisade_1 / bandit_camp_2 / bandit_chief_3, กว้าง2400ทุกแมพ
ประตูเข้าชั้นในอยู่ในช่องประตูใหญ่ กดขึ้น; ทางอื่นเดินผ่านจุดวาร์ปตามปกติ

ตามคำสั่ง: ค่ายโจรบ้านๆ รั้วท่อนไม้แหลม ป้อมไม้หยาบ เชือกผูก หลังคามุงฟาง
หน้ากำแพงค่ายเป็นแมพแรกก่อนเข้า ส่วนค่ายชั้นในและเรือนหัวหน้ามีทางยกระดับต่างกัน
พื้นดินแห้งแดงน้ำตาล หญ้าฟาง/เขียวหม่นบางๆ ต้นไม้ใบน้อย ไม่ใช่ทะเลทราย
อาคารเจนดัดแปลงจากreferenceอาคารเมืองหลวงเดิม; ต้นไม้/terrainแก้จากassetเดิม
ภาพทั้งหมดและpromptอยู่ assets/bandit_v118; แยกcropจริงพร้อมmanifest
ฉากหลัง2ชั้น: ภาพท้องฟ้า/เนินไกล และต้นไม้ไกลโปร่งบาง; พร็อพค่ายยึดพิกัดโลก
พื้น/slope/แพลตฟอร์ม/เชือกวาดจากtilesetแยกตรงcollision ไม่ได้อบพื้นเดินไว้ในBG

ใช้Frontend118คู่Backend118เพราะเพิ่มgeometry/warpใหม่
world_v56.js / WORLD_V56_GEOMETRY.json / backend world_v56.jsonตรงกัน
server.pyและไฟล์Pythonทั้งหมดเหมือนBackend114ทุกbyte; Backend118เปลี่ยนworld JSONและเอกสาร
แมพเดิมทุกแมพและจุดเชื่อมเดิมตรงV117ทุกbyte; ทะเลV117 สุสานและระบบต่อสู้เดิมคงไว้
ยังไม่มีตัวโจร/หัวหน้าบอส/เควสต์ใหม่ รอบนี้ทำฉาก geometry และทางเชื่อมเล่นได้
ไม่ได้เพิ่มสำนักหรือทางออกไปสำนัก

QA:
- Backendเดินพื้นไปกลับ3แมพ ปีนเชือก8เส้นทั้งขึ้น/ลง และAUTOเดินถึงทุกแพลตฟอร์ม22เป้าหมาย
- WebSocketจริงเข้าทั้ง3แมพ และวาร์ป6ทิศทางผ่านรวมด่านหินเก่า
- Browserจริงตรวจเดินพื้น/เชือก/กราฟ3แมพและวาร์ป6ทิศทางผ่าน
- แก้ชื่ออ้างอิงcountในtest harnessหลังจบtraversal แล้วรันcapture/ภาพ/minimapแยก
  ดูbrowser_traversal.log และ browser_capture.log; ไม่มีการเปลี่ยนphysicsหลังtraversal
- ตรวจภาพจริง3ขนาดจอ รวมภาพoverviewจากproduction renderer
- มินิแมพใหม่3ภาพตรงbounds และdecode44ภาพผ่าน ไม่มีpageerror
- ZIP CRC และfrontend/backend world parity ผ่าน
ยังไม่ได้deployหรือทดสอบVPSจริง

แตกFrontendตัวเต็มแล้วได้index.html/assetsที่root ไม่ต้องลงแพตช์เพิ่ม
แตกBackendตัวเต็มแล้วได้server.py/world_v56.jsonที่root
