# Project Jianghu v8.0CL — Passive Diagnostic Telemetry (Render)

## Purpose
ผู้ใช้เล่น Guest Online ตามปกติ รวมถึง Bot Stress 10/20/30 แล้วกดล้าง จากนั้นบอก ChatGPT ว่า `ตรวจ Performance ช่วงเมื่อกี้` ระบบจะสร้าง Render Logs อัตโนมัติทุก ~15 วินาทีขณะ Server ทำงาน ไม่ต้องถ่ายภาพ Performance Overlay.

## Render log
ค้นหา `JIANGHU_DIAG` ใน Render application logs. ทุกบรรทัด JSON มี uptime-group boot token (ไม่ผูกตัวตน), ts Unix UTC, จำนวน Guest, จำนวน AUTO, CPU% ของ Python process หนึ่งคอร์, tick P95/max, loop lag P95/max, encode P95/max, snapshot send/overwrite, websocket send duration P95/max, RX/TX. Browser ต้นทางเกมเท่านั้นส่ง FPS/Ping/Snapshot gap P95/max และ frameMs ทุก 15s (no names/account/IP/position/actions). ตัวเลข Browser เป็น client-reported ใช้วิเคราะห์ ไม่ใช้ตัดสินต่อสู้.

## Integration
Render Connector มี CPU/RAM Metrics เป็นค่าภาพรวมรายนาที; ใช้คู่กับ JIANGHU_DIAG text filter ใน logs เพื่อแยก Server vs Client. Supabase connected project `uxxkyptoocbswedwizct` ณ ปัจจุบันใช้ตารางบาลานซ์เท่านั้น **ยังไม่มีการบันทึก Performance ลง Supabase** และห้ามใส่ service_role secret ใน JS. ถ้าต้องการเก็บประวัติเป็นเดือน ค่อยต่อ ingestion แบบ service-side + RLS แยกตาราง.

## Safety
ไม่มี raw names, session tokens, IP, coordinates, inventory หรือ input logs. ไม่ส่งภาพ/เสียง. ส่ง telemetry 1 WebSocket tiny message/15s เฉพาะผู้เล่นตัวจริง ไม่ใช่ 30 Bot Stress sockets. ไม่มี SQL call ในเกม loop. หาก Backend ยังเก่า Client จะไม่ส่ง client_perf (feature negotiation), จึงต้องอัป Backend และ Netlify ทั้งสองฝั่ง.

## Deploy
Backend GitHub -> Render auto-deploy; หลัง live healthz ต้องระบุ v8.0CL. Frontend ZIP to Netlify. /?botstress=1&perf=1 ใช้ทดสอบตามเดิม แต่ไม่จำเป็นต้องเปิด perf=1 สำหรับการเก็บข้อมูล. ยังไม่มีการ deploy อัตโนมัติโดยการสร้างไฟล์นี้.

## Do not conflate
Snap gap = time between arrivals, not direct input delay; browserSnapGapP95Ms is per-browser 24-latest intervals' P95, server-side field browserSnapGapP95Ms is P95 across reporting browsers. Server CPU in Render metrics cgroup usage != server cpuCorePct (Python process). `wsSendP95Ms` measures await enqueue, not transport RTT. Perf overhead must be retested on real Render.
