Backend V155 จาก Backend V149 (ใช้คู่ Frontend V155)
มีการเปลี่ยนแค่ world_v56.json เพื่อขยายช่วงแพลตฟอร์ม10แผ่นใน4แมพน้ำแข็ง
วางทับ world_v56.json ของ backend V149 แล้ว restart service เพื่อโหลดข้อมูลใหม่
server.py และ Python อื่นใช้ V149 เดิม
World50 / feature world-maps-v155-long-snow-rock-platforms-v1
ห้ามใช้ Frontend V155 กับ world_v56.json รุ่นเก่า เพราะ collision จะไม่ตรง
