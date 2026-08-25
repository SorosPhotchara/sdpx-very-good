# Test Plan — PairEval

> The rules below are lifted from the *Key Business Rules* sections of
> `memory-bank/units/*/unit-brief.md`. Every rule written there gets a line
> here, and every line here gets a test.
>
> `project/TEST_PLAN.md` is a different thing: the room-booking warm-up from the
> WS-03 handout. It is not PairEval.

## How to run

```bash
pytest                                  # all three suites, ~0.5s
pytest backend/tests                    # the PairEval engines only
cd frontend && npx playwright test      # E2E smoke, ~3s
```

---

## Functions ที่ต้อง Test

### 1. `pairing.solve_group_feasibility()` — §8.2

- [x] ห้องใหญ่ (S=200, N=10) → coverage 5, workload 2 ตามตัวอย่างที่ 1
- [x] ห้องเล็ก (S=12, N=3) → coverage ลดเหลือ 4, workload 1 ตามตัวอย่างที่ 2
- [x] coverage ที่ถูกลด → เหตุผลต้องมีตัวเลข ไม่ใช่คำเตือนลอย ๆ (FR-PAIR-05)
- [x] constraint (1) — workload เกินจำนวนคู่ที่ประเมินได้ → ลด R
- [x] constraint (2) — `max_workload` เป็นตัวคุม → ลด R
- [x] constraint (3) — คู่ที่มีผู้มีสิทธิ์ประเมินน้อยที่สุดเป็นตัวคุม → ลด R
- [x] กลุ่มเดียว → `PairingInfeasibleError`
- [x] 2 กลุ่ม → `PairingInfeasibleError` (ไม่มีใครมีสิทธิ์ประเมิน, OQ-8)
- [x] ห้องว่าง → `PairingInfeasibleError`

### 2. `pairing.generate_group_pairs()` — §8.4, INV-1…INV-5

- [x] INV-1 — ไม่มีใครได้ pair ที่มีกลุ่มตัวเอง (FR-PAIR-02)
- [x] INV-2 — ไม่มีใครได้ pair เดิมซ้ำใน criterion เดียวกัน (FR-PAIR-07)
- [x] INV-3 — coverage ต่างกันไม่เกิน 1 (FR-PAIR-06)
- [x] INV-4 — workload ต่างกันไม่เกิน 1
- [x] INV-5 — seed เดิม → ผลเดิมเป๊ะ (FR-PAIR-09)
- [x] seed ต่าง → ผลต่าง
- [x] บันทึกตำแหน่งซ้าย/ขวาที่แสดงจริง และสุ่มจริง (FR-PAIR-08/D8)
- [x] ส่ง criterion ฝั่ง INDIVIDUAL มาให้ → `ValueError`
- [x] **property-based** — INV-1…INV-5 ทนต่อห้องสุ่ม 3–8 กลุ่ม × 3–8 คน × R 1–6 (NFR-MAINT-02)

### 3. `pairing.individual_plan()` / `generate_individual_pairs()` — §8.3

- [x] ตาราง m = 3,4,5,6,7 ตรงกับ PRD ทุกช่อง (D4)
- [x] m ≤ 2 → ไม่มีการประเมินรายบุคคล (FR-PAIR-12)
- [x] m = 3 → flag LOW_CONFIDENCE เสมอ (FR-PAIR-13)
- [x] `C(m−1,2) > k_max` → ตัดคู่และรายงาน coverage ที่ลดลง (FR-PAIR-14)
- [x] ไม่มีใครได้ pair ที่มีตัวเองอยู่ (FR-PAIR-03)
- [x] pair อยู่ในกลุ่มเดียวเท่านั้น
- [x] ส่งสมาชิกข้ามกลุ่มมา → `ValueError`

### 4. `scoring.points_for_items()` — §9.1

- [x] ทุกตัวเลือกแบ่ง 1 คะแนนพอดี
- [x] ไม่มีตัวเลือกไหนแบ่ง 50/50 — ไม่มีตัวกลาง (D1)
- [x] คะแนนตามตำแหน่งที่แสดงจริง ไม่ใช่ลำดับที่เก็บ (FR-PAIR-08)

### 5. `scoring.compute_quality_index()` — §9.2

- [x] q = weighted mean ของคะแนนที่ item ได้รับ
- [x] DRAFT / EXCLUDED ไม่เข้าการคำนวณ (DR-01)
- [x] instructor weight เป็น float ไม่ใช่ vote ซ้ำ และ comparison count ไม่เฟ้อ (D6)
- [x] comparison < `min_comparisons` → LOW_CONFIDENCE (FR-SCORE-05)
- [x] ไม่มี comparison เลย → q = None ไม่ใช่ 0

