# PairEval — รายงานตรวจความตรงตาม PRD + Definition of Done

**วันที่ตรวจ:** 2026-10-19
**Commit:** `d2c3695` (branch `develop`)
**เกณฑ์:** [PRD v1.3](project-idea/pairwise_evaluation_prd.md) + [Definition of Done](project-idea/DEFINITION_OF_DONE.md) ทั้ง 13 หมวด

---

## สรุปคำตอบ

**ตรงเกือบทั้งหมด แต่ยังปิดงานไม่ได้** — ฟังก์ชันหลักตาม PRD ทำครบและเทสเขียวทุกชุด (รวม 115 เทส) แต่เหลือ **1 ข้อที่ผิดสเปกจริงและมีผลต่อนักศึกษา** (G1), **3 ข้อ UI ที่ PRD ระบุไว้แต่ยังไม่มี** (G2, G3, G5) และ **3 release gate** ที่ต้องใช้ตัวอาจารย์/เจ้าของโปรเจกต์เองจึงปิดได้

| ด้าน | สถานะ |
|---|---|
| Backend / API / Scoring / Pairing | ✅ ครบตาม PRD แทบทุกข้อ |
| Report + Export CSV/XLSX | ✅ ครบ (ขาดคอลัมน์รวม 1 จุด) |
| Student evaluation UI | ⚠️ ใช้งานได้ครบ แต่ไม่ตรง PRD 5 จุด |
| Interim score ฝั่งนักศึกษา | ❌ ไม่มีเลย — ผิด DoD §8 |
| เทสอัตโนมัติ | ✅ เขียวหมด 115/115 |
| Release gates (Google จริง, Vercel, acceptance) | ⏳ ยังไม่ทำ |

---

## 1. ผลรันเทสทั้งหมด (2026-10-19)

| ชุด | คำสั่ง | ผล | Exit |
|---|---|---|---|
| Backend + PostgreSQL 17 | `docker compose -f compose.test.yml run --build --rm unit python -m pytest -q` | **78 passed**, 3 warnings, 10.21s | 0 |
| Backend lint | `.venv/Scripts/python.exe -m compileall -q app tests` | ผ่าน | 0 |
| Frontend unit | `npm test` (`node --test`) | **8 passed**, 654ms | 0 |
| Frontend type check | `npm run lint` (`tsc --noEmit`) | ผ่าน | 0 |
| Frontend production build | `npm run build` (vite) | 2,023 modules, 2.02s | 0 |
| Chromium E2E | `docker compose -f compose.test.yml run --build --rm e2e` | **29 passed** / 14 spec files, 1.2m | 0 |
| Migration ฐานเปล่า → head | `alembic upgrade head` บน PostgreSQL 17 ใหม่ | ถึง `20261017_unique_pair_votes (head)` | 0 |

**รวม 115 เทส ผ่านหมด ไม่มีแดง ไม่มี skip**

E2E ครบทั้ง 14 ไฟล์: `classroom-management`(2), `completion`(1), `core-flows`(5), `evaluation-responsiveness`(2), `initial-evaluation-load`(1), `language-layout`(3), `resource`(3), `responsive-navigation`(2), `responsive`(3), `roster-management`(2), `scale`(1), `shadcn-dialog`(1), `sonner`(1), `toast`(2)

### ข้อควรรู้เรื่อง environment

ก่อนรัน `npm run lint` **พังด้วย 2 errors** (`Cannot find module lucide-react`) เพราะ `frontend/node_modules` เก่า — `lucide-react@1.59.0` อยู่ใน `package-lock.json` แล้วแต่ยังไม่ถูกติดตั้ง หลัง `npm ci` ผ่านทันที **ไม่ใช่ defect ของโค้ด** แต่ใครก็ตามที่ clone มาต้อง `npm ci` ก่อน ไม่งั้นเจออาการเดียวกัน

### Environment ที่ใช้วัด (ตามที่ DoD หมวด "หลักฐาน" ต้องการ)

