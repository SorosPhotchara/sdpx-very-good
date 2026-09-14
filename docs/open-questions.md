# คำถามที่ requirement ยังตอบไม่ได้

> WS-02 homework ข้อ 4 · ที่มา: [prd.md](prd.md) (PRD v2.0, 2026-08-03)
>
> **สถานะ:** ร่าง — ทีมต้องตรวจ เลือก และหาคำตอบก่อนเขียน acceptance criteria
>
> เกณฑ์เลือก: **ถ้าตอบต่างกัน code ต้องเขียนต่างกัน** และยังไม่มีคำตอบใน PRD
> (คำถามที่อยู่ใน §17 Open Questions แล้ว จะไม่ยกมาซ้ำ ยกเว้นข้อที่ default ขัดกับ spec เอง)

---

## Q1 — Assignment เปิดให้ประเมินเมื่อไหร่ และ 2 deadline ปิดอย่างไร

**คำถาม:** สถานะ `OPEN` เริ่มเมื่อไหร่ และสถานะ `CLOSED` นับจาก deadline ไหน

**ทำไมยังตอบไม่ได้:**

| ที่ | บอกว่า |
|---|---|
| §7.3 state diagram | `PUBLISHED → OPEN` เมื่อ "ถึงเวลาเปิด" |
| FR-ASSIGN-01 และตาราง `assignment` (§11.1) | **ไม่มี field เวลาเปิด** มีแค่ `published_at` |
| FR-ASSIGN-01 | มี deadline แยก 2 ตัว: `group_deadline_utc`, `individual_deadline_utc` |
| §7.3 state diagram | มี status เดียว `OPEN → CLOSED` เมื่อ "ถึง deadline" |

**ถ้าไม่ตอบ AI จะเดา:** เพิ่ม field เวลาเปิดเองโดยไม่มีใครตั้งค่า หรือปิดทั้ง assignment ที่ deadline แรก
ทำให้ฝั่ง individual ปิดก่อนกำหนด — หรือปิดที่ deadline หลัง ทำให้ฝั่ง group รับคำตอบเกิน deadline (ขัด FR-EVAL-08)

**ทางเลือก**

| ทางเลือก | ผลต่อ code |
|---|---|
| เพิ่ม `opens_at_utc` และแยก status ต่อ side | schema ใหม่ 3 field · state machine 2 ชุด · scheduler เปิด/ปิดตามเวลา |
| Publish = เปิดทันที, status เดียว, ตรวจ deadline ต่อ side ตอน submit | ตัดสถานะ `PUBLISHED` ออกจาก flow จริง · `POST /submissions` เช็ค deadline ตาม side |
| Status เดียว `CLOSED` เมื่อผ่านทั้งสอง deadline | ต้องมี flag "side นี้ปิดแล้ว" แยกอยู่ดี · Finalize ได้หลัง deadline หลังเท่านั้น |

**ใครตัดสิน:** Instructor / Product · **ต้องรู้ก่อน:** ERD (field ของ `assignment`) และ OpenAPI schema ของ assignment

**สถานะ (14-Sep-2026):** ทีมยังไม่ตัดสิน รอถามอาจารย์ — [erd.md](erd.md) ใช้ field ตาม PRD ไปก่อน
และติดป้าย "Q1 pending" ไว้ที่ `assignment.status`

---

## Q2 — ห้องที่มี 2 กลุ่ม: default ของ OQ-8 ทำไม่ได้ทางคณิตศาสตร์

**คำถาม:** ถ้าทั้ง classroom มี 2 กลุ่ม ระบบควรทำอะไรกับ group evaluation

**ทำไมยังตอบไม่ได้:** §17 OQ-8 ตั้ง default ไว้ว่า "เตือนแต่ยังทำได้" แต่สูตรใน §8.2 บอกว่าทำไม่ได้:

