JIANGHU BACKEND V215 FULL

เป็นBackendเต็มที่ประกอบจาก V181 FULL + cumulative V184 + V187.6 + V213 + V215
รวมserver.py, combat/world/navigation/progression modulesและJSONที่ต้องใช้ครบ
ไม่ใช่เปลี่ยนชื่อแพตช์changed-onlyให้เป็นfull

เพิ่ม:
- Owned starter/equip/unequipตามUIDจริง ชุดNPC row1 Lv5 แยกอาวุธ4อาชีพ +เกราะ5ชิ้น
- Capacityกระเป๋ารวม100 ไม่มีเชื่อstats/itemที่clientส่งมา
- ปราณช่อง10/25/40แทน20/40/60 โหมดผู้เล่นตรวจเลเวลจริง ใช้3IDเดิม
- Guest Social: party6/guild24/friends50 รับคำเชิญก่อนเข้ากลุ่มและกระซิบส่วนตัว
- private equipment snapshotsเป็นimmutable cacheตามrevision ป้องกันdeltaไม่ส่งหลังถอดของ
- World52, geometry, 30Hzself/10Hzothers, V187.6 combatและV213lockfallbackคงเดิม

ติดตั้งจาก ZIP เต็มบนVPS (แยกจากFrontend):
1. สำรองไฟล์และenvironment/serviceเดิมตามปกติ แตกZIPทับรากโปรเจกต์ /opt/jianghu
   ภายในZIPมีserver.pyที่root ไม่ต้องย้ายออกจากโฟลเดอร์ซ้อน
2. ใช้venvเดิม:
   cd /opt/jianghu
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python CHECK_V215.py
   systemctl restart jianghu
   curl -fsS http://127.0.0.1:8765/healthz
   ผลต้องมี JIANGHU_BACKEND_V215, hud-owned-equipment-v215-v1, hud-social-v215-v1

ถ้าเก็บโค้ดในGitHub: อัปโหลดไฟล์ชุดนี้ลงrepoและcommit/pushก่อน แล้วที่VPS:
   cd /opt/jianghu
   git pull --ff-only
   .venv/bin/python CHECK_V215.py
   systemctl restart jianghu
   curl -fsS http://127.0.0.1:8765/healthz
อย่ารันgit pullแล้วคิดว่าZIPถูกpushให้แล้ว ชุดนี้ไม่ได้deploy/pushให้

ของ/เพื่อน/ปาร์ตี้/กิลด์ยังเป็นGuestในหน่วยความจำ ไม่ใช่บัญชีถาวรหรือDBcharacter
ไม่ได้เปลี่ยนSupabase schema/RLS/ข้อมูลดาเมจ ไม่เปิดGuest sandboxโดยอัตโนมัติ
ไม่มีอัปบาลานซ์ใหม่ ไม่มีcostumeitemใหม่ และไม่เปลี่ยนเสื้อผ้าในspriteatlas
Starter Lv5เฉพาะที่serverแจกครั้งแรกสวมได้ตั้งแต่Lv1 ไม่เพิ่มEXP/เลเวลฟรี
ดู HANDOFF_UI_V215_TH.md และ QA_V215_TH.txt สำหรับกฎและผลตรวจ
