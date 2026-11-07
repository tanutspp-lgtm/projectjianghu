Backend V146 — ใช้ทับ Backend V145
มีเฉพาะ2ไฟล์ที่เปลี่ยน: world_v56.json และ cave_contours_v145.py
ชื่อ Python module เดิมคงไว้เพื่อให้ server.py V145 import ได้ตามเดิม
ไม่ต้องเปลี่ยน server.py และไม่เพิ่ม dependencies
คัดลอกทั้ง2ไฟล์ไปโฟลเดอร์เดียวกับ server.py แล้ว restart backend
ต้องใช้ Frontend V146 คู่กัน World V46 / world-maps-v146-snow-cave-jump-ledges-v1
เพิ่มแท่นเล็กและทางกระโดดถ้ำพร้อม AUTO รองรับ one-way small ledges
ลิงก์วาร์ปเดิมทุกจุดคงเดิม รวมปิดวาร์ปเรือรอNPC