Windows 11 Home Single Language 10.0.26300 · Docker 29.8.0 Linux engine · **16 CPUs, 7.58 GiB RAM**
PostgreSQL 17-alpine บน tmpfs (ephemeral) · Playwright 1.63.0 Chromium · Vite 5 dev server · mock auth
Node v24.21.0 (host) · Python 3.13.15 (host venv) / 3.12 (container)

### Performance (DoD §12) — ยืนยันใหม่วันนี้

`e2e/scale.spec.ts` ผ่าน: classroom 200 นักศึกษา / 10 กลุ่ม → publish สำเร็จ → เวลา render จนเห็น radio ของ Group evaluation **< 2000 ms** (`scale.spec.ts:33`) และ 20 concurrent individual-evaluation API reads **max < 2000 ms** (`scale.spec.ts:45`)

ผล k6 load test (1→10→0 VUs, p95 12.03 ms) เป็นของรอบ 2026-10-17 **ไม่ได้รันซ้ำวันนี้**

---

## 2. PRD — Functional Requirements

### 4.1 Authentication — ✅ ครบ

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-AUTH-01 Google OAuth เท่านั้น | ✅ | `backend/app/auth.py:66-93`; mock bypass ล็อกไว้ที่ `APP_ENV=development` เท่านั้น (`auth.py:71-77`) |
| FR-AUTH-02 ตรวจ email กับ roster | ✅ | `backend/app/routes/classrooms.py:19-30` + activate pending |
| FR-AUTH-03 แยกสิทธิ์ Instructor/Student | ✅ | `backend/app/dependencies.py:11-18` |
| FR-AUTH-04 Instructor หลาย Classroom | ✅ | `backend/app/models.py:10` (`instructor_emails` ต่อห้อง) |
| FR-AUTH-05 `INSTRUCTOR_EMAILS` + ตรวจ token ทุก protected API | ✅ | `auth.py:58-63`; ทุก router มี dependency; public แค่ `/health` (`main.py:58-65`) |

### 4.2 Classroom Management — ✅ ครบ

FR-CLASS-01 ✅ `routes/classrooms.py:124-137` (CSV ส่งเป็น JSON `csv_text` ไม่ใช่ multipart) ·
FR-CLASS-02 ✅ `roster.py:74-91` (atomic — error เดียวตีกลับทั้งไฟล์) ·
FR-CLASS-03 ✅ `classrooms.py:95-96` + `:115-116` (ห้ามลบคนสุดท้าย) ·
FR-CLASS-04 ✅ `classrooms.py:54-57`

### 4.3 Assignment Management — ✅ ครบ

FR-ASSIGN-01 ✅ `models.py:68-75` + `schemas.py:177-192` (`total_score` ตรวจกับ 4 maxima, ไม่ตรง = 422) ·
FR-ASSIGN-02/03 ✅ `assignment_setup.py:24-25,45-48` (รวม 100% ต่อ section) ·
FR-ASSIGN-04 ✅ `assignment_setup.py:85-86` ·
FR-ASSIGN-05 ✅ `publish.py:26-28` (≥3 กลุ่ม), `pairing.py:110-111` (กลุ่ม <3 คนไม่มี individual pair), `reports.py:159` (ยกเว้นคะแนนมีส่วนร่วม)

### 4.4 Pairing Engine — ✅ ครบทั้ง 14 ข้อ

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-PAIR-01 ทุก nC2 + `min(5, eligible)` | ✅ | `pairing.py:35`, `:62` |
| FR-PAIR-02 ไม่จำกัด 5 คู่ตายตัว | ✅ | `pairing.py:63-68` |
| FR-PAIR-03 คู่ active ไม่ซ้ำ/คน/criterion | ✅ | `models.py:113-132` (4 partial unique indexes) + `instructor_evaluation.py:47-66` (409) |
| FR-PAIR-04/07 ห้ามประเมินตัวเอง | ✅ | `pairing.py:56`, `instructor_evaluation.py:99-103` |
| FR-PAIR-05/06/08 individual ในกลุ่ม + balance | ✅ | `publish.py:58-66`, `pairing.py:63,113` |
| FR-PAIR-09..14 reassignment | ✅ | `reassignment.py:49-55`, `:99-152`, `:191-192`, `:167-178`, `:208-211`, `:204-207` |
| Seeded reproducibility | ✅ | `pairing.py:34,42`; `publish.py:54,62` |

