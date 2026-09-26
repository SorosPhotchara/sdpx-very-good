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

Backend โหลด `backend/.env` ผ่าน `python-dotenv` อัตโนมัติ ไฟล์นี้ถูก ignore โดย Git; ตัวอย่างค่าที่ต้องมีอยู่ใน `.env.example` `DATABASE_URL` ต้องชี้ไป PostgreSQL และไม่มีค่าเริ่มต้นอัตโนมัติ `seed_demo.py` รักษาห้องต้นแบบ 4 ห้องและเพิ่มห้องเดโมที่มี 3 กลุ่มและ 9 นักศึกษาแบบเรียกซ้ำได้ โดยไม่แก้ข้อมูลห้องเรียนเดิม

## Authentication

โหมดปกติใช้ Google Sign-In: frontend ส่ง Google ID token ให้ API และ backend ตรวจ audience ด้วย `GOOGLE_CLIENT_ID` รวมทั้งตรวจว่าอีเมลได้รับการยืนยันจาก Google ผู้ดูแลระบบเริ่มต้นกำหนดผ่าน `ADMIN_EMAILS`; อาจารย์เริ่มต้นกำหนดได้ใน `INSTRUCTOR_EMAILS` หรือเพิ่มจากหน้า Admin ซึ่งบันทึกใน PostgreSQL อาจารย์ที่ได้รับอนุมัติแล้วจึงเชิญเข้าห้องเรียนได้ นักศึกษาต้องมีอีเมลตรงกับ roster CSV ของห้องนั้น ไม่มี endpoint สมัครบัญชีด้วยรหัสผ่าน

`AUTH_MODE=mock` ใช้ได้เฉพาะเมื่อ `APP_ENV=development` สำหรับเดโมในเครื่อง โหมดนี้ไม่มีการยืนยันตัวตนจริง อย่าเปิดในการ deploy

## Checks

ตั้ง `TEST_DATABASE_URL` ใน `.env` เป็น PostgreSQL instance ที่ใช้ทดสอบ:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Database tests ใช้ schema แยกต่อ test เพื่อลดผลกระทบต่อข้อมูลเดิม; ควรใช้ instance สำหรับการทดสอบโดยเฉพาะเมื่อทำงานร่วมกัน
