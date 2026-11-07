Backend V156 จากฐาน Backend V155
แตกทับ backend เดิมแล้ว restart
เปลี่ยน server.py และเพิ่ม cave_ice_v156.py + cave_ice_v156.json เท่านั้น
WorldV50, world_v56.json, Python physics/nav เดิม
น้ำแข็งถ้ำทั้ง3แมพ: serverตรวจปะทะแบบsweepที่30Hz ดาเมจ15%MaxHP ไม่คิดDEF/ตั้งการ์ด/โล่ปราณ ล้ม1.2วิ หลังลุกกันน้ำแข็งซ้ำอย่างน้อย1.5วิ
จุดเดิมวน10.4–12.89วิ; ต่อการร่วงหนึ่งครั้งโดนคนเดิมได้ครั้งเดียว, ทุกคนเห็นจังหวะเดียวกันผ่านcaveIceTime
ไม่เพิ่มมอนสเตอร์ ไม่เปลี่ยนgeometry/warp/combatส่วนอื่น
ใช้คู่ Frontend V156
