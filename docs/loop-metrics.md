# Loop Metrics — WS-06

บันทึกนี้ใช้เวลาที่วัดได้จริงเท่านั้น ก่อนหน้านี้มี CI ขั้นต้นอยู่แล้ว จึงไม่มี baseline ของช่วง "ก่อนมี CI" ที่วัดย้อนหลังได้

| ตัวชี้วัด | ก่อนมี CI (ย้อนหลัง) | Local reference, 5 ต.ค. 2569 | CI หลังปรับ |
|---|---|---|---|
| Frontend unit test | ไม่มีข้อมูล | 0.94 วินาที (6 tests) | รอผล GitHub Actions |
| Backend unit test (PostgreSQL) | ไม่มีข้อมูล | 9.15 วินาที (47 tests, coverage 85.59%) | รอผล GitHub Actions |
| E2E (Playwright) | ไม่มีข้อมูล | 51.3 วินาที (27 tests) | รอผล GitHub Actions |
| Pipeline ทั้งชุด | ไม่มีข้อมูล | ไม่ใช่ตัวชี้วัด local | รอ successful run |
| Lead time จาก commit ถึง staging | ไม่มีข้อมูล | ไม่ใช่ตัวชี้วัด local | รอ deploy staging สำเร็จ |
| Deployment frequency | ไม่มีข้อมูล | ไม่ใช่ตัวชี้วัด local | รอข้อมูล deployment อย่างน้อย 1 สัปดาห์ |

## วิธีวัด

- Local: จับเวลาตั้งแต่เริ่มคำสั่งทดสอบจนคำสั่งจบ โดยแยกเวลาสร้าง Docker image ออกจากเวลารัน test หากต้องการเทียบรอบถัดไป
- CI: ใช้เวลาเริ่มและจบของ job จาก GitHub Actions run เดียวกัน; pipeline คือเวลาตั้งแต่ workflow เริ่มจน `deploy-staging` สำเร็จ
- Lead time: เวลา commit ที่อยู่บน `develop` ถึงเวลา `deploy-staging` สำเร็จ
- Deployment frequency: นับ deployment staging ที่สำเร็จใน 7 วันที่ผ่านมา
- เมื่อมี run แรก ให้บันทึก URL, วันที่, commit SHA, job ที่ช้าที่สุด และจำนวน push ที่ใช้แก้ CI ในเอกสารนี้

## หลักฐานที่ยังต้องเก็บ

- URL ของ successful pipeline run และ staging deployment
- Screenshot ที่ `docs/screenshots/` ของ PR ที่ test ล้มเหลวและถูก branch protection บล็อก merge
- เวลาจริงของแต่ละ job และจำนวน push ที่ใช้แก้ pipeline
