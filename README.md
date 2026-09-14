# Pairwise

ระบบประเมินผลนักศึกษาแบบ pairwise comparison สำหรับงานกลุ่มในมหาวิทยาลัย
นักศึกษาเปรียบเทียบกลุ่ม (หรือเพื่อนร่วมกลุ่ม) ทีละคู่ในแต่ละเกณฑ์ แล้วระบบคำนวณเป็น
คะแนนกลุ่มและคะแนนรายบุคคล ให้อาจารย์ตรวจสอบและยืนยันผล — requirement ทั้งหมดอยู่ใน
[docs/prd.md](docs/prd.md)

> **สถานะปัจจุบัน:** โครง frontend (landing page) เท่านั้น
> หน้าประเมินจริงยังเป็น placeholder และยังไม่มี backend / database
>
> **Live:** https://sdpx-very-good.vercel.app (deploy อัตโนมัติเมื่อ push เข้า `develop`)

## Tech Stack

| ส่วน | ที่ใช้ |
| --- | --- |
| Framework | React 19 |
| Language | TypeScript 5.9 (strict) |
| Styling | Tailwind CSS 4 (ผ่าน `@tailwindcss/vite`) |
| Build tool | Vite 7 |
| Runtime / package manager / test | Bun |

Backend (FastAPI + PostgreSQL, login ด้วย Google) เป็นแผนที่ตัดสินใจไว้แล้ว แต่ **ยังไม่ได้เริ่มทำ** —
รายละเอียดและเหตุผลอยู่ใน [memory-bank/standards/tech-stack.md](memory-bank/standards/tech-stack.md)
ภาพรวมระบบอยู่ใน [docs/architecture.md](docs/architecture.md) และ schema อยู่ใน [docs/erd.md](docs/erd.md)

## เริ่มใช้งาน

```bash
bun install
bun run dev     # เปิด http://localhost:5173
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
    FeaturePlaceholder.tsx          ที่ที่หน้าประเมินจะมาอยู่
docs/
  prd.md                            requirement ของระบบ (PRD v2.0)
  architecture.md                   component diagram และการตัดสินใจเชิงสถาปัตยกรรม
  erd.md                            ER diagram ของ database (PostgreSQL)
  user-stories.md                   user stories พร้อม acceptance criteria
  open-questions.md                 คำถามที่ requirement ยังตอบไม่ได้
  ui-design.md                      แนวทางออกแบบ UI: สี ตัวอักษร และหน้าประเมิน
memory-bank/standards/tech-stack.md บันทึกการตัดสินใจเรื่อง tech stack
AGENTS.md                           กติกาสำหรับ AI agent ที่มาแก้ repo นี้
LOOP_NOTES.md                       บันทึกผลการทดลองให้ AI รันจน test เขียว
```

## Test

Test รันด้วย `bun:test` โดย render component เป็น static markup
(`renderToStaticMarkup`) แล้วตรวจว่ามีข้อความและ `data-testid` ที่ต้องการ
— ยังไม่ได้ใช้ DOM testing library

```bash
bun test                    # รันทุก test
bun test src/App.test.tsx   # รันไฟล์เดียว
bun test --coverage         # ดู coverage
```

ตอนนี้มี 4 tests ใน [src/App.test.tsx](src/App.test.tsx) และผ่านทั้งหมด
คำสั่ง test ทั้งหมดอยู่ในหัวข้อ Testing ของ [AGENTS.md](AGENTS.md)

## การทำงานร่วมกัน

อ่าน [AGENTS.md](AGENTS.md) ก่อนแก้โค้ด สรุปสั้น ๆ:

- ใส่ `data-testid` ให้ element ที่ test จะอ้างถึง
- Commit ตาม Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`)
- ทำงานบน branch `feature/*` แล้ว PR เข้า `develop`
- test ต้องเขียวก่อนเสนอ diff — ถ้าแดงให้แก้ code ห้ามแก้ test
- ห้าม commit secret ลง repo ใช้ env var เท่านั้น
- UI ใช้สีและรูปแบบตาม [docs/ui-design.md](docs/ui-design.md)
