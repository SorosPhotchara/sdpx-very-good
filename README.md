# PairEval

ระบบประเมินผลงานนักศึกษาแบบเปรียบเทียบคู่ รองรับการจัดห้องเรียน งานประเมิน คะแนน รายงาน และการใช้งานทั้งภาษาไทยและอังกฤษ

คู่มือสำหรับอาจารย์และนักศึกษา: [USER_GUIDE.md](USER_GUIDE.md)

## สิ่งที่ต้องติดตั้ง

- Git
- Python 3.12
- Node.js และ npm
- Docker Desktop

## ติดตั้งโปรเจกต์บน Windows

### 1. Clone โปรเจกต์และสร้างไฟล์ environment

```powershell
git clone <repository-url>
cd sdpx-very-good

Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

ไฟล์ `.env` จะไม่ถูก commit เข้า Git ให้แต่ละคนสร้างจาก `.env.example` บนเครื่องของตนเอง

### 2. เลือกวิธีเข้าสู่ระบบ

#### โหมดทดลอง

ค่าเริ่มต้นจาก `.env.example` ใช้งานโหมดทดลองได้ทันที

`backend/.env`:

```env
APP_ENV=development
AUTH_MODE=mock
INSTRUCTOR_EMAILS=teacher@example.edu
ADMIN_EMAILS=teacher@example.edu
```

`frontend/.env`:

```env
VITE_AUTH_MODE=mock
```

บัญชีตัวอย่างคือ `teacher@example.edu` และ `student1@example.edu`

#### Google Login

สร้าง OAuth Client ID ชนิด **Web application** ใน Google Cloud และเพิ่ม Authorized JavaScript origins:

```text
http://localhost
http://localhost:5173
```

ตั้งค่า `backend/.env`:

```env
GOOGLE_CLIENT_ID=<google-web-client-id>
ADMIN_EMAILS=admin@gmail.com
INSTRUCTOR_EMAILS=teacher1@gmail.com
AUTH_MODE=google
```

ตั้งค่า `frontend/.env` โดยใช้ Client ID เดียวกัน:

```env
VITE_GOOGLE_CLIENT_ID=<google-web-client-id>
VITE_AUTH_MODE=google
```

ถ้า OAuth App อยู่ในสถานะ Testing ต้องเพิ่มบัญชีที่ใช้เข้าสู่ระบบในรายการ Test users ของ Google Cloud ด้วย ผู้ดูแลระบบเริ่มต้นต้องใช้อีเมลใน `ADMIN_EMAILS` ส่วน `INSTRUCTOR_EMAILS` ใช้กำหนดอาจารย์เริ่มต้น นักศึกษาต้องใช้อีเมลที่ตรงกับ roster CSV

ระบบไม่มีหน้าสมัครสมาชิกแยก Google จะยืนยันตัวตนและ Backend จะกำหนดสิทธิ์จากอีเมล

### 3. เปิด PostgreSQL

รันจากโฟลเดอร์หลักของโปรเจกต์:

```powershell
docker compose up -d postgres
```

Docker ใช้สำหรับ PostgreSQL เท่านั้น ส่วน Backend และ Frontend รันบนเครื่อง โดยฐานข้อมูลเปิดที่ `127.0.0.1:5433`

### 4. ติดตั้งและรัน Backend

เปิด Terminal ใหม่:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

สร้าง virtual environment และติดตั้ง package เฉพาะครั้งแรก ส่วน `alembic upgrade head` ให้รันเมื่อสร้างฐานข้อมูลใหม่หรือหลังดึง migration ใหม่

หากต้องการข้อมูลตัวอย่าง ให้รันหนึ่งครั้งก่อนเปิด Uvicorn:

```powershell
.\.venv\Scripts\python.exe seed_demo.py
```

Backend โหลดค่าจาก `backend/.env` อัตโนมัติ

### 5. ติดตั้งและรัน Frontend

เปิด Terminal อีกหน้าต่าง:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --host localhost --port 5173
```

`npm.cmd ci` ทำเฉพาะครั้งแรกหรือเมื่อ dependencies เปลี่ยน จากนั้นเปิด [http://localhost:5173](http://localhost:5173)

## การใช้งานสำหรับอาจารย์

1. เข้าสู่ระบบด้วยอีเมลที่อยู่ใน `INSTRUCTOR_EMAILS` หรือได้รับอนุมัติจากผู้ดูแลระบบ
2. สร้าง Classroom จากแถบด้านซ้าย
3. เปิด **จัดการห้องเรียน** และนำเข้า roster CSV
   หรือกรอก **อีเมล Google ของนักศึกษา** กับ **ชื่อกลุ่ม** เพื่อเพิ่มทีละคนก่อนเผยแพร่ Assignment
4. สร้าง Assignment กำหนดคะแนน Deadline และเกณฑ์ประเมิน
5. ตรวจคู่ประเมินแล้ว Publish
6. ติดตามผลประเมิน ดูคะแนน และดาวน์โหลดรายงาน

ผู้ดูแลระบบที่อยู่ใน `ADMIN_EMAILS` สามารถอนุมัติหรือถอนสิทธิ์อาจารย์ได้จากหน้า **จัดการสิทธิ์อาจารย์** โดยรายชื่อที่เพิ่มผ่านหน้านี้จะเก็บใน PostgreSQL และใช้เชิญเข้าห้องเรียนได้ทันที ไม่ต้องแก้ environment หรือ deploy ใหม่

รูปแบบ roster CSV:

```csv
email,groupname
student1@gmail.com,Group 1
student2@gmail.com,Group 1
student3@gmail.com,Group 2
student4@gmail.com,Group 2
student5@gmail.com,Group 3
student6@gmail.com,Group 3
```

ควรมีอย่างน้อย 3 กลุ่มก่อนเผยแพร่ Group Evaluation และกลุ่มต้องมีสมาชิกอย่างน้อย 3 คนจึงจะเปิด Individual Evaluation ได้

## หยุดระบบ

กด `Ctrl+C` ใน Terminal ของ Backend และ Frontend จากนั้นหยุด PostgreSQL:

```powershell
docker compose stop postgres
```

ข้อมูลยังคงอยู่ใน Docker volume `paireval_demo_data`

## ทดสอบ

เปิด PostgreSQL ก่อน แล้วรัน Backend tests จาก `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

หรือรัน pytest และ PostgreSQL ชั่วคราวใน container:

```powershell
cd backend
npm.cmd run test:container
```

รัน Frontend checks จาก `frontend/`:

```powershell
npm.cmd test
npm.cmd run test:e2e
npm.cmd run lint
npm.cmd run build
```

### Docker tests on a fresh machine

Install Node.js and Docker Desktop, start Docker, and clone this repository. No image exported from another developer's machine is needed. Compose downloads the PostgreSQL/Python/Playwright base images and builds the test images from the Dockerfiles; later runs reuse cached layers.

From the repository root, run these commands one at a time:

```powershell
npm.cmd --prefix backend run test:container
npm.cmd --prefix frontend run test:e2e
```

These container tests use a temporary PostgreSQL database and mock Google identities. They do not need Neon credentials or a Google OAuth client. The runner removes the test containers and temporary data afterward.

คำสั่ง E2E ใช้ `compose.test.yml` เพื่อ build และรัน Playwright, Chromium, Backend และ Frontend ภายใน service `e2e` พร้อมฐานข้อมูล `test-db` แบบชั่วคราว ข้อมูลทดสอบอยู่ใน schema `paireval_e2e` ซึ่งถูกสร้างใหม่ทุกครั้ง และ container ทดสอบจะถูกลบเมื่อจบ
