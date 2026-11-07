JIANGHU FRONTEND V130 / BACKEND V130 / World V41
ฐาน Frontend V128 + V129 coastal fixes / Backend Python V124 unchanged from V127.
Feature: world-maps-v130-burial-floor-fix-v1

ลบพื้นชนล่องหนกลาง imperial_tomb_burial เฉพาะ x720–1680 y470 และ navJumps ที่อ้างถึง
พื้นหลัก y550 ชานซ้าย/ขวา y135 บันได ฉาก แท่นโลง และวาร์ปคงเดิม
รวมการแก้ V129: เรือสัมผัสน้ำ เสาค้ำท่าเรือเต็มชิ้น ทะเลไกลไม่ยืดตามกล้องในสามหาดและหมู่บ้าน
ต้องอัป frontend/backend คู่กันเพราะ collider เปลี่ยน
ถ้ามี Backend V127 อยู่แล้ว เปลี่ยนเฉพาะ world_v56.json จาก BACKEND_CHANGED; server.py ไม่เปลี่ยน
FULL แตกที่ root; index.html/assets หรือ server.py/world_v56.json

บันไดโถงบรรพกษัตริย์และห้องพระบรมศพใช้ assets/tomb_v80/ladder.png แบบเดียวกับใต้ดิน1–2 กว้าง48และ anchorเดียวกัน โดยไม่เปลี่ยน geometry ระยะปีนหรือจุดขึ้นลง