```
N = 2 → P = C(2,2) = 1 คู่ คือ {A, B}
(1) k ≤ P − (N − 1) = 1 − 1 = 0
(3) R ≤ S − |A| − |B| = 0     ← นักศึกษาทุกคนอยู่ A หรือ B จึงไม่มีใครมีสิทธิ์ประเมินคู่นี้
```

FR-PAIR-05 ให้ลด R ลงจนผ่าน → ได้ **R = 0** → ไม่มี comparison ฝั่ง group เลย
แล้วสูตร q ใน §9.2 จะเป็น 0 / 0

**ถ้าไม่ตอบ AI จะเดา:** ทำตาม default แล้ว publish ได้ scoring engine หารด้วยศูนย์
(ได้ `NaN` หรือ crash) หรือแอบตั้ง q = 0 ทำให้ทั้งสองกลุ่มได้ floor 60% โดยไม่มีใครประเมินเลย

**ทางเลือก**

| ทางเลือก | ผลต่อ code |
|---|---|
| ห้าม publish ฝั่ง group เมื่อ R = 0 (บังคับ `group_max_score = 0`) | publish validation + ข้อความอธิบายเป็นตัวเลขตาม FR-PAIR-05 |
| ให้อาจารย์เป็นผู้ประเมินฝั่ง group คนเดียว (`INSTRUCTOR_SELF`) | feasibility ต้องรู้จัก evaluator ที่เป็น instructor · min_comparisons ต้องนับ instructor (ดู Q3) |
| ปิด group evaluation อัตโนมัติ เหลือแต่ individual | ต้องแยกสถานะ "side ปิดเพราะ infeasible" ออกจาก `group_max_score = 0` |

**ใครตัดสิน:** Product (ตาม OQ-8) · **ต้องรู้ก่อน:** unit brief ของ `pairing-engine` — ต้องแก้ default ใน §17 ด้วย

---

## Q3 — Comparison ของอาจารย์นับเข้าเกณฑ์ขั้นต่ำหรือไม่

**คำถาม:** เมื่ออาจารย์ประเมินเอง ("ประเมินเอง" / "ส่งประเมินเพิ่ม") comparison นั้นนับเข้าเกณฑ์ต่อไปนี้หรือไม่ และนับเป็น 1 หรือเท่ากับ `instructor_weight`

| เกณฑ์ | ที่ | PRD บอกว่านับอะไร |
|---|---|---|
| `min_comparisons` (default 3) → flag `LOW_CONFIDENCE` | FR-SCORE-05 | "comparison" — ไม่ระบุว่ารวมของอาจารย์ไหม |
| `k_min` (default 3) → ซ่อนคะแนน individual | FR-ANON-02 | "ผู้ประเมินที่ submit แล้ว" — ไม่ระบุ |
| Coverage balance ≤ 1 | FR-PAIR-06 | ไม่ระบุว่า pair ที่ `source = INSTRUCTOR_*` นับไหม |

ตาราง `computed_score` มีทั้ง `comparison_count` และ `effective_weight_sum` แยกกัน
แต่ไม่มีข้อไหนบอกว่าเกณฑ์ใช้ตัวไหน

**ตัวอย่างที่ผลต่างกัน:** กลุ่ม 4 คน → coverage = m − 2 = 2 → ทุกคนต่ำกว่า `min_comparisons = 3`
ถ้าอาจารย์ประเมินเพิ่ม 1 ครั้ง (`instructor_weight = 3`):

- นับเป็นจำนวน → 3 ครั้ง ผ่านเกณฑ์
- นับเฉพาะนักศึกษา → ยัง 2 ครั้ง ติด `LOW_CONFIDENCE` ตลอดไป ไม่ว่าอาจารย์จะช่วยแค่ไหน
- นับตาม weight → 2 + 3 = 5 ผ่าน

และถ้านับอาจารย์เข้า `k_min` นักศึกษาจะเห็นคะแนนเมื่อมีเพื่อนประเมินแค่ 2 คน — anonymity อ่อนลง (R3)

**ทางเลือก**

