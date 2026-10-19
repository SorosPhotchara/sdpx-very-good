# WS-07 before: k6 smoke baseline

ทดสอบวันที่ 5 ตุลาคม 2569 ด้วย k6 1.8.1 บน API และ PostgreSQL ที่รันใน Docker ของเครื่องนี้เท่านั้น เป้าหมายคือ `GET /api/health` ซึ่งมีอยู่แล้วใน `backend/app/main.py` และตอบ `{"status":"ok"}` เมื่อฐานข้อมูลพร้อม การทดสอบนี้ยังไม่ใช่ผลของ staging หรือการวัด user journey จริง

| Metric | ผล local | เกณฑ์ |
|---|---:|---:|
| Virtual users / duration | 3 / 30 วินาที | ตามโจทย์ |
| Requests | 90 (2.98 requests/s) | — |
| `http_req_duration` p95 | 5.73 ms | < 500 ms |
| `http_req_failed` | 0% (0/90) | < 1% |
| Checks | 180/180 ผ่าน | — |
| Exit code | 0 | ผ่าน |

การพิสูจน์ threshold ที่ไม่ผ่าน: ใช้ `BASE_URL=http://127.0.0.1:9` ใน container และ `K6_DURATION=2s`; ทั้ง 6 requests เชื่อมต่อไม่ได้, `http_req_failed=100%`, Docker/k6 คืน exit code **1**. ไม่ได้ยิงไปยัง production

## รันซ้ำบน PowerShell

```powershell
docker build -f backend/Dockerfile --target runtime -t paireval-smoke-api .
docker compose -f compose.test.yml up -d test-db
docker run -d --name paireval-smoke-api --network paireval-test_default -e DATABASE_URL=postgresql+psycopg://testuser:testpass@test-db:5432/testdb paireval-smoke-api
$mount = 'type=bind,source=' + (Get-Location).Path + '\performance,target=/work'
docker run --rm --network paireval-test_default --mount $mount -e BASE_URL=http://paireval-smoke-api:8000 grafana/k6:1.8.1 run --summary-export=/work/smoke-local.json /work/smoke.js
docker rm -f paireval-smoke-api
docker compose -f compose.test.yml down --volumes
```

`performance/smoke-local.json` เป็นผลดิบที่สร้างใหม่ได้และถูก ignore ไว้ในเครื่อง ขั้นตอน staging ต้องใช้ URL ของ staging ที่ทีมอนุญาตให้ยิง load test; `sdpx-very-good.vercel.app` ดูเป็น production จึงไม่ได้ใช้ทดสอบ
