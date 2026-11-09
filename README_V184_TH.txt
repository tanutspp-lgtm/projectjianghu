Project Jianghu — Frontend184 / Backend184 — base V183

รายการแก้รอบนี้
1. ธารเยือกแข็งและเขตหิมะ: เอาการสร้างพื้น/รูปประกอบซ้ำระหว่างเล่นออกจากเส้นทางเรนเดอร์ทั้ง12แมพ
   พื้น/บันได/เชือกแบบคงที่เตรียมเป็นภาพ lossless จากตัวเรนเดอร์เดิม ไม่ย้ายตำแหน่งและไม่วาดฉากใหม่
   โหลดและ decode เฉพาะแมพปัจจุบัน ปล่อยภาพแมพก่อนหน้า ไม่ preload เขตหิมะทั้งหมดพร้อมกัน
   terrain/water tiles ไม่เกิน1024x1024ต่อภาพ และไม่เกิน48MiB RGBAรวมต่อแมพ
   คงคลื่นน้ำ เรือโยก น้ำแข็งลอย อากาศ หิมะ และกลไกน้ำแข็งตกทำดาเมจเดิม
   เผยฉากเมื่อรูปพร้อม decode และเรนเดอร์ฉากปลายทางสำเร็จแล้วเท่านั้น
2. Android/Chrome ท่าเรือเหมันต์: เปลี่ยนทางวาดพื้น ท่าเรือ น้ำ เกาะไกล น้ำแข็งเปียก และ surf
   จากรูปผ่าน offscreen Canvas เป็นรูป Image ที่เตรียมไว้โดยตรง ไม่สร้าง/อ่าน pixel ระหว่างเล่น
   แก้เส้นทางเดียวกันในภาพประกอบแมพหิมะอื่นและ surf ฝั่งทะเลแผ่นดินใหญ่
   ภาพที่ผู้ใช้ส่งแสดงเฉพาะแหล่ง Image ตรงแต่ส่วน Canvas-derived หาย จึงเป็นเหตุให้ตรวจเส้นทางนี้
   เป็นข้อสันนิษฐานจากอาการและการจำลอง failure path ไม่ใช่ผลวินิจฉัย GPU เครื่อง Android จริง
   ถ้าวาดผิดพลาด cover แสดง error/reload โดยไม่ปล่อยเกมหยุดแบบเงียบๆ
3. วาปวนตอนเลือกแมพ: บาง spawn ของตัวเลือกแมพอยู่ใน trigger ทางออกพอดี
   ป้องกันวาปอัตโนมัติจนเดินพ้น trigger แรก และไม่ส่งต่อแมพขณะกำลังโหลดฉาก
   ไม่แก้พิกัดภูมิประเทศ วาป จุดเกิด หรือกติกากดขึ้นเข้าถ้ำ
4. ทุกอาชีพตีข้ามชั้น: เดิมใช้ abs(monsterFeet-shotY-78)<95 โดยไม่มีพื้นคั่นในการตรวจชน
   เพิ่มการตรวจความสูงจริงของตัวมอนสเตอร์และแนวโจมตี/กระสุนที่มีพื้น ผนัง หรือเนื้อถ้ำคั่น
   ล็อกตำแหน่งปล่อยและระดับเท้าตอนออกอาวุธ ตรวจพื้นระหว่างผู้โจมตีกับเหยื่อ
   ใช้กฎเดียวกันใน JS ออฟไลน์และ Python authoritative ออนไลน์ ไม่รับกล่องดาเมจจากclient
   ใช้กับตีธรรมดา สกิลล้ม ทลายการ์ด และการเลือกฟัน/ปาของสกุลถังทุกเพศ
   ปราณคลื่นสะท้อนไม่ลัดผ่านพื้นไปตัวอีกชั้น คงการสะท้อนหาเป้าชั้นเดียวกัน
   คงการโจมตีบนทางลาดและเป้ากระโดดที่อยู่ในระยะและไม่มีพื้นคั่น