### 6. `scoring.score_ratio()` / `compute_component()` — §9.3

- [x] q=0 → floor, q=1 → ceiling, q=0.5 → กึ่งกลาง
- [x] ไม่ normalize ให้ผลรวม = 1 (D2)
- [x] q นอกช่วง [0,1] → `ScoringError` ไม่ใช่ clamp
- [x] น้ำหนัก criteria ไม่ครบ 100% → `ScoringError` (FR-ASSIGN-02)
- [x] ฝั่งที่ไม่มี criteria = ปิดใช้งาน ไม่ใช่ผิด (FR-ASSIGN-07)
- [x] criteria ของอีกฝั่งถูกข้าม

### 7. `scoring` — golden test จาก §9.5

- [x] กลุ่ม Aurora = **12.798 / 15**
- [x] นก (ประเมินครบ) = **16.93 / 20**
- [x] ต้น (ส่ง 9 จาก 15) = **10.97 / 20**

### 8. `scoring.participation_multiplier()` / `final_personal_score()` — §9.4

- [x] p ≥ threshold → M = 1
- [x] คนที่ไม่ได้รับมอบหมายอะไรเลย → ไม่ถูกลงโทษ (p = 1)
- [x] ส่งมากกว่าที่ได้รับมอบหมาย → `ScoringError`
- [x] **คะแนนกลุ่มไม่ลดตาม M ของสมาชิกคนใดคนหนึ่ง** (FR-SCORE-11/D5)

### 9. `roster.parse_roster_csv()` / `normalize_email()` — §7.2

- [x] roster address กับ login address ของคนเดียวกันจับคู่ได้ (FR-AUTH-03)
- [x] ตัวพิมพ์ / จุด / `+tag` ถูกตัดทิ้ง
- [x] อีเมลผิดรูปแบบ → reject
- [x] header ไม่สนตัวพิมพ์และช่องว่าง (FR-CLASS-01)
- [x] แถวเดียวพัง → ทั้งไฟล์ถูก reject (FR-CLASS-02)
- [x] รายงานเลขบรรทัดที่พัง
- [x] รายงาน error ทุกข้อพร้อมกัน
- [x] อีเมลซ้ำถูกจับหลัง normalize
- [x] `group_name` ว่าง → error
- [x] กลุ่มมีสมาชิกคนเดียว → warn แต่ import ผ่าน (FR-CLASS-03)
- [x] บรรทัดว่างท้ายไฟล์ไม่นับเป็น error
- [x] header ขาด / ไฟล์ว่าง → `RosterImportError`
- [x] เซลล์ที่ Excel จะรันเป็นสูตร ถูกทำให้ไม่ทำงาน (FR-SEC-04)

### 10. `services.AssignmentService`

- [x] fake repo ผ่าน Protocol เดียวกับของจริง
- [x] publish รายงาน coverage ที่จะใช้จริง (FR-PAIR-04)
- [x] publish สร้าง pair ครบทุก group criterion
- [x] `individual_max_score = 0` → ไม่สร้าง individual pair เลย (FR-ASSIGN-07)
- [x] กลุ่ม 2 คน → รายงานว่าไม่มีการประเมินรายบุคคล พร้อมเหตุผล (FR-PAIR-12)
- [x] ห้องว่าง → refuse
- [x] น้ำหนักไม่ครบ 100% → บล็อกตั้งแต่ก่อนสร้าง pair
- [x] final score คูณด้วย participation
- [x] ไม่มี comparison repo → error ดัง ๆ ไม่ใช่เงียบ
- [x] item ที่ไม่มีใครประเมิน → flag ไม่ใช่ให้ 0

### 11. E2E (Playwright) — `frontend/tests/e2e/smoke.spec.ts`

- [x] หน้าแรกโหลดได้และมี title `PairEval`
- [x] main navigation มองเห็นได้ (ผ่าน `getByRole`)
- [x] main CTA กดได้
- [x] backend ล่ม → หน้ายังเรนเดอร์ และแสดง `offline`
- [x] จอกว้าง 320 px → ใช้งานได้ ไม่ scroll แนวนอน (NFR-COMPAT-02)

---

## กฎที่ยังไม่มี test (ยอมรับไว้ชั่วคราว)

