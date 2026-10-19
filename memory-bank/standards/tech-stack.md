# Tech Stack

## Decision Summary
ทีม: เก่งมากครับ Domain: Pairwise Evaluation System (PairEval) Date: 21-7-2026

อัปเดต 19 ตุลาคม 2026 ตามแอปที่อยู่ใน `frontend/` และ `backend/`

## Frontend

- React 18, TypeScript และ Vite 5
- Tailwind CSS 3 และส่วนประกอบ shadcn/ui ใน `frontend/src/components/ui/`
- npm เป็นตัวติดตั้งและรันคำสั่งจาก `frontend/package.json`
- Rationale: คุ้นเคยกับ python

## Backend

- Python 3.12+, FastAPI, Pydantic และ SQLAlchemy 2
- Alembic สำหรับ migrations และ psycopg สำหรับ PostgreSQL
- API อยู่ใน `backend/app/`; การทดสอบอยู่ใน `backend/tests/`

## Database and deployment

- PostgreSQL; ใช้ Docker สำหรับฐานข้อมูลบนเครื่อง และ Neon สำหรับ deployment
- Vercel Services ให้บริการ frontend และ API ตาม `vercel.json`
- ค่าตั้งต้นอยู่ใน `frontend/.env.example` และ `backend/.env.example`; ค่าใช้งานจริงอยู่ใน environment variables

## Deployment
- Platform: Vercel
- Staging URL: [https://sdpx-very-good.vercel.app/]

## AI Tools
- Code generation: GitHub Copilot / Claude / Cursor / Copilot / Codex
- Review policy: ทุก AI-generated code ต้องอ่านและอธิบายได้ก่อน commit

## Verification

- Frontend: `npm run lint`, `npm test`, `npm run build` จาก `frontend/`
- Backend: `python -m pytest` จาก `backend/`; integration tests ต้องมี PostgreSQL