คงแพทช์ V183 ทั้งหมด: Aim Assist defaultOFF ในSettings, สกุลถังฟัน1/2หรือปาตามระยะ,
หมอฮีลCD3s/พัก.60s, ผลักมอนตามทิศฟัน, ไม่มีเอฟเฟกต์อาวุธซ้ำที่หัวมอน
คงขนาด/ภาพตัวละคร worldCell134.68, อนิเมชั่น/เสียง, V180 HUD/mobile/chat,
World52 geometry/physics/cave-contours, ดาเมจน้ำแข็งตก และ network binary/cadence เดิม

ติดตั้ง Frontend
วาง3PART ZIPกับMERGE_V184.ps1ในDownloads แล้วรัน PowerShell:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\MERGE_V184.ps1"
จะตรวจ SHA256 แตกลงโฟลเดอร์ใหม่ และสร้าง JIANGHU_FRONTEND_V184_FULL.zip พร้อมอัป
ทั้ง3PARTเป็น ZIPอิสระ ไม่ใช่ไฟล์แบ่งไบต์ อย่าต่อไบต์ไฟล์

Backend จำเป็นต้องอัปด้วย เพราะมีการแก้ authoritative combat:
JIANGHU_BACKEND_V184_FROM_V181_CHANGED_ONLY.zip มีเฉพาะไฟล์เพิ่ม/เปลี่ยนเทียบ Backend V181 FULL
รวมการเปลี่ยนฝั่ง Backend ของ V182+V183+V184 ครบ ไม่ต้องลงแพทช์กลาง
แตกทับ Backend V181 เดิม เก็บ .env/.venv/ข้อมูลผู้เล่น/service เดิม ไม่มีไฟล์ที่ต้องลบ
อ่าน START_HERE_V184_FROM_V181.txt สำหรับขั้นตอนของแพทช์สะสมนี้
อัปไฟล์เข้าrepoเดิมที่VPSใช้งาน แล้วที่โฟลเดอร์repoบนVPS:
git pull --ff-only
bash RESTART_AND_VERIFY_V184.sh
ตัวช่วยตรวจ syntax/dependencies แล้วหา service เดิมจาก WorkingDirectory+server.py
จะไม่ restart หากพบไม่ตรงเพียง1service และไม่สร้างservice/configใหม่
/healthz ต้องรายงาน JIANGHU_BACKEND_V184 และ combat-layers-v184-v1
Frontend184จะปฏิเสธbackendเก่าซึ่งยังตีข้ามชั้นได้
ยังไม่ได้ push/deploy หรือ restart VPSจริงจากการทำแพทช์นี้

ผลตรวจ
- เรนเดอร์ nativeทั้ง12snow/cave maps: cold/กลับเข้า ไม่มี offscreen Canvas allocation/readback ในเส้นทางใหม่
- terrain/raster loader:9แมพครบไฟล์ ขนาดภาพ/48MiB, delayed decode, cancel/stale callback, failure/reveal/release ผ่าน
- PNG→losslessWebP ของภาพเตรียมไว้ RGBAตรงต้นฉบับ; การวางภาพรวมอาจต่างเล็กน้อยที่ขอบจากresampling
- selector spawn guard8จุด/incoming snow portals22จุดผ่าน
- browserจริงเข้าและสลับธารเยือกแข็ง/ท่าเรือได้ เห็นพื้น น้ำ น้ำแข็ง และสิ่งประกอบครบ
- offline real-controller308กรณี และ authoritative616กรณีข้ามชั้น:ไม่ทำดาเมจ/ล้ม/ทลายการ์ด
- บนชั้นเดียวกันทุกอาชีพยังตีโดน, ทางลาดจริง1379แนวไม่มีการปฏิเสธผิด, เป้ากระโดดที่ไม่มีพื้นคั่นผ่าน
- collision JS/Python6000seeded casesตรงกัน; backend17testsผ่าน
- local WebSocketจริง8avatars:admission/settings/facing/Tang ranged/healer recoveryผ่าน
- PvE-only/cast metadata6tests และปราณ3กรณีผ่าน
ไม่มีเครื่องAndroidที่ผู้ใช้พบปัญหาให้ยืนยันผลจริง ไม่มีphysical iOS/FPS benchmark
โมเดลที่จำลอง Canvas-source ไม่ใช่การทดสอบเครื่องนั้น ขอทดสอบซ้ำหลังอัปแพทช์