| กฎ | เหตุผลที่ยังไม่ทำ | จะทำเมื่อไหร่ |
|---|---|---|
| FR-AUTHZ-01/02 — ตรวจสิทธิ์ฝั่ง server ทุก endpoint | ยังไม่มี role model และไม่มี auth layer (TD-02) | ก่อน M1 — §19 บอกว่าห้ามตัด |
| FR-ANON-01/02/03 — k-anonymity และห้ามแสดง delta | ยังไม่มีตาราง `comparison` ให้ query (TD-01) | ก่อน M3 |
| FR-AUDIT-01/02/03 — audit log | ยังไม่มีตาราง (TD-03) | ก่อน M3 — §19 บอกว่าห้ามตัด |
| FR-EVAL-04/06 — autosave, re-submit | ยังไม่มีหน้า evaluation | ก่อน M2 |
| FR-PAIR-10 — "ส่งประเมินเพิ่ม" | engine ทิ้ง `already` bookkeeping หลังจัดสรรเสร็จ ต้องเก็บก่อน | ก่อน M2 |
| FR-PAIR-11 — เปลี่ยนกลุ่มหลัง publish | ยังไม่ตัดสินว่า comparison เก่าจะเป็นอย่างไร (`docs/open-questions.md` Q3) | หลังได้คำตอบ |
| FR-CLASS-05 — CSV upsert พร้อม diff | ผูกกับ FR-PAIR-11 | ก่อน M2 |
| QS-01…QS-07 — quality signals | ต้องมีข้อมูลจริง 1 ภาคเรียนก่อนตั้งเกณฑ์ | M3 |
| NFR-PERF-01…05 — load test (k6) | ยังไม่มี staging ให้ยิง | หลังปิด deploy loop |
| FR-A11Y-01…07 — a11y scan | มีแค่ landing page ให้ scan · E2E ตรวจ role/label ไปแล้วบางส่วน | เมื่อมีหน้า evaluation |
| BUG-01 — `Float` ในตาราง assignment ขัด DR-04 | ต้อง migration | ก่อน M2 |

---

## Fidelity Check (WS-03)

วิธีทำ: ทำลายกฎทีละข้อในโค้ด → รัน `pytest` → ดูว่ามี test แดงไหม → คืนค่าเดิม
สคริปต์: `scratchpad/fidelity.py` (ไม่ commit — เป็นเครื่องมือชั่วคราว)

**ผล: 11 / 11 mutations ถูกจับได้**

| # | กฎที่ลบ | test ที่แดง | ผล |
|---|---|---|---|
| 1 | FR-PAIR-08/§9.1 — อ่านคะแนนตามลำดับที่เก็บ แทนตำแหน่งที่แสดง | `test_points_follow_the_displayed_position_not_the_stored_item_order` | ✅ 1 แดง |
| 2 | DR-01 — ปล่อยให้ DRAFT/EXCLUDED เข้าการคำนวณ | `test_draft_and_excluded_comparisons_never_reach_a_score` | ✅ 1 แดง |
| 3 | D2/§9.3 — ตัด floor ของ band mapping | `test_band_mapping_*` + golden ทั้ง 3 ตัว | ✅ 6 แดง |
| 4 | FR-SCORE-05 — เลิก flag LOW_CONFIDENCE | `test_item_below_min_comparisons_is_flagged_low_confidence` ฯลฯ | ✅ 3 แดง |
| 5 | INV-1/FR-PAIR-02 — ให้ประเมินกลุ่มตัวเองได้ | `test_no_evaluator_is_ever_asked_to_judge_their_own_group` + property test | ✅ 2 แดง |
| 6 | INV-2/FR-PAIR-07 — ให้ประเมิน pair เดิมซ้ำได้ | `test_no_evaluator_receives_the_same_pair_twice_in_one_criterion` + property test | ✅ 2 แดง |
| 7 | INV-5/FR-PAIR-09 — seed แบบสุ่มจริง | `test_the_same_seed_reproduces_the_identical_allocation` + property test | ✅ 2 แดง |
| 8 | §8.2 constraint (3) — ไม่สนจำนวนผู้มีสิทธิ์ประเมินต่อคู่ | `test_coverage_is_capped_by_how_many_people_may_judge_the_hardest_pair` | ✅ 1 แดง |
| 9 | FR-CLASS-02 — import แถวที่ดีแทนที่จะ reject ทั้งไฟล์ | `test_one_bad_row_rejects_the_entire_file` | ✅ 1 แดง |
| 10 | FR-AUTH-03 — เลิกตัดจุดและ `+tag` | `test_roster_address_and_login_address_resolve_to_the_same_person` ฯลฯ | ✅ 6 แดง |
| 11 | FR-SEC-04 — เลิกกัน formula injection | `test_cells_that_excel_would_execute_are_defused` ฯลฯ | ✅ 5 แดง |

### ช่องโหว่ที่ fidelity check หาเจอ

รอบแรกได้ **10/11** — mutation ข้อ 8 (§8.2 constraint 3) **รอดไปได้ ไม่มี test แดงเลย**

สาเหตุ: ทุกเคสที่มีอยู่ตอนนั้น ถูก constraint (1) ตัดก่อนเสมอ จึงไม่เคยมีเคสไหน
ที่ constraint (3) เป็นตัวตัดสิน — coverage report บอกว่าบรรทัดนั้น "ถูกรัน" แล้ว
แต่ไม่มีใครยืนยันว่ามัน *ทำอะไร*

