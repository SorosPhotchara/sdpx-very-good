# PairEval Backend

FastAPI service สำหรับห้องเรียน การประเมินแบบเปรียบเทียบคู่ คะแนน และรายงาน ข้อกำหนด domain อยู่ใน [DOMAIN.md](DOMAIN.md) และ API อยู่ใน [API.md](API.md)

## Local setup

จาก root ของโปรเจกต์ รัน `docker compose up -d postgres` เพื่อเปิด PostgreSQL ที่ `127.0.0.1:5433` จากนั้นใน `backend/`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend โหลด `backend/.env` ผ่าน `python-dotenv` อัตโนมัติ ไฟล์นี้ถูก ignore โดย Git; ตัวอย่างค่าที่ต้องมีอยู่ใน `.env.example` `DATABASE_URL` ต้องชี้ไป PostgreSQL และไม่มีค่าเริ่มต้นอัตโนมัติ `seed_demo.py` รักษาห้องต้นแบบ 4 ห้อง เพิ่มอาจารย์คนแรกใน allowlist ให้ห้องต้นแบบที่มีอยู่ และเพิ่มห้องเดโมที่มี 3 กลุ่มและ 9 นักศึกษาแบบเรียกซ้ำได้
กำหนด `INSTRUCTOR_EMAILS` ก่อนรัน migration กับฐานที่มีห้องต้นแบบเดิม เพื่อให้ migration เพิ่มอาจารย์คนแรกใน allowlist เป็นเจ้าของห้องโดยคงอาจารย์เดิมไว้

## Authentication

โหมดปกติใช้ Google Sign-In: frontend ส่ง Google ID token ให้ API และ backend ตรวจ audience ด้วย `GOOGLE_CLIENT_ID` รวมทั้งตรวจว่าอีเมลได้รับการยืนยันจาก Google ผู้ดูแลระบบกำหนดผ่าน `ADMIN_EMAILS`; สิทธิ์อาจารย์กำหนดผ่าน `INSTRUCTOR_EMAILS` เท่านั้น หน้า Admin แสดงรายชื่ออาจารย์ที่กำหนดไว้ แต่ไม่เพิ่มหรือถอนสิทธิ์จากฐานข้อมูล อาจารย์ที่อยู่ใน allowlist จึงเชิญเข้าห้องเรียนได้ นักศึกษาต้องมีอีเมลตรงกับ roster CSV ของห้องนั้น ไม่มี endpoint สมัครบัญชีด้วยรหัสผ่าน

`AUTH_MODE=mock` ใช้ได้เฉพาะเมื่อ `APP_ENV=development` สำหรับเดโมในเครื่อง โหมดนี้ไม่มีการยืนยันตัวตนจริง อย่าเปิดในการ deploy

## Checks

ตั้ง `TEST_DATABASE_URL` ใน `.env` เป็น PostgreSQL instance ที่ใช้ทดสอบ:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Database tests ใช้ schema แยกต่อ test เพื่อลดผลกระทบต่อข้อมูลเดิม; ควรใช้ instance สำหรับการทดสอบโดยเฉพาะเมื่อทำงานร่วมกัน