**ยืนยันจาก DB จริง:** migration สร้าง index ครบ 4 ตัว — `uq_pairs_active_student_group`, `uq_pairs_active_student_individual`, `uq_pairs_active_instructor_group`, `uq_pairs_active_instructor_individual`

### 4.5 Evaluation UI — ⚠️ ใช้งานได้ แต่ไม่ตรง PRD 5 จุด

| ID | สถานะ | หมายเหตุ |
|---|---|---|
| FR-EVAL-01 หน้าเดียวทุก criteria (Group) | ⚠️ | แสดงทุก criterion/pair จริง แต่เป็น `<details>` ในการ์ด assignment ไม่ใช่ "หน้า" — แอปไม่มี router (`AssignmentWorkspace.tsx:251`) |
| FR-EVAL-02 layout + จัดกลุ่มตาม criterion | ⚠️ | แต่ละคู่เป็น `<fieldset>` ที่ `<legend>` ซ้ำชื่อ criterion; ฝั่ง group ไม่มีหัวข้อ criterion แล้วไล่คู่ใต้หัวข้อ (`EvaluationWorkspace.tsx:94-101`) |
| FR-EVAL-03 radio 5 ระดับ 1/3/5 | ✅ ค่า · ⚠️ layout | ค่าถูก (`EvaluationWorkspace.tsx:11,104`) แต่ PRD วาดเป็นแถวเดียว `Group A ( )( )( )( )( ) Group B` ของจริงแยกเป็น left — VS — right แถวหนึ่ง แล้ว radio อีกแถวล่าง (`:99-107`, `assets/styles.css:62-66`) |
| FR-EVAL-04 ปุ่ม **Save** | ❌ **G4** | ไม่มีปุ่ม Save — autosave ทุกครั้งที่กด radio (`:104-105`) ฟังก์ชันครบแต่ไม่มี control ตามที่ PRD เขียน |
| FR-EVAL-05 ปุ่ม Submit + แก้ส่งใหม่ได้ | ✅ | `:116-117`, `:48-60` |
| FR-EVAL-06 เตือนคู่ที่ยังไม่ประเมิน | ❌ **G5** | dialog เขียนลอย ๆ ว่า "Submit all currently saved answers?" ไม่บอกจำนวนคู่ที่ยังว่าง; จำนวนโผล่ *หลัง* ส่งแล้ว (`:118-120`, `:54`) |
| FR-EVAL-07 หน้า Individual แยก | ⚠️ | component/API/draft แยกจริง แต่เป็น `<details>` อันที่สองบนจอเดียวกัน |
| FR-EVAL-08 เฉพาะเพื่อนในกลุ่ม | ✅ | `:68-72` + บังคับที่ backend |
| FR-EVAL-09 รูปแบบเดียวกับ Group | ⚠️ | ฝั่ง individual แบ่งหน้าทีละ criterion (มี navigator, "รอบ n/N", ปุ่มก่อนหน้า/ถัดไป) ไม่ได้ไล่ทุก criterion เหมือน group (`:82-92`, `:111-115`) |
| FR-EVAL-10 Save/Submit แยกกัน | ✅ | `:43`, `:52` |
| FR-EVAL-11 หลัง deadline ปิด Save+Submit | ✅ | `:94` (radio disabled), `:116` (ซ่อน Submit) |
| FR-EVAL-12 draft ไม่นับ | ✅ backend | `reports.py:18-21` อ่านแค่ `Submission`; `DraftChoice` แยกตาราง — แต่ UI ไม่ได้บอกผู้ใช้ และตัวนับ progress นับ draft |
| FR-EVAL-13 **Countdown timer** + deadline | ❌ **G2** | **ไม่มี countdown เลย** (grep `countdown`/`เหลือเวลา`/`timeLeft` = 0 hits) มีแค่วันที่ deadline (`:77`) |
| FR-EVAL-14..17 re-submission | ✅ | `:116` (ไม่ปิดหลังส่ง), `:80` (`Last submitted` timestamp), `:17` (key แยก section) |