แก้โดยเพิ่ม `test_coverage_is_capped_by_how_many_people_may_judge_the_hardest_pair`
(กลุ่มขนาด 10, 10, 1, 1, 1 — คู่ของสองกลุ่มใหญ่เหลือผู้มีสิทธิ์ประเมินแค่ 3 คน)
แล้วรันใหม่ได้ **11/11**

> นี่คือเหตุผลที่ coverage % ไม่ใช่ตัวชี้วัดคุณภาพ test —
> บรรทัดนั้นมี coverage 100% มาตลอด แต่ไม่มีอะไรคุ้มครองมันเลย

### ช่องโหว่ที่ property test หาเจอ (ระหว่างเขียน)

| รอบ | สิ่งที่พัง | สาเหตุจริง |
|---|---|---|
| 1 | `PairingInfeasibleError` ในห้องที่ควรจัดได้ (4+4+2) | allocator แจก quota ก่อนดู eligibility — สมาชิกกลุ่มเล็กซึ่งเป็นคนเดียวที่ประเมินคู่ของสองกลุ่มใหญ่ได้ กลับได้ quota 0 |
| 2 | INV-4 พัง spread = 2 (N=5, m=5) | greedy อย่างเดียวไปติด local optimum ปลายรอบ |
| 3 | INV-4 ยังพังที่ 300 examples (N=4, m=6) | ย้ายงานตรง ๆ ทีละคู่ยังไม่พอ ต้องหา augmenting chain |

ทั้งสามข้อเป็น bug จริงในโค้ด ไม่ใช่ test เขียนผิด — และไม่มีข้อไหนที่
example-based test จับได้ เพราะทั้งสามเคสอยู่นอกรูปห้องที่ PRD ยกตัวอย่างไว้

---

## Loop latency

วัดบนเครื่อง dev (Linux, Python 3.14.4) รัน 3 ครั้งเอาค่าที่เสถียร

| Loop | คำสั่ง | เวลา | จำนวน test |
|---|---|---|---|
| ไฟล์เดียว (แคบที่สุด) | `pytest backend/tests/unit/test_scoring.py` | **0.24 s** | 22 |
| engine ทั้งหมด | `pytest backend/tests` | **0.47 s** | 95 |
| ทั้ง repo | `pytest` | **0.48 s** | 106 |
| E2E | `npx playwright test` | **~2.8 s** | 5 |

**เกณฑ์ของวิชาคือ < 10 วินาที — ผ่านสบาย ๆ ที่ 0.48 วินาที**

เหตุผลที่เร็วขนาดนี้ไม่ใช่เพราะ test น้อย แต่เพราะ pairing/scoring engine เป็น
pure function ที่ไม่แตะ database, ไม่แตะนาฬิกา, ไม่มี global (AR-01) —
property test ยิงห้องเรียนสุ่มเป็นพัน ๆ ห้องได้ในเวลาไม่ถึง 2 วินาที

**สิ่งที่จะทำให้ช้าลง:** เมื่อทำ TD-01 (ตาราง `comparison`) แล้ว test ที่แตะ
database จะเข้ามา ต้องแยก `pytest -m "not db"` ไว้เป็น loop ชั้นในตั้งแต่วันแรก
ไม่ใช่รอจนช้าแล้วค่อยแก้

---

## Coverage

```bash
python3 -m coverage run -m pytest && python3 -m coverage html && rm -f docs/coverage/.gitignore
```

รายงาน: [`docs/coverage/index.html`](docs/coverage/index.html)

| Module | Coverage | หมายเหตุ |
|---|---:|---|
| `app/roster.py` | 100% | |
| `app/repositories.py` | 100% | |
| `app/services.py` | 96% | |
| `app/scoring.py` | 95% | |
| `app/pairing.py` | 93% | ที่ขาดคือ error path ของห้องที่จัดไม่ได้จริง ๆ |
| `app/domain.py` | 84% | validation branch ใน `__post_init__` |
| `app/crud.py` · `models.py` · `schemas.py` · `utils.py` | **0%** | ชั้น ORM ยังไม่มี test เลย |
| **รวม** | **75%** | |

ตัวเลข 75% นี้ **ไม่ใช่เป้าหมาย** สิ่งที่สำคัญคือ 0% สามก้อนล่าง —
ชั้น ORM และ CRUD ยังไม่มีอะไรคุ้มครองเลย ซึ่งเป็นที่ที่ BUG-01 (`Float` แทน
`Numeric`) และ BUG-02 (`orm_mode` ของ Pydantic v1) นอนรออยู่
