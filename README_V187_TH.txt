Backend187 — สกิล6ท่าจริงของ4อาชีพ
ใช้คู่ Frontend187 เท่านั้น ตัวแพตช์เป็น deltaสะสมจากBackend181
คัดลอกทุกไฟล์ทับrootของbackend181เดิม ไม่ลบ .env/.venv หรือไฟล์ตั้งค่าของตน
จากนั้นรัน: bash RESTART_AND_VERIFY_V187.sh
สคริปต์จะตรวจไฟล์และหาserviceที่WorkingDirectoryตรงกับโฟลเดอร์นี้และรันserver.py
ถ้าพบไม่ตรง1serviceจะหยุดโดยไม่แก้serviceใด ให้ระบุและrestartserviceเดิมด้วยตนเอง
ตรวจ /healthz ต้องขึ้น JIANGHU_BACKEND_V187 martial-combat-v187-v1
ไม่มีmigrationSQL ไม่มีการแก้บัญชี/ตี้ถาวร/Supabaseในแพตช์นี้
เกมออนไลน์ยังcooperativePvE สนามPvPกับบอทอยู่แยกในFrontend ไม่เปิดตีผู้เล่นด้วยกันบนpublicworld
player.party_idถ้ามีระบบตี้จริงเชื่อมไว้แล้วจะใช้เป็นเงื่อนไขฮีล มิฉะนั้นGuestฮีลตนเองเท่านั้น
ฮีลรวมจากหมอทุกคนต่อผู้รับ40%MaxHP/rolling60วิ เปลี่ยนแมพ/ตี้ไม่ล้างledger
คำสั่งclientส่งเพียงบทบาทสกิล/การ์ด/ล็อก/ขนาดviewport ไม่มีสิทธิ์ส่งดาเมจหรือผลฮีล
คงโปรโตคอลbinaryและรอบ30Hz/10Hz ส่วนเสริมmartialใช้metadataและeventcursorหลังส่งสำเร็จ
ค่าบาลานซ์เป็นรอบทดสอบเริ่มต้น ไม่อ้างว่าเล่นบนVPS/iOS/Androidจริงแล้ว
