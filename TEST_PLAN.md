# Test Plan: Pairwise

ที่มาของกฎ: section *Key Business Rules* ใน `memory-bank/units/*/unit-brief.md` (WS-02)
— ทุกกฎมีบรรทัดของตัวเองที่นี่ และชื่อ test ใช้ตามคอลัมน์ "Planned test" ของ unit-brief
เพื่อให้ test ที่แดงชี้กลับไปหากฎได้ทันที

สถานะ: ✅ มี test และผ่าน · 🟡 กำลังทำใน WS-03 lab · ⬜ ยังไม่ทำ (ดู "กฎที่ยังไม่มี test")

> ชื่อ function ด้านล่างเป็นชื่อที่ **เสนอ** — ยังไม่มี domain code (unit-brief: "No code exists yet")
> Unit tests ของ engine ใช้ Python + pytest ตามแผน backend (FastAPI) ใน `memory-bank/standards/tech-stack.md`

---

## Functions ที่ต้อง Test

### 1. Roster Import — `parse_roster(csv_text) -> RosterResult` 🟡

เป้าหมายของ WS-03 lab (Simple Construction — กฎเยอะแต่ตื้น ทำเสร็จใน 60 นาทีได้)

| กฎ | Test | สถานะ |
|---|---|---|
| ที่อยู่ใน roster กับที่อยู่ตอน login ของคนเดียวกันต้อง match (FR-AUTH-03) | `test_roster_address_and_login_address_resolve_to_the_same_person` | 🟡 |
| ตัวพิมพ์ใหญ่และ `+tag` ถูกตัดทิ้งตอน normalise | `test_case_and_plus_tags_are_folded_away` | 🟡 |
| อีเมลที่ไม่สมเหตุสมผลถูกปฏิเสธ ไม่ถูกเก็บ | `test_implausible_addresses_are_rejected` | 🟡 |
| Header match ได้ไม่ว่าตัวพิมพ์หรือช่องว่างรอบ ๆ (FR-CLASS-01, US-CLASS-01 AC1) | `test_header_matching_ignores_case_and_surrounding_space` | 🟡 |
| **แถวผิด 1 แถว → ปฏิเสธทั้งไฟล์ (FR-CLASS-02)** | `test_one_bad_row_rejects_the_entire_file` | 🟡 |
| Error บอกเลขแถวตามที่ Excel แสดง — แถว 42 ในไฟล์ 100 แถว (US-CLASS-01 AC2) | `test_a_rejected_file_names_the_row_that_broke_it` | 🟡 |
| รายงาน error ทุกข้อพร้อมกัน ไม่ใช่ทีละรอบ upload | `test_every_error_is_reported_at_once_rather_than_one_upload_at_a_time` | 🟡 |
| ตรวจอีเมลซ้ำ **หลัง** normalise (FR-CLASS-03) | `test_duplicate_emails_are_caught_after_normalisation_not_before` | 🟡 |
| `group_name` ว่าง → error ไม่ใช่ค่า default | `test_an_empty_group_name_is_an_error_not_a_default` | 🟡 |
| บรรทัดว่างถูกข้าม และเลขแถวถัดไปยังตรงกับ Excel | `test_blank_lines_are_skipped_without_shifting_row_numbers` | 🟡 |
| ขาด header ที่บังคับ → หยุด import ทันที | `test_a_missing_required_header_stops_the_import_immediately` | 🟡 |
| Cell ที่ Excel จะ execute ถูกทำให้ไร้พิษ (FR-SEC-04) | `test_cells_that_excel_would_execute_are_defused` | 🟡 |
| สูตรใน group name ผ่าน import ออกมาเป็นข้อความเฉย ๆ | `test_a_formula_in_a_group_name_survives_import_as_inert_text` | 🟡 |

### 2. Publish service — `publish(assignment_id)` (ใช้ `AssignmentRepo`) 🟡

Service บาง ๆ ที่อ่าน roster จาก repo → เรียก Pairing Engine → บันทึก `pair_assignment` กลับลง repo
เป็นจุดที่ใช้ Fake Repository ของ harness

| กฎ | Test | สถานะ |
|---|---|---|
| จำนวน pair ที่สร้างเท่ากับยอดที่ preview ไว้ (US-PUBLISH-01 AC1) | `test_publish_generates_exactly_the_previewed_number_of_pairs` | 🟡 |

### 3. Scoring Engine ⬜

