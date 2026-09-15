# Pairwise

เว็บสำหรับจัดอันดับสิ่งต่าง ๆ ด้วยการเปรียบเทียบทีละคู่ (pairwise comparison)
สำหรับงานในมหาวิทยาลัย — จัดอันดับโปรเจกต์ หัวข้อ หรือ peer review

> **สถานะปัจจุบัน:** Frontend เป็น landing page + หน้าเปรียบเทียบจริงยังเป็น placeholder
> Backend เริ่มมี domain code แล้ว (`backend/`, FastAPI) ครอบคลุม roster import และ publish service
> แต่ยังไม่มี database จริง (มีแค่ in-memory Fake สำหรับ test) และยังไม่ได้ deploy

## Tech Stack

| ส่วน | ที่ใช้ |
| --- | --- |
| Framework | React 19 |
| Language | TypeScript 5.9 (strict) |
| Styling | Tailwind CSS 4 (ผ่าน `@tailwindcss/vite`) |
| Build tool | Vite 7 |
| Runtime / package manager / test | Bun |

Backend (FastAPI + SQLite) และ deployment (Vercel) เป็นแผนที่ตัดสินใจไว้แล้ว
แต่ **ยังไม่ได้เริ่มทำ** — รายละเอียดและเหตุผลอยู่ใน
[memory-bank/standards/tech-stack.md](memory-bank/standards/tech-stack.md)

## เริ่มใช้งาน

```bash
bun install
bun run dev     # เปิด http://localhost:5173
```

Backend (Python):

```bash
python -m venv .venv && .venv/Scripts/activate   # หรือ source .venv/bin/activate บน macOS/Linux
pip install -r backend/requirements.txt -r requirements-dev.txt
pytest                                            # รัน unit tests
uvicorn app.main:app --reload --app-dir backend   # เปิด API ที่ http://localhost:8000
```

## Commands

| คำสั่ง | ทำอะไร |
| --- | --- |
| `bun install` | ติดตั้ง dependencies |
| `bun run dev` | รัน Vite dev server (port 5173) |
| `bun test` | รัน test ด้วย `bun:test` |
| `bun run lint` | ตรวจ type ด้วย `tsc --noEmit` |
| `bun run build` | ตรวจ type แล้ว build ลง `dist/` |
| `bun run preview` | ดู production build ที่ build แล้ว |
| `pytest` | รัน backend unit tests ด้วย `pytest` |
| `uvicorn app.main:app --reload --app-dir backend` | รัน FastAPI dev server (port 8000) |

## โครงสร้างโปรเจกต์

```
index.html                          entry point ของ Vite
src/
  main.tsx                          mount React ลง #root
  App.tsx                           หน้า landing page
  App.test.tsx                      test — render เป็น static markup แล้วเช็ค
  index.css                         import Tailwind
  components/
    Navbar.tsx                      แถบนำทาง (data-testid="main-nav")
    FeaturePlaceholder.tsx          ที่ที่หน้าเปรียบเทียบจะมาอยู่
backend/
  app/
    main.py                         FastAPI app — /api/health, /api/rosters/import
    domain/roster.py                parse_roster, normalize_email, allocate_pairs
    services/publish.py             publish(assignment_id, repo)
    repositories/protocols.py       AssignmentRepo (Protocol)
  requirements.txt                  fastapi, pydantic, uvicorn
tests/
  unit/                             pytest — test_roster_import.py, test_publish.py
  fakes/fake_assignment_repo.py     in-memory AssignmentRepo สำหรับ test
  factories.py                      make_roster_row / make_roster_csv / make_roster
  conftest.py                       fixtures — valid_csv, csv_with_bad_row_42
memory-bank/standards/tech-stack.md บันทึกการตัดสินใจเรื่อง tech stack
AGENTS.md                           กติกาสำหรับ AI agent ที่มาแก้ repo นี้
LOOP_NOTES.md                       บันทึกผลการทดลองให้ AI รันจน test เขียว
```

## Test

Test รันด้วย `bun:test` โดย render component เป็น static markup
(`renderToStaticMarkup`) แล้วตรวจว่ามีข้อความและ `data-testid` ที่ต้องการ
— ยังไม่ได้ใช้ DOM testing library

```bash
bun test
```

ตอนนี้มี 4 tests ใน [src/App.test.tsx](src/App.test.tsx) และผ่านทั้งหมด

## การทำงานร่วมกัน

อ่าน [AGENTS.md](AGENTS.md) ก่อนแก้โค้ด สรุปสั้น ๆ:

- ใส่ `data-testid` ให้ element ที่ test จะอ้างถึง
- Commit ตาม Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`)
- ทำงานบน branch `feature/*` แล้ว PR เข้า `develop`
- test ต้องเขียวก่อนเสนอ diff — ถ้าแดงให้แก้ code ห้ามแก้ test
- ห้าม commit secret ลง repo ใช้ env var เท่านั้น
