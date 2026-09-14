# Tech Stack

## Decision Summary
ทีม: เก่งมากครับ
Domain: Pairwise
Date: 09-Sep-2026 (อัปเดตให้ตรงกับ code: 14-Sep-2026)

> **สถานะปัจจุบัน:** มีแค่ frontend (landing page) — Backend และ Database ด้านล่างเป็นแผนที่ตัดสินใจแล้ว แต่ยังไม่ได้เริ่มทำ

## Frontend — ✅ ใช้งานอยู่
- Framework: React 19.2 + Vite 7.3 (single-page app)
- Language: TypeScript 5.9 (strict)
- Styling: Tailwind CSS 4 (ผ่าน `@tailwindcss/vite`)
- Package manager / test runner: Bun (`bun.lock`, `bun:test`)
- Rationale:
  - React: Component-based ทำให้แยกส่วน UI ไปใช้ซ้ำได้ และแตกงานให้หลายคนทำพร้อมกันได้ง่าย
  - TypeScript: จับ error ตั้งแต่ตอนเขียน ไม่ต้องรอ runtime
  - Tailwind: เขียน style ในไฟล์เดียวกับ markup ไม่ต้องสลับไฟล์ ไม่ต้องคิดชื่อ class และไม่มีปัญหา CSS ชนกันหรือ specificity war เพราะไม่มี global selector
  - Vite + Bun: frontend ตอนนี้เป็นหน้าเว็บล้วน ไม่ต้องใช้ framework ใหญ่ — Vite build เป็นไฟล์ static ที่ deploy บน Vercel ได้ตรง ๆ ส่วน Bun ทำหน้าที่ทั้ง install และรัน test ในตัว ไม่ต้องติดตั้ง test framework เพิ่ม

## Backend — ⏳ แผน (ยังไม่เริ่ม)
- Framework: FastAPI
- Language: Python 3.12 + type hints
- Rationale:
  - เร็วในการเขียน — endpoint หนึ่งตัวใช้ไม่กี่บรรทัด ไม่ต้องตั้งค่าเยอะ เหมาะกับโปรเจกต์ที่ต้องเห็นผลไว
  - Type hints ใช้งานจริง — FastAPI ใช้ type hint ไป validate request/response อัตโนมัติผ่าน Pydantic ข้อมูลผิด format จะถูกปฏิเสธพร้อมบอกว่าผิดตรงไหน
  - เอกสาร API เกิดเอง — มี Swagger UI / ReDoc ที่ `/docs` ทีม frontend เปิดดูและยิง request ทดสอบได้ทันที
  - Async ในตัว — งานที่รอ I/O (เรียก API อื่น, อ่านไฟล์, รอ DB) ทำ concurrent ได้โดยไม่ต้องเพิ่ม library
  - Python ecosystem — ถ้าต้องต่อกับงาน ML / ประมวลผลข้อมูล ใช้ numpy ฯลฯ ได้ตรง ๆ ไม่ต้องแยก service

## Database — ⏳ แผน (ยังไม่เริ่ม)
- SQLite (ผ่าน SQLAlchemy หรือ SQLModel)
- Rationale:
  - ไม่ต้องติดตั้ง server — เป็นไฟล์เดียว ไม่ต้องตั้ง user/password/port ทุกคน clone แล้วรันได้ทันที
  - Backup ง่าย — ก๊อปไฟล์ `.db` ก็คือ backup
  - เร็วสำหรับงานอ่านเยอะ — อ่านจาก disk ตรง ๆ ไม่มี network overhead
  - ย้ายไป PostgreSQL ได้ภายหลัง — ใช้ ORM ทำให้เปลี่ยน connection string เป็นหลัก ไม่ต้องรื้อโค้ด
- ข้อควรระวัง: platform ส่วนใหญ่ (Vercel, Render free tier) มี filesystem ที่ถูกล้างทุกครั้งที่ deploy/restart ถ้าใช้ SQLite บน production ต้องมี persistent disk หรือย้ายไป PostgreSQL — ต้องตัดสินใจก่อนเริ่มทำ backend

## Deployment
- Platform (frontend): Vercel — Vite preset, build `bun run build`, output `dist`, deploy อัตโนมัติเมื่อ push เข้า `develop`
- Platform (backend): ยังไม่ตัดสินใจ (lab แนะนำ Render สำหรับ FastAPI)
- Staging URL: [จะเพิ่มหลัง deploy]
- Commit-to-live time: [จะวัดหลัง deploy]

## AI Tools
- Agent ที่ใช้: GitHub Copilot, Claude, GPT Codex
- Review policy: ทุก AI-generated code ต้องอ่านและอธิบายได้ก่อน commit