**`choice_points(choice, display_left_item_id, …)`** — §9.1

| กฎ | Test | สถานะ |
|---|---|---|
| ทุก choice แบ่ง 1 แต้มพอดีระหว่าง 2 item (§9.1) | `test_every_choice_splits_exactly_one_point_between_the_two_items` | ⬜ |
| ไม่มีตัวเลือกกลาง — ไม่มี choice ไหนแบ่ง 50/50 (D1) | `test_scale_has_no_neutral_option_so_no_choice_splits_the_point_evenly` | ⬜ |
| แต้มตามตำแหน่งที่ *แสดง* ไม่ใช่ลำดับที่เก็บ (FR-PAIR-08) | `test_points_follow_the_displayed_position_not_the_stored_item_order` | ⬜ |

**`quality_index(comparisons, …)`** — §9.2

| กฎ | Test | สถานะ |
|---|---|---|
| `q` = weighted mean ของแต้มที่ item ได้ (§9.2) | `test_quality_index_is_the_weighted_mean_of_the_points_an_item_received` | ⬜ |
| คิดเฉพาะคำตอบที่ submit แล้ว เวอร์ชันล่าสุด; draft และ `EXCLUDED` ไม่นับ (DR-01, FR-EVAL-06) | `test_only_the_latest_submitted_version_of_each_answer_is_scored` | ⬜ |
| น้ำหนักอาจารย์เป็น float ใน mean ไม่ใช่โหวตซ้ำ (D6) | `test_instructor_weight_shifts_the_mean_without_inflating_the_comparison_count` | ⬜ |
| ต่ำกว่า `min_comparisons` (default 3) → `LOW_CONFIDENCE` (FR-SCORE-05) | `test_item_below_min_comparisons_is_flagged_low_confidence` | ⬜ |
| ไม่มี comparison → ไม่มี `q` และไม่มีคะแนน ไม่ใช่ศูนย์ | `test_item_with_no_comparisons_has_no_quality_index_rather_than_zero` | ⬜ |

**`band_score(q, score_floor, score_ceiling)` และผลรวม** — §9.3 (default floor 0.600, ceiling 1.000)

| กฎ | Test | สถานะ |
|---|---|---|
| ผลรวมที่ยังมี criterion ไม่มีคะแนน → `None` ไม่ใช่ผลรวมบางส่วน | `test_a_total_is_unknown_while_any_criterion_has_no_score` | ⬜ |
| q=0 → floor, q=1 → ceiling (§9.3) | `test_band_mapping_puts_q_zero_at_the_floor_and_q_one_at_the_ceiling` | ⬜ |
| ไม่ normalise ให้ผลรวม = 1 (D2) | `test_band_mapping_never_normalises_scores_to_sum_to_one` | ⬜ |
| `q` นอก [0, 1] ถูกปฏิเสธ ไม่ถูก clamp | `test_quality_index_outside_zero_to_one_is_rejected_rather_than_clamped` | ⬜ |

**`validate_criteria_weights(side)`** — FR-ASSIGN-02, FR-ASSIGN-07

| กฎ | Test | สถานะ |
|---|---|---|
| น้ำหนักรวมต้อง 100% ± 0.01 ต่อ side: 99.99 ผ่าน, 99.98 ไม่ผ่าน (US-ASSIGN-01) | `test_criteria_weights_must_total_one_hundred_percent` | ⬜ |
| Side ที่ max score = 0 ไม่มี criteria และถูกข้าม | `test_a_side_with_max_score_zero_is_switched_off_rather_than_invalid` | ⬜ |

**`participation_multiplier(p, completion_threshold)`** — §9.4 (default threshold 0.900)

| กฎ | Test | สถานะ |
|---|---|---|
| `M = min(1, p / threshold)` ใช้กับคะแนนส่วนตัวเท่านั้น | `test_participation_at_or_above_the_threshold_gives_a_full_multiplier` | ⬜ |
| นักศึกษาที่ไม่ได้รับงานเลยไม่ถูกหักคะแนน | `test_a_student_who_was_assigned_nothing_is_not_penalised` | ⬜ |
| Submit มากกว่าที่ได้รับเป็นข้อมูลที่เป็นไปไม่ได้ → ปฏิเสธ | `test_submitting_more_than_assigned_is_rejected_as_impossible_data` | ⬜ |
| **การขาดของสมาชิกไม่ลดคะแนนกลุ่ม (FR-SCORE-11, D5)** | `test_a_members_missing_participation_does_not_reduce_the_group_score` | ⬜ |

