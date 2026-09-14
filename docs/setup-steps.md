# Setup Steps — Environment Loop

ขั้นตอนตั้งแต่ clone repo จนเปิดหน้า app และรัน test ได้บนเครื่องใหม่

## Before (WS-05)

1. ติดตั้ง Node 24 (Playwright ต้องใช้ `npx`)
2. ติดตั้ง Bun (`curl -fsSL https://bun.sh/install | bash`) แล้วเปิด shell ใหม่
3. `git clone` แล้ว `cd` เข้า repo
4. `bun install`
5. `npx playwright install --with-deps` (ดาวน์โหลด browser ~500 MB และต้องใช้ sudo)
6. `bun run dev` → เปิด http://localhost:5173

→ 6 ขั้นตอน ~25 นาที (ประมาณการ — ขึ้นกับความเร็วเน็ตและว่ามี Node/Bun อยู่แล้วหรือยัง)
และถ้า version ของ Node/Bun ไม่ตรงกัน ผลของ test ในแต่ละเครื่องก็อาจไม่ตรงกัน

## After

ต้องมีแค่ Docker (Docker Desktop หรือ Docker Engine + Compose v2)

1. `docker compose up` → เปิด http://localhost:3000

→ 1 ขั้นตอน ~40 วินาที (ครั้งแรก วัดจริง — pull image + `npm ci`) / ~20 วินาที (ครั้งถัดไป — ประมาณการ ยังไม่ได้วัด)

Test ใช้คำสั่งเดียวเช่นกัน (ดู section Commands ใน `AGENTS.md`):

```bash
docker compose -f compose.test.yaml up unit --build --abort-on-container-exit --exit-code-from unit
docker compose -f compose.test.yaml --profile e2e up e2e --build --abort-on-container-exit --exit-code-from e2e
docker compose -f compose.test.yaml down -v
```

## ผลที่วัดได้จริง

| สิ่งที่วัด | ผล | ใครวัด / วันที่ |
|---|---|---|
| `docker compose up` ครั้งแรก | ~40 วินาที จนถึง Vite ready — build image app 38.1 วินาที (pull `node:24-alpine` 7.3 วินาที, `npm ci` 17.5 วินาที, `npm run build` 2.4 วินาที, export image 7.3 วินาที) โดย pull `postgres:17-alpine` 16.9 วินาทีรันขนานกันไป จากนั้น db healthy และ Vite ready ใน 150 ms | george (Ubuntu 26.04) / 14-Sep-2026 |
| `docker compose up` ครั้งถัดไป | 2 วินาที | Toto is comming (Windows11) 14-sep-2026 |
| Clone ใหม่บนเครื่องที่ไม่เคยรัน project | _(กรอกหลังรัน)_ | |
| Unit test ผ่าน → exit code | _(กรอกหลังรัน)_ | |
| Unit test แดง → exit code (ต้องไม่ใช่ 0) | _(กรอกหลังรัน)_ | |
| E2E ผ่าน → exit code | _(กรอกหลังรัน)_ | |