| ทางเลือก | ผลต่อ code |
|---|---|
| นับทุก comparison เป็น 1 | ใช้ `comparison_count` ตรง ๆ |
| นับตาม weight | เกณฑ์เทียบกับ `effective_weight_sum` |
| นับเฉพาะนักศึกษา (อย่างน้อยสำหรับ `k_min`) | ต้องเก็บ count แยกตามประเภท evaluator |

**ใครตัดสิน:** Instructor + Privacy officer · **ต้องรู้ก่อน:** unit brief ของ `scoring-engine` และ M3 (anonymity)

---

## Q4 — กลุ่มที่มีสมาชิก < 2 คน: reject หรือเตือน

**คำถาม:** ตอน import roster ถ้ามีกลุ่มที่มีสมาชิก 1 คน ระบบควร reject ทั้งไฟล์ หรือบันทึกแล้วเตือน

**ทำไมยังตอบไม่ได้:**

| ที่ | บอกว่า |
|---|---|
| FR-CLASS-02 | ถ้ามีแถวใดผิด ให้ reject ทั้งไฟล์ |
| FR-CLASS-03 | ต้องตรวจ "กลุ่มที่มีสมาชิก < 2" แต่ AC ใช้คำว่า "รายงาน**เตือน**" |

กลุ่ม 1 คนทำให้ individual eval ของคนนั้นไม่มีผู้ประเมิน (coverage = m − 2 < 0 ใน §8.3)

**ถ้าไม่ตอบ AI จะเดา:** reject → อาจารย์ที่ตั้งใจให้บางคนทำงานเดี่ยว import ไม่ได้เลย ·
เตือนแต่บันทึก → ไปพังตอน publish / pairing โดยอาจารย์ไม่ทันเห็นคำเตือน

**ทางเลือก**

| ทางเลือก | ผลต่อ code |
|---|---|
| Reject เหมือน error อื่น | validator เดียว · ต้องมีทางอื่นให้ทำงานเดี่ยว |
| บันทึกได้ แต่ต้องกดยืนยันคำเตือนก่อน | import 2 ขั้น (preview → confirm) · ต้องเก็บผล parse ระหว่างขั้น |
| บันทึกได้ แล้วไป block ตอน publish | validation ย้ายไป publish · ปิด individual side ของกลุ่มนั้น |

**ใครตัดสิน:** Instructor / Product · **ต้องรู้ก่อน:** US-CLASS-01 ใน [user-stories.md](user-stories.md)

---

## Q5 — Import ซ้ำเข้า classroom ที่มี roster อยู่แล้ว

**คำถาม:** Upsert (FR-CLASS-05) เป็นแค่ Should — ถ้า MVP ยังไม่มี แล้วอาจารย์ import ไฟล์ที่สองเข้า classroom เดิม ควรเกิดอะไร

**ถ้าไม่ตอบ AI จะเดา:** replace → ลบ `group_id` ที่ pair และ evaluation ผูกอยู่ ข้อมูลที่เก็บมาเสียเปล่า (R8) ·
append → ชน `UNIQUE (classroom_id, user_id)` ได้ 500

**ทางเลือก**

| ทางเลือก | ผลต่อ code |
|---|---|
| Reject ถ้ามี roster แล้ว — ให้แก้ทีละคน | ง่ายสุด · ต้องมี UI แก้รายคน |
| Replace ได้เฉพาะเมื่อยังไม่มี assignment ที่ publish | ตรวจสถานะ assignment ก่อน import · ลบ + สร้างใหม่ใน transaction |
| ทำ upsert (FR-CLASS-05) ใน MVP เลย | ต้องมี diff + confirm · เลื่อน scope ขึ้นมาเป็น Must |

**ใครตัดสิน:** Product · **ต้องรู้ก่อน:** US-CLASS-01 และ FR-PAIR-11

---

## Q6 — อีเมลใน CSV ที่ไม่ควรเป็นนักศึกษา