**Golden tests — PRD §9.5 worked example (NFR-MAINT-01)**

| Case | Expected | Test | สถานะ |
|---|---|---|---|
| Group Aurora | 12.798 / 15 | `test_golden_group_aurora_scores_12_798_out_of_15` | ⬜ |
| นก, ประเมินครบ | 16.93 / 20 | `test_golden_student_nok_who_evaluated_everything_scores_16_93_out_of_20` | ⬜ |
| ต้น, submit 9 จาก 15 | 10.97 / 20 | `test_golden_student_ton_who_skipped_half_scores_10_97_out_of_20` | ⬜ |

### 4. Pairing Engine ⬜

**`solve_feasibility(group_sizes, target_coverage, max_workload)`** — §8.2

| กฎ | Test | สถานะ |
|---|---|---|
| Coverage กับ workload คำนวณจากกันและกัน ไม่ fix ทั้งคู่ (D3) | `test_large_room_reaches_the_default_coverage_of_five` | ⬜ |
| เป้าที่เป็นไปไม่ได้ถูกลด พร้อมเหตุผลเป็นตัวเลข — 12 คน 3 กลุ่ม × 4 → coverage สูงสุด 4 (FR-PAIR-05) | `test_a_lowered_coverage_is_explained_in_numbers_not_just_warned_about` | ⬜ |
| งบเวลาของนักศึกษาจำกัด coverage (constraint 2) | `test_max_workload_caps_coverage_even_when_the_room_is_large` | ⬜ |
| รายงาน coverage ที่ได้จริง ไม่ใช่แค่เป้า — 200 คน 10 กลุ่ม: เป้า 5, ได้จริง 8–9 | `test_feasibility_reports_the_coverage_the_allocation_really_achieves` | ⬜ |
| ห้องที่มี 2 กลุ่มถูกปฏิเสธ เพราะไม่มีใครมีสิทธิ์ตัดสิน (provisional, Q2) | `test_a_two_group_classroom_is_refused_because_nobody_is_eligible_to_judge` | ⬜ |

**`allocate(roster, settings, seed)`** — INV-1 … INV-5 (+ property-based ตาม NFR-MAINT-02: 3–8 กลุ่ม × 3–8 คน × coverage 1–6)

| กฎ | Test | สถานะ |
|---|---|---|
| **INV-1** ไม่มีใครตัดสิน pair ที่มีงานของตัวเอง (FR-PAIR-02/03) | `test_no_evaluator_is_ever_asked_to_judge_their_own_group` | ⬜ |
| **INV-2** ไม่มีใครได้ pair เดิมซ้ำใน criterion เดียว (FR-PAIR-07) | `test_no_evaluator_receives_the_same_pair_twice_in_one_criterion` | ⬜ |
| **INV-3** Coverage ต่างกัน ≤ 1 ทุก pair (FR-PAIR-06) | `test_coverage_is_balanced_across_every_pair` | ⬜ |
| **INV-4** Workload ต่างกัน ≤ 1 ทุกผู้ประเมิน | `test_workload_is_balanced_across_every_evaluator` | ⬜ |
| **INV-5** Seed เดิม → allocation เหมือนเดิมทุกตัว (FR-PAIR-09) | `test_the_same_seed_reproduces_the_identical_allocation` | ⬜ |
| ตำแหน่งซ้าย/ขวาถูกสุ่มและบันทึก (FR-PAIR-08, D8) | `test_each_pair_records_which_item_was_shown_on_the_left` | ⬜ |

**`individual_plan(group_size, max_workload)`** — §8.3

| กฎ | Test | สถานะ |
|---|---|---|
| Coverage รายบุคคล = `m − 2` (D4) | `test_individual_plan_matches_the_table_in_the_prd` | ⬜ |
| กลุ่ม ≤ 2 คนไม่มีการประเมินรายบุคคล (FR-PAIR-12) | `test_groups_of_two_or_fewer_get_no_individual_evaluation` | ⬜ |
| กลุ่ม 3 คนถูก flag low confidence เสมอ (FR-PAIR-13) | `test_a_group_of_three_is_always_flagged_low_confidence` | ⬜ |
| Workload cap ตัด pair และรายงาน coverage ที่ลดลง (FR-PAIR-14) | `test_workload_cap_trims_pairs_and_reports_the_lower_coverage` | ⬜ |

