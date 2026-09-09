# Tech Stack

## Decision Summary
ทีม: เก่งมากครับ
Domain: Pairwise
Date: 09-Sep-2026

## Frontend
- Framework: React
- Language: TypeScript
- Styling: Tailwind CSS
- Rationale: Component-based ทำให้แยกส่วน UI ไปใช้ซ้ำได้ และแตกงานให้หลายคนทำพร้อมกันได้ง่าย, จับ error ตั้งแต่ตอนเขียน ไม่ต้องรอ runtime, เขียน style ในไฟล์เดียวกับ markup ไม่ต้องสลับไฟล์ ไม่ต้องคิดชื่อ class, ไม่มีปัญหา CSS ชนกันหรือ specificity war เพราะไม่มี global selector

## Backend
- Framework: FastAPI
- Language: Python
- Rationale: เร็วในการเขียน — เขียน endpoint หนึ่งตัวได้ในไม่กี่บรรทัด ไม่ต้องตั้งค่าอะไรเยอะ เหมาะกับโปรเจกต์ที่ต้องเห็นผลไว, 
Type hints ใช้งานจริง — FastAPI เอา type hint ของ Python ไป validate request/response ให้อัตโนมัติผ่าน Pydantic ส่งข้อมูลผิด format มาจะโดนปฏิเสธพร้อมบอกว่าผิดตรงไหน โดยที่เราไม่ต้องเขียนโค้ดเช็คเอง, เอกสาร API เกิดขึ้นเอง — มี Swagger UI กับ ReDoc ให้ที่ /docs โดยไม่ต้องทำอะไรเพิ่ม ทีม frontend เปิดดูแล้วยิง request ทดสอบได้เลย ตรงนี้ประหยัดเวลาสื่อสารเยอะมาก, Async ในตัว — รองรับ async/await แต่แรก งานที่รอ I/O เยอะ (เรียก API อื่น, อ่านไฟล์, รอ DB) ทำ concurrent ได้โดยไม่ต้องเพิ่ม library, Python ecosystem — ถ้าโปรเจกต์แตะ ML, computer vision, การประมวลผลข้อมูล หรือคุยกับ ROS2 การอยู่ในโลก Python ทำให้เอา OpenCV / PyTorch / numpy มาต่อได้ตรง ๆ ไม่ต้องแยก service

## Database
- SQLite
- Rationale: ไม่ต้องติดตั้ง server — เป็นไฟล์เดียวจบ ไม่มี process แยก ไม่ต้องตั้ง user/password/port ทุกคนในทีม clone repo มาแล้วรันได้ทันที, Deploy ง่าย — ก๊อปไฟล์ .db ก็คือ backup แล้ว ย้ายเครื่องก็แค่ย้ายไฟล์, เร็วสำหรับงานอ่านเยอะ — ไม่มี network overhead เพราะอ่านจาก disk ตรง ๆ ในบางเคสเร็วกว่า DB ที่ต้องต่อผ่าน socket ด้วยซ้ำ
รองรับ SQL มาตรฐาน — ใช้ SQLAlchemy หรือ SQLModel เขียน ถ้าวันหนึ่งต้องย้ายไป PostgreSQL ก็เปลี่ยน connection string เป็นหลัก ไม่ต้องรื้อโค้ดใหม่หมด, นับเป็น production-grade — ถูกใช้ในมือถือ เบราว์เซอร์ และอุปกรณ์ embedded ทั่วโลก 

## Deployment
- Platform: Vercel
- Staging URL: [จะเพิ่มหลัง deploy]
- Commit-to-live time: 

## AI Tools
- Agent ที่ใช้: GitHub Copilo, Claude, GPT Codex
- Review policy: ทุก AI-generated code ต้องอ่านและอธิบายได้ก่อน commit