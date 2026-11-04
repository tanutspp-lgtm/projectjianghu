# Project Jianghu — Frontend V111 + Backend V111

ฐาน Frontend/Backend V110. WorldV30 / `world-maps-v111-beach-variety-v1` ต้องใช้คู่กัน.
ผู้ใช้ขอปรับplatformอีกสองหาดให้หลากหลาย และเพิ่มมะพร้าวเพราะภาพโล่ง.
รักษาหาดแรกสามชั้น, ความกว้าง2060, ทางเชื่อมเดิม และการเอาท่าเรือ/เรือออกจากหาดสาม.

หาดสองเป็นทางกระโดดไต่เฉียง มีแพลตฟอร์มยาว350/410/350/350และเกาะสูง580.
หาดสามแบ่งเป็นกลุ่มซ้าย/ขวา มีฐาน500สองฝั่ง ชาน410สองฝั่ง และเกาะเชื่อมกลาง350.
ใช้ภาพทรายทั้งชิ้น V109 เดิม ไม่สร้างถนน/แพลตฟอร์มลง BG และไม่เปลี่ยนแรงกระโดด.
navJumps ใหม่ทั้ง10ทิศต้องคง from/to/launch/land/direction ให้ตรง geometryและbackend.
มะพร้าวผ่าน scenery.palms8/7/7ต้น ใช้2ภาพเดิมสลับขนาด/กลับด้านและยึดพื้นworld.

## Layout

### open_sea_shore_6

Platform(x,x2,y): [(920, 1620, 320), (1030, 1560, 100), (1110, 1460, -120)]

Ropes: [{"x": 1010, "top": 320, "bottom": 627.2964084798042, "type": "rope"}, {"x": 1420, "top": 100, "bottom": 320, "type": "rope"}, {"x": 1200, "top": -120, "bottom": 100, "type": "rope"}]

Jumps: []

Palms: [[280, 570, false, false], [430, 180, true, true], [650, 430, true, false], [780, 230, false, true], [1100, 230, true, false], [1510, 280, true, true], [1650, 190, false, true], [1830, 390, true, true]]

### tidal_beach_7

Platform(x,x2,y): [(300, 650, 330), (690, 1100, 260), (1140, 1490, 190), (1530, 1880, 120), (1030, 1610, -100)]

Ropes: [{"x": 460, "top": 330, "bottom": 584.853892118366, "type": "rope"}, {"x": 1320, "top": -100, "bottom": 190, "type": "rope"}]

Jumps: [{"from": 1, "to": 2, "launch": 628, "land": 722, "direction": 1}, {"from": 2, "to": 1, "launch": 712, "land": 618, "direction": -1}, {"from": 2, "to": 3, "launch": 1078, "land": 1172, "direction": 1}, {"from": 3, "to": 2, "launch": 1162, "land": 1068, "direction": -1}, {"from": 3, "to": 4, "launch": 1468, "land": 1562, "direction": 1}, {"from": 4, "to": 3, "launch": 1552, "land": 1458, "direction": -1}]

Palms: [[240, 300, false, false], [480, 240, true, false], [720, 260, true, true], [970, 350, false, true], [1280, 500, false, false], [1570, 300, true, false], [1820, 320, true, true]]

### deepwater_harbor_8

Platform(x,x2,y): [(230, 730, 320), (1320, 1820, 315), (450, 860, 100), (1290, 1700, 95), (900, 1250, 25)]

Ropes: [{"x": 350, "top": 320, "bottom": 580.0, "type": "rope"}, {"x": 1760, "top": 315, "bottom": 604.5543946475194, "type": "rope"}, {"x": 620, "top": 100, "bottom": 320, "type": "rope"}, {"x": 1490, "top": 95, "bottom": 315, "type": "rope"}]

Jumps: [{"from": 3, "to": 5, "launch": 838, "land": 932, "direction": 1}, {"from": 5, "to": 3, "launch": 922, "land": 828, "direction": -1}, {"from": 5, "to": 4, "launch": 1228, "land": 1322, "direction": 1}, {"from": 4, "to": 5, "launch": 1312, "land": 1218, "direction": -1}]

Palms: [[230, 270, true, false], [480, 280, false, false], [740, 260, true, true], [1030, 500, false, false], [1390, 290, true, false], [1640, 290, true, true], [1840, 240, false, true]]

## ข้อกำหนด

คงคลื่นV106/เกาะฉากหลังV107/สุสาน/ระบบต่อสู้เดิม. ห้ามใช้แคร่/ไม้ไผ่. Featureใหม่ต้องตรงกันทั้งfront/back. server.py/nav/physicsเดิมจากV110 เปลี่ยนworld_v56.jsonเท่านั้น. ดู QA_V111_TH.txt และqa/v111สำหรับขอบเขตตรวจในเครื่อง ไม่ใช่VPSจริง. เอกสารV110และเก่ากว่าเป็นประวัติ.
