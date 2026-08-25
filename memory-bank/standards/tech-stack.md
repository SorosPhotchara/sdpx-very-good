# Tech Stack

> Renamed from `teck-stack.md` in WS-03. The old file also carried unresolved
> `<<<<<<<` merge markers into a commit — see the Lessons section at the end.

## Decision Summary

- **ทีม:** เก่งมากครับ
- **Domain:** PairEval — ระบบประเมินผลนักศึกษาแบบ pairwise comparison (`pairwise_evaluation_prd.md`)
- **Date:** 2026-07-21 (updated 2026-08-25)

## Frontend

- **Framework:** React 18 + Vite 5
- **Language:** TypeScript (`strict: true`)
- **Styling:** Tailwind CSS 3
- **Rationale:** PRD §13 ต้องรองรับจอกว้าง ≥ 320 px และ mobile-first (NFR-COMPAT-02)
  Tailwind ทำ responsive ได้โดยไม่ต้องเขียน media query เอง · Vite ให้ dev server
  ที่ reload เร็ว ซึ่งสำคัญกับ loop latency ของทีม · เลือก React เพราะสมาชิกทุกคน
  เคยเขียนมาแล้ว ไม่ต้องเสียเวลาเรียน framework ใหม่ระหว่าง sprint

## Backend

- **Framework:** FastAPI + SQLAlchemy 2
- **Language:** Python 3.12+
- **Rationale:** คุ้นเคยกับ Python · หัวใจของระบบคือ pairing engine (§8) และ
  scoring engine (§9) ซึ่งเป็นงานคำนวณล้วน ๆ ที่ต้อง unit test หนัก — Python +
  `pytest` + `hypothesis` ทำ property-based test ตาม NFR-MAINT-02 ได้ตรงไปตรงมา
  · FastAPI generate OpenAPI ให้อัตโนมัติ ใช้ cross-check กับ `docs/openapi.yaml` ได้

## Database

- **Dev:** SQLite (`backend/paireval.db`, ไม่ commit)
- **Production target:** PostgreSQL (PRD §6)
- **Rationale:** SQLite เก็บในไฟล์เดียว ไม่ต้องติดตั้ง ทุกคนใน lab เริ่มได้ทันที ·
  แต่ PRD §11 ใช้ `numeric`, `text[]` และ append-only audit log ซึ่ง SQLite ทำได้ไม่ครบ
  จึงเขียนผ่าน SQLAlchemy เพื่อให้ย้ายไป PostgreSQL ได้โดยไม่ต้องแก้ query
- **ข้อควรระวัง:** DR-04 บังคับให้เก็บคะแนนเป็น `numeric` ไม่ใช่ `float` —
  scoring engine ใช้ `Decimal` ตลอดเส้นทางแล้ว แต่ตาราง `assignment` ปัจจุบัน
  ยังเป็น `Float` อยู่ ต้องแก้ก่อนขึ้น production (ดู `docs/backlog.md`)

## Deployment

- **Platform:** Vercel (frontend) + Render (backend)
- **Staging URL:** _ยังไม่ได้ deploy_ — ดูหัวข้อถัดไป
- **Commit-to-live time:** _ยังวัดไม่ได้_ — ต้อง deploy ก่อน

### สถานะจริงของ Deploy Loop (2026-08-25)

Deploy loop **ยังไม่ปิด** และเป็นงานค้างชิ้นเดียวที่เหลือจาก WS-01

| ขั้น | สถานะ |
|---|---|
| commit → push | ✅ ทำได้ |
| build | ✅ `cd frontend && npm run build` ผ่านบนเครื่อง |
| deploy | ❌ ยังไม่ได้เชื่อม Vercel/Render กับ repo |
| เห็น URL จริง | ❌ |
| วัดเวลา | ❌ |

**ทำไมยังไม่เสร็จ:** การเชื่อม Vercel/Render ต้อง login ด้วยบัญชี GitHub ของเจ้าของ repo
และกดอนุมัติสิทธิ์เข้าถึง ซึ่งทำแทนกันไม่ได้

**ขั้นตอนที่เหลือ:**

1. vercel.com → Add New Project → Import `SorosPhotchara/sdpx-very-good`
2. ตั้ง **Root Directory = `frontend`** (สำคัญ — repo นี้เป็น monorepo)
3. Production Branch = `develop` เพื่อให้ push แล้ว deploy เอง (ไม่ต้องกดปุ่ม)
4. render.com → New Web Service → Root Directory = `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. แก้ข้อความบนหน้าแรก 1 บรรทัด → commit → push → จับเวลาจนเห็นของใหม่
6. เอาตัวเลขมาเติม 2 บรรทัดข้างบน

## AI Tools

- **Agent ที่ใช้:** GitHub Copilot / Claude / Cursor
- **Review policy:** ทุก AI-generated code ต้องอ่านและอธิบายได้ก่อน commit
- **กติกาที่เขียนไว้ให้ agent อ่าน:** `AGENTS.md` (ห้ามแก้ test เพื่อให้ผ่าน,
  ห้าม commit secret, diff เกิน ~200 บรรทัดให้หยุดถาม)

## Testing

- **Unit + property:** `pytest` + `hypothesis` — `pytest` ที่ root รันครบทุก suite
- **E2E:** Playwright (Chromium)
- **Coverage:** `coverage.py` → `docs/coverage/`
- **Loop latency:** ดู `TEST_PLAN.md`

## Lessons ที่ต้องไม่ทำซ้ำ

| เกิดอะไรขึ้น | ผลที่ตามมา | กันยังไง |
|---|---|---|
| commit ไฟล์ที่มี merge marker `<<<<<<<` ค้าง | ไฟล์มาตรฐานของทีมอ่านไม่รู้เรื่องอยู่หลายสัปดาห์ | อ่าน diff ก่อน commit เสมอ — `git diff --cached` |
| `.gitignore` มีแต่ Node | `__pycache__` 17 ไฟล์ และ `paireval.db` หลุดเข้า git | เพิ่ม pattern ของ **ทุกภาษา** ที่ repo ใช้ ตั้งแต่ commit แรก |
| ตั้งชื่อไฟล์ `teck-stack.md` / `AGENT.md` | agent หาไฟล์ไม่เจอ เพราะมันมองหา `AGENTS.md` | ชื่อไฟล์ที่เครื่องอ่านต้องสะกดตามสเปกเป๊ะ |
| `backend/package.json` เขียน `py -m uvicorn` | รันบน Linux/macOS ไม่ได้เลย | ใช้ `python3` และทดสอบบนเครื่องของสมาชิกทุกคน |