### 4.6 Scoring Engine — ✅ ครบ ยกเว้น FR-SCORE-13

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-SCORE-01 mapping + เฉลี่ย | ✅ | `scoring.py:6` (`1/0, .75/.25, .5/.5, .25/.75, 0/1`), `:44-54` |
| FR-SCORE-02 normalize = 1.0 | ✅ | `scoring.py:55,69` |
| FR-SCORE-03 weight × max | ✅ | `scoring.py:71`, `reports.py:90-94` |
| FR-SCORE-04/05 zero rule + draft ไม่นับ | ✅ | `reports.py:160-162`, `:18-21` |
| FR-SCORE-06..09 instructor weight | ✅ | `models.py:72`, `reports.py:88` (ค่าเดียวใช้ทั้ง group+individual ตาม FR-SCORE-08), `:101,140` |
| FR-SCORE-10 rolling update | ✅ | คำนวณสดทุกครั้งที่อ่าน (`reports.py:13-175`) — ถี่กว่า "ทุกวัน" ที่ PRD ขอ |
| FR-SCORE-11/12/14 | ✅ | `evaluation.py:118-137`, `routes/reports.py:66-68`, `reports.py:20,56` |
| **FR-SCORE-13 label "Interim"** | ❌ **G1** | `/my-scores` คืน student row เปล่า **ไม่มี** `group_final`/`individual_final` (`routes/reports.py:66-68`); flag มีอยู่ที่ `reports.py:174-175` แต่ไม่ถูกส่งออก และ label ที่ `ScoreWorkspace.tsx:61` อยู่ใน `{report && ...}` = **เห็นเฉพาะอาจารย์** |
| FR-SCORE-15..18 participation | ✅ | `reports.py:143-162` (`max × done/total`), แยก group/individual (`:148`), ยกเว้นกลุ่ม <3 (`:159`) |
| FR-SCORE-19..21 anonymity | ✅ | `routes/reports.py:55-68`, `reports.py:204-206` (owner-only), `export.py:42-47` (ชื่อแฝง) |

**หมายเหตุ FR-SCORE-01:** ตัวหารใช้ `effective_votes` (รวมน้ำหนักแล้ว) → instructor weight 3 นับเป็น 3 ทั้งตัวตั้งและตัวหาร สอดคล้องกับ FR-SCORE-07 ที่เขียนว่า "นับเทียบเท่า 3 votes" — **ถูกต้อง**

### 4.7 Report & Export — ✅ ครบ (ขาดคอลัมน์รวม)

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-REPORT-01/02 | ✅ | `reports.py:172`, `:163-170` |
| FR-REPORT-03 Pair Coverage ครบ 9 ฟิลด์ | ✅ | `reports.py:130-141` — `eligible_evaluators`, `target_evaluations`, `assigned_evaluators`, `votes`, `missing_to_target`, `shortage_to_five`, `instructor_votes`, `effective_votes`, `left_points`/`right_points`; **instructor votes ไม่ลด `missing_to_target`** ตาม PRD (`:126-129`) |
| FR-REPORT-04 "ส่งประเมินเพิ่ม" | ✅ | `routes/assignments.py:160-170`, `instructor_evaluation.py:92-118`; ส่งเกินเป้า 5 ได้; label จริงคือ "ส่งคู่เพิ่มให้นักศึกษา" |
| FR-REPORT-05 "ประเมินเอง" | ✅ | `routes/assignments.py:147-157,184-193`; label จริงคือ "กำหนดให้ฉัน" |
| FR-REPORT-06 | ✅ | `routes/reports.py:55-68` |
| **FR-REPORT-07 rolling + Interim** | ⚠️ **G1** | คะแนน rolling มี แต่ไม่มี label Interim (เหตุเดียวกับ FR-SCORE-13) |
| FR-REPORT-08 | ✅ | `routes/reports.py:67-68` |
| FR-EXPORT-01/03/04/05 | ✅ | `routes/reports.py:71-100`, `xlsx_export.py:54` (3 sheets), `routes/reports.py:20-30` (ชื่อไฟล์ + RFC 5987 รองรับชื่อไทย) |
| FR-EXPORT-02 "Individual Summary + total" | ⚠️ **G9** | มีคะแนนแยกครบทุกคอลัมน์ แต่**ไม่มีคอลัมน์รวมยอดเดียว** (`export.py:30-38`) |

