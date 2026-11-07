Backend V145 — ใช้ทับ Backend ที่อัป World V144 แล้ว
ต้องใช้ Frontend V145 คู่กัน World V45
Feature: world-maps-v145-natural-ice-cave-contours-v1

อัปทุกไฟล์ใน ZIP ไปยังโฟลเดอร์เดียวกับ server.py แล้ว restart backend
ไฟล์ที่เปลี่ยน: server.py, world_physics_v56.py, late_map_nav_v67.py, world_v56.json
ไฟล์ใหม่: cave_contours_v145.py
Python dependencies เหมือนเดิม ไม่ต้องติดตั้งแพ็กเกจเพิ่ม
รองรับพื้นและเพดาน contour ของถ้ำน้ำแข็งที่เปลี่ยนใหม่ รวมถึง validation และ AUTO
แมพเก่าและประตูทั้งหมดคงเดิม ไม่เพิ่ม NPC/มอนสเตอร์/บอส
