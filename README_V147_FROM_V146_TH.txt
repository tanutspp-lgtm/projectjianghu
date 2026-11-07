Backend V147 — DELTA จาก V146 เท่านั้น
มีไฟล์ production ที่เปลี่ยน2ไฟล์: world_v56.json และ cave_contours_v145.py
แตกทับราก backend V146 แล้ว restart service ตามวิธีเดิม
ไม่ต้องเปลี่ยน server.py; ใช้ server.py จากชุด V145/V146 ที่มี contour physics อยู่แล้ว
ต้องใช้คู่ Frontend V147 / World V47
Feature world-maps-v147-coherent-cliff-rock-ends-v1

เพิ่ม collision รูปทรงปลายมวลหินใน3ถ้ำให้ตรง alpha terrain ใหม่ และตรวจแนวผนังด้านข้างตามรูปร่างแทนสี่เหลี่ยมเดิม
สโคปเฉพาะ rockEndsV147; คง walking profiles ตำแหน่งแท่น small ledges31ชิ้น เชือกบันได และลิงก์วาร์ปทั้งหมด
แมพเดิมนอกโซนถ้ำไม่เปลี่ยนฟิสิกส์หรือข้อมูล
ทดสอบ local เท่านั้น ไม่ได้ deploy VPS