---

## 3. Definition of Done — 13 หมวด

| หมวด | สถานะ | หมายเหตุ |
|---|---|---|
| §1 ขอบเขตรุ่นแรก (7) | ⚠️ 6✅ 1⏳ | ครบทุกข้อ; ข้อ Google login ยืนยันด้วย mock เท่านั้น |
| §2 Authentication/Authorization (9) | ✅ 9/9 | 401/403 มีเทสคุม (`test_auth.py`, `test_api_access.py`); logout ล้าง credential |
| §3 Classroom และ Roster (9) | ✅ 9/9 | header/email/แถวซ้ำ validate ครบ, import ไม่ทิ้งข้อมูลครึ่ง ๆ, pending activate ตอน login |
| §4 Assignment และ Criteria (9) | ✅ 9/9 | |
| §5 Pairing Engine (9) | ✅ 9/9 | ยืนยัน 200 คน/10 กลุ่มด้วย `scale.spec.ts` วันนี้ |
| §6 Evaluation และ Submission (10) | ⚠️ 9✅ 1⚠️ | "หน้า Group และ Individual แยกจากกัน" — แยก logic จริงแต่เป็น section บนจอเดียว (G7) |
| §7 Group Reassignment (6) | ✅ 6/6 | backend เก็บ actor ครบ (`reassignment.py:204-207`) แต่ UI ไม่โชว์ (G8) |
| §8 Scoring (11) | ❌ 10✅ **1❌** | **"คะแนนระหว่างช่วงประเมินมีสถานะ Interim"** — นักศึกษาไม่เห็นเลย (G1); "ยังไม่มีข้อมูล" ก่อน final ✅ (`ScoreWorkspace.tsx:9`) |
| §9 Report และ Export (9) | ⚠️ 8✅ 1⚠️ | formula injection ป้องกันแล้ว + มีเทส; ขาดคอลัมน์รวม (G9) |
| §10 UI และ Accessibility (6) | ✅ 6/6 | **ยืนยัน: ไม่มี `alert`/`confirm`/`prompt` ของ browser เลย**; TH/EN, data-testid, focus state ครบ |
| §11 Security และ Data Integrity (7) | ✅ 7/7 | ยืนยัน unique indexes จาก DB จริง; archive snapshot ≥366 วัน |
| §12 Performance และ Reliability (5) | ✅ 5/5 | <2s ยืนยันวันนี้; migration ฐานเปล่า→head ยืนยันวันนี้; k6 เป็นผล 2026-10-17 |
| §13 Verification และการส่งมอบ (9) | ❌ 6✅ **3⏳** | เทสเขียวหมด/README/.env.example/docs ✅ · **Google login จริง, product owner acceptance, Critical-High defect** ยังค้าง |

---

## 4. ช่องว่างที่ต้องแก้ เรียงตามความสำคัญ

### ต้องแก้ก่อนส่งอาจารย์

| # | เรื่อง | ทำไมสำคัญ | แก้ที่ไหน |
|---|---|---|---|
| **G1** | นักศึกษาไม่เห็นสถานะ Interim | **ผิด DoD §8 ตรง ๆ** + PRD FR-SCORE-13/FR-REPORT-07 นักศึกษาอาจเข้าใจผิดว่าคะแนนนิ่งแล้ว | ส่ง `group_final`/`individual_final` ใน `/my-scores` (`backend/app/routes/reports.py:66-68`) แล้วโชว์ label ใน student branch (`frontend/src/ScoreWorkspace.tsx:48,57-61`) |
| **G2** | ไม่มี Countdown timer | PRD FR-EVAL-13 ระบุชัด "แสดง Countdown timer" | `frontend/src/EvaluationWorkspace.tsx:77` |
| **G5** | ไม่เตือนคู่ที่ยังไม่ประเมิน | PRD FR-EVAL-06; นักศึกษาส่งไม่ครบแล้วเสียคะแนนมีส่วนร่วมโดยไม่รู้ตัว | `EvaluationWorkspace.tsx:118-120` |
| **G3** | ไม่มี progress bar ต่อ criterion | PRD FR-SCORE-17 ขอ bar `X / Y pairs submitted`; ของจริงเป็น text รวม และนับ **draft** ไม่ใช่ submitted | `EvaluationWorkspace.tsx:78`, `:89` |

