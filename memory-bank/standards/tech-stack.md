# Tech Stack

## Decision Summary
ทีม: เก่งมากครับ
Domain: Pairwise
Date: 09-Sep-2026 (อัปเดตให้ตรงกับ code: 14-Sep-2026 · เปลี่ยน Database เป็น PostgreSQL และเลือกรูปแบบ session: 14-Sep-2026)

> **สถานะปัจจุบัน:** มีแค่ frontend (landing page) — Backend, Database และ Authentication ด้านล่างเป็นแผนที่ตัดสินใจแล้ว แต่ยังไม่ได้เริ่มทำ

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
- PostgreSQL (ผ่าน SQLAlchemy) — เปลี่ยนจาก SQLite เมื่อ 14-Sep-2026 ก่อนเริ่มทำ backend
- Schema: [docs/erd.md](../../docs/erd.md)
- Rationale:
  - ตรงกับ PRD §6 และ data model §11 ที่ใช้ `text[]` (เช่น `allowed_email_domains`, `flags`) และ `numeric` — SQLite ไม่มีชนิด array
  - ข้อมูลอยู่รอดข้าม deploy — PRD ให้เก็บข้อมูล 2 ปีการศึกษา (§14.1) และ RPO ≤ 15 นาที (NFR-AVAIL-02) ขณะที่ไฟล์ SQLite บน host ส่วนใหญ่ถูกล้างทุกครั้งที่ deploy/restart
  - รับการเขียนพร้อมกันได้ — ชั่วโมงสุดท้ายก่อน deadline มีคน autosave/submit พร้อมกันจำนวนมาก (NFR-SCALE-02) ส่วน SQLite เขียนได้ทีละ transaction
  - ยังใช้ SQLAlchemy เหมือนแผนเดิม — แนวทางเขียน code ฝั่ง backend ไม่เปลี่ยน
- ยังไม่ตัดสิน: host ของ database และวิธีรัน PostgreSQL ตอน local dev
- หมายเหตุ: เป็นการเปลี่ยน stack หลังเลือกไปแล้ว — ควรบันทึกเหตุผลเป็น ADR (WS-08)

## Authentication — ⏳ แผน (ยังไม่เริ่ม)
- Login: Google OAuth 2.0 / OIDC เท่านั้น (FR-AUTH-01) แบบ authorization code flow ที่ server เป็นคนคุยกับ Google — browser redirect ไป Google แล้วกลับมาที่ `/api/auth/google/callback` token ของ Google จึงไม่ผ่าน JavaScript เลย (ตัดสินเมื่อ 14-Sep-2026)
- Session: เก็บฝั่ง server ในตาราง `session` แล้วส่ง id ผ่าน cookie แบบ `httpOnly` + `Secure` + `SameSite` (FR-SEC-01) อายุ 12 ชั่วโมงและ refresh ได้ (FR-AUTH-04)
- Rationale:
  - ตรงกับ FR-SEC-01 ที่บังคับใช้ cookie — JavaScript ในหน้าเว็บอ่าน cookie `httpOnly` ไม่ได้ จึงขโมยผ่าน XSS ไม่ได้
  - ยกเลิก session ได้ทันที (logout, ปิดบัญชี) เพราะเก็บไว้ที่ server — ต่างจาก JWT ที่ใช้ได้จนหมดอายุ
- ข้อจำกัด: API ต้องอยู่ site เดียวกับเว็บ (เช่น Vercel rewrite `/api/*` ไป backend) เพราะ browser ไม่ส่ง cookie ข้าม site

## Deployment
- Platform (frontend): Vercel — Vite preset, build `bun run build`, output `dist`, deploy อัตโนมัติเมื่อ push เข้า `develop`
- Platform (backend): ยังไม่ตัดสินใจ (lab แนะนำ Render สำหรับ FastAPI)
- Staging URL: https://sdpx-very-good.vercel.app
- Commit-to-live time: 9.30 วินาที (วัดเมื่อ WS-01)

## AI Tools
- Agent ที่ใช้: GitHub Copilot, Claude, GPT Codex
- Review policy: ทุก AI-generated code ต้องอ่านและอธิบายได้ก่อน commit