**คำถาม:** ตอน import ถ้าเจออีเมลต่อไปนี้ ควร reject แถวหรือแค่เตือน

- อีเมลนอก `allowed_email_domains` ของ classroom (FR-AUTH-02)
- อีเมลของคนที่เป็น Owner / Co-teacher / TA ใน classroom นี้อยู่แล้ว

**ถ้าไม่ตอบ AI จะเดา:** ยอมรับทั้งหมด → นักศึกษา login ไม่ได้เพราะติด `hd` ·
TA ถูก insert เป็น STUDENT แล้วชน `UNIQUE (classroom_id, user_id)` หรือได้ไปประเมินเพื่อน

**ทางเลือก**

| ทางเลือก | ผลต่อ code |
|---|---|
| Reject แถวทั้งสองกรณี | validator ต้องอ่าน config domain และ member เดิมของ classroom |
| เตือนกรณี domain, reject กรณี staff | รายงานต้องแยก error กับ warning |

**ใครตัดสิน:** Instructor · **ต้องรู้ก่อน:** US-CLASS-01 · เกี่ยวกับคำถามสำรองเรื่อง "Domain ที่อนุญาตตรวจตอนไหน"

---

## คำถามสำรอง

ใช้แทนข้อบนได้ หรือเปิดเป็น issue แยก:

- **Domain ที่อนุญาตตรวจตอนไหน:** FR-AUTH-02 ให้ตั้ง `hd` ต่อ classroom แต่ login เกิดก่อนรู้ว่าจะเข้า classroom ไหน —
  ตรวจตอน login (ใช้ list ของทุก classroom รวมกัน?) หรือตรวจตอนเข้าถึงแต่ละ classroom
- **นักศึกษาเห็นคะแนนกลุ่มตัวเองเมื่อไหร่:** FR-REPORT-06 ไม่ระบุเวลา ส่วน FR-ANON-02/03 ใช้กับคะแนน individual เท่านั้น —
  คะแนนกลุ่มแบบ interim แสดงระหว่าง `OPEN` ได้ไหม และห้ามแสดง delta เหมือน individual หรือไม่
- **Re-submit ด้วยคำตอบที่น้อยลง:** ถ้า submit ครั้งแรกตอบ 10 คู่ แล้ว re-submit ตอบ 8 คู่ (FR-EVAL-06) —
  2 คู่ที่หายไปยังนับเป็น SUBMITTED ค่าเดิม หรือกลายเป็นไม่ได้ตอบ (มีผลต่อ `p` ใน §9.4)
- **Vercel ผ่าน C1 ไหม:** C1 บังคับให้ deploy บน infrastructure ของมหาวิทยาลัยหรือ cloud ที่ผ่านการอนุมัติ — ต้องถามอาจารย์

---

## คำถามจากร่างแรก (อิง PRD v1.1) — PRD v2.0 ตอบแล้ว

| คำถามเดิม | v2.0 ตอบที่ |
|---|---|
| ปุ่มประเมิน 5 หรือ 6 ระดับ | D1, FR-EVAL-03, §9.1 — 6-point forced choice |
| Individual coverage 5 ครั้งเป็นไปไม่ได้ | D4, §8.3 — coverage = m − 2 |
| Normalize ผลรวม = 1.0 | D2, §9.3 — band mapping |
| Submit แล้วแก้ได้ไหม | FR-EVAL-06 — re-submit ได้ไม่จำกัด |
| Partial credit vs ไม่ submit = 0 | D5, §9.4 — participation multiplier |
| Raw export มีชื่อ evaluator ไหม | FR-EXPORT-03/04 — pseudonym เป็น default |
| เปลี่ยนกลุ่มหลัง publish | FR-PAIR-11 — unpublish → แก้ → publish ใหม่ |
| แก้ assignment ได้ถึงเมื่อไหร่ | FR-ASSIGN-03 — เฉพาะสถานะ `DRAFT` |
| แจ้งเตือนช่องทางไหน | §6, §7.9 — email |