### 5. Landing page (`src/App.test.tsx`, bun:test) ✅

| กฎ | Test | สถานะ |
|---|---|---|
| หน้าแรกแสดงชื่อบริการ Pairwise | `landing page > shows the service name` | ✅ |
| มี navigation bar (`data-testid="main-nav"`) พร้อมลิงก์ How it works | `landing page > renders the navigation bar with its test id` | ✅ |
| มีปุ่มหลัก Start comparing (`data-testid="cta-primary"`) | `landing page > renders the main CTA with its test id` | ✅ |
| มี placeholder ของ Comparison workspace | `landing page > renders a placeholder for the main feature` | ✅ |

### 6. E2E smoke (`tests/e2e/smoke.spec.ts`, Playwright) 🟡

| กฎ | Test | สถานะ |
|---|---|---|
| หน้าแรกโหลดได้ title มี "Pairwise" และเห็น navigation | `homepage loads correctly` | 🟡 |
| ปุ่ม Start comparing มองเห็นได้ | `main CTA is visible` | 🟡 |

---

## กฎที่ยังไม่มี test (ยอมรับไว้ชั่วคราว)

- **Scoring Engine ทั้งหมด (18 กฎ + golden 3)** — เป็น DDD Construction ต้องใช้ `Decimal` ตลอดเส้นทาง
  และ golden test ต้องได้ตัวเลขตรงทุกหลัก ใช้เวลาเกิน lab 1.5 ชม. → ทำใน WS-04
- **Pairing Engine ทั้งหมดยกเว้นกฎ publish (15 กฎ)** — ต้องมี rebalance pass สำหรับ INV-4 และ
  property-based test ต้องคุมให้ทั้ง suite < 10 วินาที → ทำหลัง Scoring Engine
- **กฎที่ขึ้นกับ Open Question** — ทำ test ตามค่า provisional ไปก่อน แล้วแก้เมื่อได้คำตอบ:
  Q2 (ห้อง 2 กลุ่ม), Q3 (instructor comparisons นับเป็น 1 หรือ `instructor_weight`),
  การตัดจุดในอีเมล (FR-AUTH-03)

---

## Harness Inventory

| ส่วน | ไฟล์ | สถานะ |
|---|---|---|
| Fake Repository | `tests/fakes/fake_assignment_repo.py` — `FakeAssignmentRepo` implement `AssignmentRepo` (Protocol) เก็บข้อมูลใน dict | 🟡 |
| Factories | `tests/factories.py` — `make_roster_row(**overrides)`, `make_roster_csv(rows)`, `make_roster(group_sizes)` | 🟡 |
| Fixtures | `tests/conftest.py` — `valid_csv`, `csv_with_bad_row_42` | 🟡 |
| Unit tests | `tests/unit/test_roster_import.py`, `tests/unit/test_publish.py` | 🟡 |
| Frontend tests | `src/App.test.tsx` (รันด้วย `bun test ./src`) | ✅ |
| E2E | `tests/e2e/smoke.spec.ts` + `playwright.config.ts` (baseURL `http://localhost:5173`) | 🟡 |

---

## Fidelity Check (WS-03)

> ยังไม่ได้รัน — กรอกหลังทำขั้นที่ 6 ของ lab (commit ก่อน → comment out กฎ → `pytest -q` → `git checkout -- backend/`)

| ลบกฎ | Test ที่แดง | ผล |
|---|---|---|
| ลบบรรทัด normalise email (lowercase + ตัด `+tag`) | _(กรอกหลังรัน)_ | _(กรอกหลังรัน)_ |
| ลบการเช็กว่าไฟล์มีแถวผิด แล้ว import แถวที่ถูกไปก่อน | _(กรอกหลังรัน)_ | _(กรอกหลังรัน)_ |

---

## Verification Results

| คำสั่ง | ผล | วันที่ |
|---|---|---|
| `bun run test` | 4 pass, 0 fail — 34ms (ต่ำกว่างบ 10 วินาที) | 14-Sep-2026 |
| `pytest -q` | _(ยังไม่มี test)_ | |
| `bunx playwright test` | _(ยังไม่ได้เขียน smoke.spec.ts)_ | |
| Coverage → `docs/coverage/` | _(ยังไม่ได้รัน)_ | |
