# เปิดบัญชี Seven Wind บนโปรเจกต์ project jianghu

ตาราง sw_terms_acceptances, sw_characters และนโยบาย RLS จาก character_roster.sql ติดตั้งแล้วในโปรเจกต์ uxxkyptoocbswedwizct ไม่ต้องรัน SQL ซ้ำ สถานะตอนส่งงาน: anonymous_users และ google ยังปิดอยู่

1. ใน Supabase Dashboard → Authentication → Sign In / Providers เปิด Anonymous Sign-Ins สำหรับ Guest
2. สร้าง OAuth client ประเภท Web application ใน Google Cloud ของเกม โดยลง Authorized redirect URI เป็น https://uxxkyptoocbswedwizct.supabase.co/auth/v1/callback เลือก scopes openid, email และ profile หากแอป Google ยังอยู่ในโหมด Testing ให้เพิ่มอีเมลผู้ทดสอบ
3. เปิด Google provider ใน Supabase แล้วใส่ Client ID และ Client Secret ใน Dashboard โดยตรง เก็บ Secret ไว้กับผู้ให้บริการเท่านั้น หน้าเกมใช้เพียง publishable key
4. ใน Supabase Authentication → URL Configuration เพิ่ม redirect URL แบบตรงโดเมนและเส้นทางสำหรับหน้าตัวละครของเกม และ https://seven-wind-showcase-atlas.fnadvisory.chatgpt.site/roster.html สำหรับโชว์เคส เช่น https://โดเมนเกม/roster.html ปรับ Site URL ให้ตรงโดเมนเกมจริง
5. แตก frontend ทั้งสาม ZIP ลงในโฟลเดอร์เดียวกัน นำขึ้นเว็บไซต์เกม HTTPS ที่ root มี index.html, roster.html และ character.html ติดตั้งและรีสตาร์ต backend ตาม HANDOFF_GAME_ENTRY_TH.md ใน ZIP backend โชว์เคสแยกมีเฉพาะหน้าบัญชีและฉากเลือกตัว
6. ทดสอบ Guest และ Google คนละบัญชี เลื่อนข้อตกลง สร้างตัวละคร แล้วกลับมาล็อกอินอีกครั้งด้วยวิธีเดิม Google ใช้บัญชีเดิมข้ามอุปกรณ์ได้ Guest ต้องใช้เบราว์เซอร์และ origin เดิม เมื่อเปิดเกมจริงตรวจชื่อและรูปลักษณ์ในโลก แม้ลงชื่อด้วย Google เหมือนกัน การเลือกหน้าเว็บจากคนละ origin ต้องลงชื่อใหม่
7. ก่อนเปิดสาธารณะ เติมชื่อผู้ให้บริการ ช่องทางรับคำขอเกี่ยวกับข้อมูลและอุทธรณ์ ระยะเวลาเก็บข้อมูลจริง และทบทวนร่างเงื่อนไขกับผู้รับผิดชอบกฎหมาย ข้อมูลบัญชีอยู่ใน Supabase Auth ตัวละครและการยอมรับใช้รหัสบัญชีเป็นตัวเชื่อม เกมไม่ขอสิทธิ์ Gmail, Contacts หรือ Drive ไม่คัดลอกอีเมล รูป หรือ token ของ Google ลงตารางเกม

เบราว์เซอร์เก็บ refresh credential ของ Supabase สำหรับ Guest ไว้ใน origin ของเกม และเก็บของ Google เฉพาะเซสชันของแท็บ ห้ามใส่สคริปต์ที่ไม่น่าเชื่อถือใน origin นี้ รหัสผ่าน Google, client secret และ service_role ไม่ใช่ข้อมูลตั้งค่าฝั่งผู้เล่น โหมดทดลองบนเครื่องใช้คีย์คนละชุด และไม่นำตัวละครทดลองเข้าบัญชีจริง