### ควรแก้ (ไม่บล็อก)

| # | เรื่อง | แก้ที่ไหน |
|---|---|---|
| G4 | ไม่มีปุ่ม Save (autosave แทน) — ถ้าอาจารย์ยืนตาม PRD ต้องเพิ่มปุ่ม | `EvaluationWorkspace.tsx:104-105` |
| G6 | layout คู่เปรียบเทียบไม่ตรง mock ของ PRD | `assets/styles.css:62-66` |
| G7 | Group/Individual เป็น section ไม่ใช่ "หน้า" ตาม PRD §8 Screen Flow | ต้องเพิ่ม router |
| G8 | ประวัติ reassignment ไม่โชว์ผู้สั่งย้าย + โชว์ raw ID | `frontend/src/api.ts:220-223`, `GroupReassignment.tsx:83` |
| G9 | Individual Summary ไม่มีคอลัมน์รวม | `backend/app/export.py:30-38` |
| G10 | Coverage table โชว์ `left_id`/`right_id` เป็นเลข ไม่ใช่ชื่อ | `frontend/src/ScoreWorkspace.tsx:24-26` |

---

## 5. ช่องว่างในการเทส (เทสเขียวหมด แต่ไม่ได้คุมเรื่องเหล่านี้)

**นี่คือความเสี่ยงที่ควรบอกอาจารย์** — ผ่าน 115 เทสไม่ได้แปลว่าคุมครบ

| เรื่อง | ความเสี่ยง |
|---|---|
| **Deadline ปิดแล้ว (`is_open: false`)** | **ไม่มี E2E/fixture ไหนทดสอบเลย** — ทุก fixture ใช้ deadline อนาคต (`completion.spec.ts:32`, `evaluation-responsiveness.spec.ts:13`, `scale.spec.ts:14`) ทั้งที่ DoD §6 บังคับ 2 ข้อเรื่องนี้ |
| **Re-submission** | ทดสอบแค่ submit ครั้งเดียว ไม่มีการ submit ซ้ำเลย (DoD §6 บังคับ) |
| `POINTS` choice 2 และ 4 | `0.75/0.25` และ `0.25/0.75` **ไม่เคยถูก assert** — `test_scoring.py` คุมแค่ 1, 3, 5 |
| `group_final`/`individual_final` | ไม่มีเทสอ้างถึง → G1 จึงหลุดมาได้ |
| Individual participation exemption กลุ่ม <3 | คุมแค่ฝั่ง pairing ไม่คุมที่ระดับ report (`reports.py:159`) |
| FR-REPORT-04/05 instructor evaluation UI | ไม่มี spec ไหนแตะ `InstructorEvaluation` เลย |
| Coverage table 9 ฟิลด์ | `<details>` ของ coverage ไม่เคยถูกเปิดใน E2E |

---

## 6. Release gates ที่ต้องใช้เจ้าของโปรเจกต์/อาจารย์เอง

1. **Google Login จริง** ทั้ง Instructor และ Student บน production origin — ยังไม่ทำ (`TASKS.md:100`, DoD §13)
2. **ยืนยัน Vercel production revision** ว่าเป็น `d61ab2b` หรือลูกหลาน (`RELEASE_VERIFICATION.md:35`)
3. **Product owner acceptance** + แนบตัวอย่าง CSV/XLSX, account matrix, known limitations (`DEFINITION_OF_DONE.md:149-158`)

---

*รายงานนี้สร้างจากการอ่านโค้ด (ทุกข้ออ้าง file:line) + รันเทสจริงทั้ง 7 ชุดเมื่อ 2026-10-19 ไม่มีการแก้ production code หรือ test ใด ๆ*
