# PairEval — รายงานตรวจความตรงตาม PRD + Definition of Done

**วันที่ตรวจ:** 2026-10-19
**Commit ที่ตรวจ:** `d2c3695` (branch `develop`)
**แก้แล้วที่:** branch `fix-fr` — G1–G10 ปิดครบแล้ว และ merge `develop` ล่าสุดเข้ามาแล้ว (ดูหัวข้อ 4)
**เกณฑ์:** PRD **v1.3** + [Definition of Done](project-idea/DEFINITION_OF_DONE.md) ทั้ง 13 หมวด

> ⚠️ **รายงานนี้ตรวจกับ PRD v1.3 ไม่ใช่ [v2.0](project-idea/pairwise_evaluation_prd.md) ฉบับปัจจุบัน**
> v2.0 เปลี่ยนเลข requirement ใหม่ทั้งฉบับ เลข FR ในรายงานนี้จึงถูก **แปลงเป็นเลขของ v2.0 แล้ว**
> เพื่อให้ยังอ้างอิงได้ (ดูตารางการแปลงท้ายเอกสาร)
>
> เครื่องหมาย **⚠️** หลังเลข FR หมายถึง **v2.0 เปลี่ยนตัว requirement นั้น** ✅ ในแถวนั้น
> จึงยืนยันได้แค่ข้อความเดิมของ v1.3 **ไม่ใช่** ข้อกำหนดใหม่ — ดู §19.1 ของ PRD ว่าข้อใดกำลังแก้อยู่

---

## สรุปคำตอบ

**ตรงตาม PRD/DoD ครบทุกข้อที่โค้ดคุมได้แล้ว** — ช่องว่างทั้ง 10 ข้อ (G1–G10) แก้บน branch `fix-fr` เรียบร้อย merge `develop` ล่าสุดเข้ามาแล้ว และเทสเขียวทุกชุด รวม 120 เทส เหลือเพียง **3 release gate** ที่ต้องใช้ตัวอาจารย์/เจ้าของโปรเจกต์เองจึงปิดได้

| ด้าน | สถานะ |
|---|---|
| Backend / API / Scoring / Pairing | ✅ ครบตาม PRD แทบทุกข้อ |
| Report + Export CSV/XLSX | ✅ ครบ รวมคอลัมน์รวมและชื่อ subject ใน coverage |
| Student evaluation UI | ✅ countdown / progress / คำเตือน / ปุ่ม Save / layout แถวเดียว / แยกหน้า ครบแล้ว |
| Interim score ฝั่งนักศึกษา | ✅ แก้แล้ว (G1) |
| เทสอัตโนมัติ | ✅ เขียวหมด 120/120 |
| Release gates (Google จริง, Vercel, acceptance) | ⏳ ยังไม่ทำ |

---

## 1. ผลรันเทสทั้งหมด (2026-10-19)

| ชุด | คำสั่ง | ผล | Exit |
|---|---|---|---|
| Backend + PostgreSQL 17 | `docker compose -f compose.test.yml run --build --rm unit python -m pytest -q` | **81 passed**, 3 warnings, 11.59s | 0 |
| Backend lint | `.venv/Scripts/python.exe -m compileall -q app tests` | ผ่าน | 0 |
| Frontend unit | `npm test` (`node --test`) | **8 passed**, 870ms | 0 |
| Frontend type check | `npm run lint` (`tsc --noEmit`) | ผ่าน | 0 |
| Frontend production build | `npm run build` (vite) | 2,023 modules, 2.73s | 0 |
| Chromium E2E | `docker compose -f compose.test.yml run --build --rm e2e` | **31 passed** / 16 spec files, 1.2m | 0 |
| Migration ฐานเปล่า → head | `alembic upgrade head` บน PostgreSQL 17 ใหม่ | ถึง `20261017_unique_pair_votes (head)` | 0 |

**รวม 120 เทส ผ่านหมด ไม่มีแดง ไม่มี skip** (เพิ่มจากเดิม 115 ด้วยเทสที่คุม G1–G10 และ spec `instructor-pair-planner` ที่ติดมากับ `develop`)

รันซ้ำทั้งหมดอีกครั้ง**หลัง merge `develop`** (commit `77f9423`) ซึ่งนำ `DisclosureSummary` และ instructor pair planner ตัวใหม่เข้ามา

E2E ครบทั้ง 15 ไฟล์: `classroom-management`(2), `completion`(1), `core-flows`(5), `deadline-and-progress`(1), `evaluation-responsiveness`(2), `initial-evaluation-load`(1), `language-layout`(3), `resource`(3), `responsive-navigation`(2), `responsive`(3), `roster-management`(2), `scale`(1), `shadcn-dialog`(1), `sonner`(1), `toast`(2)

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
| FR-AUTH-03 ตรวจ email กับ roster | ✅ | `backend/app/routes/classrooms.py:19-30` + activate pending |
| FR-AUTHZ-01 แยกสิทธิ์ Instructor/Student | ✅ | `backend/app/dependencies.py:11-18` |
| FR-AUTHZ-03 Instructor หลาย Classroom | ✅ | `backend/app/models.py:10` (`instructor_emails` ต่อห้อง) |
| FR-AUTHZ-01 `INSTRUCTOR_EMAILS` + ตรวจ token ทุก protected API | ✅ | `auth.py:58-63`; ทุก router มี dependency; public แค่ `/health` (`main.py:58-65`) |

### 4.2 Classroom Management — ✅ ครบ

FR-CLASS-01 ✅ `routes/classrooms.py:124-137` (CSV ส่งเป็น JSON `csv_text` ไม่ใช่ multipart) ·
FR-CLASS-02 ✅ `roster.py:74-91` (atomic — error เดียวตีกลับทั้งไฟล์) ·
FR-CLASS-06 ✅ `classrooms.py:95-96` + `:115-116` (ห้ามลบคนสุดท้าย) ·
FR-AUTHZ-02 ✅ `classrooms.py:54-57`

### 4.3 Assignment Management — ✅ ครบ

FR-ASSIGN-01 ✅ `models.py:68-75` + `schemas.py:177-192` (`total_score` ตรวจกับ 4 maxima, ไม่ตรง = 422) ·
FR-ASSIGN-02 ✅ `assignment_setup.py:24-25,45-48` (รวม 100% ต่อ section) ·
FR-ASSIGN-03 ✅ `assignment_setup.py:85-86` ·
FR-ASSIGN-02 + FR-PAIR-12 ✅ `publish.py:26-28` (≥3 กลุ่ม), `pairing.py:110-111` (กลุ่ม <3 คนไม่มี individual pair), `reports.py:159` (ยกเว้นคะแนนมีส่วนร่วม)

### 4.4 Pairing Engine — ✅ ครบทั้ง 14 ข้อ

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-PAIR-01 ทุก nC2 + `min(5, eligible)` | ✅ | `pairing.py:35`, `:62` |
| FR-PAIR-05 ไม่จำกัด 5 คู่ตายตัว | ✅ | `pairing.py:63-68` |
| FR-PAIR-07 คู่ active ไม่ซ้ำ/คน/criterion | ✅ | `models.py:113-132` (4 partial unique indexes) + `instructor_evaluation.py:47-66` (409) |
| FR-PAIR-02 + FR-PAIR-03 ห้ามประเมินตัวเอง | ✅ | `pairing.py:56`, `instructor_evaluation.py:99-103` |
| FR-PAIR-03 + FR-PAIR-06 individual ในกลุ่ม + balance | ✅ | `publish.py:58-66`, `pairing.py:63,113` |
| FR-PAIR-11 + FR-AUDIT-02 reassignment | ✅ | `reassignment.py:49-55`, `:99-152`, `:191-192`, `:167-178`, `:208-211`, `:204-207` |
| Seeded reproducibility | ✅ | `pairing.py:34,42`; `publish.py:54,62` |

**ยืนยันจาก DB จริง:** migration สร้าง index ครบ 4 ตัว — `uq_pairs_active_student_group`, `uq_pairs_active_student_individual`, `uq_pairs_active_instructor_group`, `uq_pairs_active_instructor_individual`

### 4.5 Evaluation UI — ⚠️ ใช้งานได้ แต่ไม่ตรง PRD 5 จุด

| ID | สถานะ | หมายเหตุ |
|---|---|---|
| FR-EVAL-01 หน้าเดียวทุก criteria (Group) | ✅ **แก้แล้ว (G7)** | `StudentEvaluationPages` แสดงทีละหน้า มี page nav สลับ Group/Individual; หน้า Group ยังไล่ทุก criterion/pair ในหน้าเดียว |
| FR-EVAL-02 layout คู่เปรียบเทียบ | ✅ **แก้แล้ว (G6)** | แถวเดียว `ซ้าย — 5 ระดับ — ขวา` ตาม mock; ยุบเป็นชื่อสองฝั่งบนแถวบนและสเกลแถวล่างเมื่อจอ ≤900px |
| FR-EVAL-03 ⚠️ radio 5 ระดับ 1/3/5 | ✅ ค่า · ⚠️ layout | ค่าถูก (`EvaluationWorkspace.tsx:11,104`) แต่ PRD วาดเป็นแถวเดียว `Group A ( )( )( )( )( ) Group B` ของจริงแยกเป็น left — VS — right แถวหนึ่ง แล้ว radio อีกแถวล่าง (`:99-107`, `assets/styles.css:62-66`) |
| FR-EVAL-04 ปุ่ม **Save** | ✅ **แก้แล้ว (G4)** | เพิ่มปุ่ม `save-draft` ที่ flush ร่างแล้วยืนยันผลจริง (hook คืนค่าสำเร็จ/ไม่สำเร็จ) โดยยังคง autosave ไว้ |
| FR-EVAL-05 ปุ่ม Submit + แก้ส่งใหม่ได้ | ✅ | `:116-117`, `:48-60` |
| FR-EVAL-05 เตือนคู่ที่ยังไม่ประเมิน | ✅ **แก้แล้ว (G5)** | เพิ่มคำเตือนในหน้า (`unanswered-notice`) และย้ำจำนวนใน dialog ยืนยัน (`unanswered-warning`) — `EvaluationWorkspace.tsx` |
| FR-EVAL-11 หน้า Individual แยก | ✅ **แก้แล้ว (G7)** | mount ทีละหน้า — เปิด Individual แล้วหน้า Group จะถูก unmount (เทสยืนยันด้วย `toHaveCount(0)`) |
| FR-PAIR-03 เฉพาะเพื่อนในกลุ่ม | ✅ | `:68-72` + บังคับที่ backend |
| FR-EVAL-02 รูปแบบเดียวกับ Group | ⚠️ | ฝั่ง individual แบ่งหน้าทีละ criterion (มี navigator, "รอบ n/N", ปุ่มก่อนหน้า/ถัดไป) ไม่ได้ไล่ทุก criterion เหมือน group (`:82-92`, `:111-115`) |
| FR-EVAL-11 Save/Submit แยกกัน | ✅ | `:43`, `:52` |
| FR-EVAL-08 หลัง deadline ปิด Save+Submit | ✅ | `:94` (radio disabled), `:116` (ซ่อน Submit) |
| FR-EVAL-09 draft ไม่นับ | ✅ backend | `reports.py:18-21` อ่านแค่ `Submission`; `DraftChoice` แยกตาราง — แต่ UI ไม่ได้บอกผู้ใช้ และตัวนับ progress นับ draft |
| FR-EVAL-10 **Countdown timer** + deadline | ✅ **แก้แล้ว (G2)** | เพิ่ม `frontend/src/useCountdown.ts` + `evaluation-countdown` นับถอยหลังทุกวินาที รองรับ TH/EN, deadline ว่าง และเลยกำหนด; clear interval ตอน unmount |
| FR-EVAL-06 re-submission | ✅ | `:116` (ไม่ปิดหลังส่ง), `:80` (`Last submitted` timestamp), `:17` (key แยก section) |

### 4.6 Scoring Engine — ✅ ครบ ยกเว้น FR-SCORE-07

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-SCORE-01 mapping + เฉลี่ย | ✅ | `scoring.py:6` (`1/0, .75/.25, .5/.5, .25/.75, 0/1`), `:44-54` |
| FR-SCORE-02 ⚠️ normalize = 1.0 | ✅ | `scoring.py:55,69` |
| FR-SCORE-02 ⚠️ weight × max | ✅ | `scoring.py:71`, `reports.py:90-94` |
| FR-SCORE-04 ⚠️ + FR-EVAL-09 zero rule + draft ไม่นับ | ✅ | `reports.py:160-162`, `:18-21` |
| FR-SCORE-03 ⚠️ instructor weight | ✅ | `models.py:72`, `reports.py:88` (ค่าเดียวใช้ทั้ง group+individual ตาม FR-SCORE-03 ⚠️), `:101,140` |
| FR-SCORE-06 ⚠️ rolling update | ✅ | คำนวณสดทุกครั้งที่อ่าน (`reports.py:13-175`) — ถี่กว่า "ทุกวัน" ที่ PRD ขอ |
| FR-EVAL-06 + FR-REPORT-06 | ✅ | `evaluation.py:118-137`, `routes/reports.py:66-68`, `reports.py:20,56` |
| **FR-SCORE-07 label "Interim"** | ✅ **แก้แล้ว (G1)** | `/my-scores` ส่ง `group_final`/`individual_final` แล้ว และ `ScoreWorkspace.tsx` แสดง label ทั้ง branch นักศึกษาและอาจารย์ (`score-finality`); ข้อความ TH เปลี่ยนเป็น "Interim — อาจเปลี่ยนแปลงได้" ตรงตาม PRD |
| FR-SCORE-04 ⚠️ participation | ✅ | `reports.py:143-162` (`max × done/total`), แยก group/individual (`:148`), ยกเว้นกลุ่ม <3 (`:159`) |
| **FR-EVAL-07 progress bar ต่อ criterion** | ✅ **แก้แล้ว (G3)** | เพิ่ม `criterion-progress` — `<progress>` ต่อ criterion นับ **submitted** (`pair.submitted_choice`) แสดง `X / Y pairs submitted` พร้อม aria-label |
| FR-REPORT-06 + FR-ANON-01 + FR-EXPORT-03 anonymity | ✅ | `routes/reports.py:55-68`, `reports.py:204-206` (owner-only), `export.py:42-47` (ชื่อแฝง) |

**หมายเหตุ FR-SCORE-01:** ตัวหารใช้ `effective_votes` (รวมน้ำหนักแล้ว) → instructor weight 3 นับเป็น 3 ทั้งตัวตั้งและตัวหาร สอดคล้องกับ FR-SCORE-03 ⚠️ ที่เขียนว่า "นับเทียบเท่า 3 votes" — **ถูกต้อง**

### 4.7 Report & Export — ✅ ครบ (ขาดคอลัมน์รวม)

| ID | สถานะ | หลักฐาน |
|---|---|---|
| FR-REPORT-01 + FR-REPORT-02 | ✅ | `reports.py:172`, `:163-170` |
| FR-REPORT-03 Pair Coverage ครบ 9 ฟิลด์ | ✅ | `reports.py:130-141` — `eligible_evaluators`, `target_evaluations`, `assigned_evaluators`, `votes`, `missing_to_target`, `shortage_to_five`, `instructor_votes`, `effective_votes`, `left_points`/`right_points`; **instructor votes ไม่ลด `missing_to_target`** ตาม PRD (`:126-129`) |
| FR-PAIR-10 "ส่งประเมินเพิ่ม" | ✅ | `routes/assignments.py:160-170`, `instructor_evaluation.py:92-118`; ส่งเกินเป้า 5 ได้; label จริงคือ "ส่งคู่เพิ่มให้นักศึกษา" |
| FR-REPORT-03 "ประเมินเอง" | ✅ | `routes/assignments.py:147-157,184-193`; label จริงคือ "กำหนดให้ฉัน" |
| FR-REPORT-06 | ✅ | `routes/reports.py:55-68` |
| **FR-REPORT-06 ⚠️ rolling + Interim** | ✅ **แก้แล้ว (G1)** | คะแนน rolling + label Interim ฝั่งนักศึกษาครบแล้ว |
| FR-ANON-01 | ✅ | `routes/reports.py:67-68` |
| FR-EXPORT-01 + FR-EXPORT-03 + FR-EXPORT-05 | ✅ | `routes/reports.py:71-100`, `xlsx_export.py:54` (3 sheets), `routes/reports.py:20-30` (ชื่อไฟล์ + RFC 5987 รองรับชื่อไทย) |
| FR-EXPORT-02 ⚠️ "Individual Summary + total" | ✅ **แก้แล้ว (G9)** | เพิ่มคอลัมน์ `total_score` = work + participation ทั้งสองส่วน; ส่วนที่ได้รับการยกเว้นเป็น `None` จึงถูกข้าม ไม่ถูกนับเป็น 0 (`export.py`) |

---

## 3. Definition of Done — 13 หมวด

| หมวด | สถานะ | หมายเหตุ |
|---|---|---|
| §1 ขอบเขตรุ่นแรก (7) | ⚠️ 6✅ 1⏳ | ครบทุกข้อ; ข้อ Google login ยืนยันด้วย mock เท่านั้น |
| §2 Authentication/Authorization (9) | ✅ 9/9 | 401/403 มีเทสคุม (`test_auth.py`, `test_api_access.py`); logout ล้าง credential |
| §3 Classroom และ Roster (9) | ✅ 9/9 | header/email/แถวซ้ำ validate ครบ, import ไม่ทิ้งข้อมูลครึ่ง ๆ, pending activate ตอน login |
| §4 Assignment และ Criteria (9) | ✅ 9/9 | |
| §5 Pairing Engine (9) | ✅ 9/9 | ยืนยัน 200 คน/10 กลุ่มด้วย `scale.spec.ts` วันนี้ |
| §6 Evaluation และ Submission (10) | ✅ 10/10 | หน้า Group/Individual แยกจากกันจริงแล้ว (G7); progress/deadline/submission ล่าสุด ครบ พร้อม countdown และปุ่ม Save |
| §7 Group Reassignment (6) | ✅ 6/6 | backend เก็บ actor ครบ และ UI โชว์ชื่อนักศึกษา ชื่อกลุ่มเดิม/ใหม่ และผู้สั่งย้ายแล้ว (G8) |
| §8 Scoring (11) | ✅ 11/11 | **"คะแนนระหว่างช่วงประเมินมีสถานะ Interim"** แก้แล้ว (G1); "ยังไม่มีข้อมูล" ก่อน final ✅ (`ScoreWorkspace.tsx:9`) |
| §9 Report และ Export (9) | ✅ 9/9 | formula injection ป้องกันแล้ว + มีเทส; เพิ่มคอลัมน์รวม (G9) และ coverage โชว์ชื่อ subject (G10) |
| §10 UI และ Accessibility (6) | ✅ 6/6 | **ยืนยัน: ไม่มี `alert`/`confirm`/`prompt` ของ browser เลย**; TH/EN, data-testid, focus state ครบ |
| §11 Security และ Data Integrity (7) | ✅ 7/7 | ยืนยัน unique indexes จาก DB จริง; archive snapshot ≥366 วัน |
| §12 Performance และ Reliability (5) | ✅ 5/5 | <2s ยืนยันวันนี้; migration ฐานเปล่า→head ยืนยันวันนี้; k6 เป็นผล 2026-10-17 |
| §13 Verification และการส่งมอบ (9) | ⚠️ 7✅ **2⏳** | เทสเขียวหมด/README/.env.example/docs ✅ · ไม่มี Critical/High defect เปิดอยู่แล้วหลังปิด G1 ✅ · **Google login จริง + product owner acceptance** ยังค้าง |

---

## 4. ช่องว่าง

### ✅ ปิดแล้วบน branch `fix-fr`

| # | เรื่อง | แก้อย่างไร | Commit |
|---|---|---|---|
| **G1** | นักศึกษาไม่เห็นสถานะ Interim (ผิด DoD §8) | `/my-scores` ส่ง `group_final`/`individual_final`; `ScoreWorkspace` แสดง label ทั้งสอง branch; ข้อความ TH ตรง PRD | `fix(scores): show interim state to students` |
| **G2** | ไม่มี Countdown timer (FR-EVAL-10) | hook `useCountdown` + แถบ `evaluation-countdown` นับทุกวินาที | `feat(evaluation): add deadline countdown…` |
| **G3** | ไม่มี progress bar ต่อ criterion (FR-EVAL-07) | `<progress>` ต่อ criterion นับ submitted จริง ไม่ใช่ draft | ↑ commit เดียวกัน |
| **G5** | ไม่เตือนคู่ที่ยังไม่ประเมิน (FR-EVAL-05) | คำเตือนในหน้า + จำนวนคู่ที่ยังว่างใน dialog ยืนยัน | ↑ commit เดียวกัน |
| **G4** | ไม่มีปุ่ม Save (FR-EVAL-04) | ปุ่ม `save-draft` + hook คืนผลสำเร็จจริง จึงยืนยันได้ว่าบันทึกแล้ว; ยังคง autosave ไว้ | `feat(evaluation): separate evaluation pages…` |
| **G6** | layout ไม่ตรง mock (FR-EVAL-02 + FR-EVAL-03 ⚠️) | แถวเดียว `ซ้าย — 5 ระดับ — ขวา`; ≤900px ยุบเป็นชื่อสองฝั่งแถวบน สเกลแถวล่าง | ↑ commit เดียวกัน |
| **G7** | Group/Individual อยู่จอเดียวกัน (FR-EVAL-01 + FR-EVAL-11) | `StudentEvaluationPages` mount ทีละหน้า + page nav; คง disclosure ต่อ assignment ไว้เพื่อ lazy load | ↑ commit เดียวกัน |
| **G8** | ประวัติ reassignment ไม่โชว์ผู้สั่งย้าย + โชว์ raw ID (FR-AUDIT-02) | `/reassignments` ส่ง `student_email`, `old_group_name`, `new_group_name`, `instructor_email`; UI โชว์ "นักศึกษา: กลุ่มเดิม → กลุ่มใหม่ · ย้ายโดย …" | `feat(reports): name reassignment actors…` |
| **G9** | Individual Summary ไม่มีคอลัมน์รวม (FR-EXPORT-02 ⚠️) | เพิ่ม `total_score` = work + participation ทั้งสองส่วน ข้ามส่วนที่ยกเว้น | ↑ commit เดียวกัน |
| **G10** | Coverage table โชว์ ID ไม่ใช่ชื่อ (FR-REPORT-03) | coverage ส่ง `left`/`right` เป็นชื่อกลุ่ม/อีเมล ใช้ labels ชุดเดียวกับ raw pair report; ไฟล์ export ยังใช้ ID เพื่อคง Raw Pairs เป็นชื่อแฝง | ↑ commit เดียวกัน |

เทสที่เพิ่มคุมทั้ง 10 ข้อ: `backend/tests/test_evaluation_api.py` (`test_my_scores_carries_interim_and_final_state`, `test_coverage_rows_name_their_subjects`, `test_individual_summary_export_totals_work_and_participation` และ assertion ใน `test_reassignment_preserves_eligible_pairs_and_records_notifications`), `frontend/e2e/deadline-and-progress.spec.ts` และส่วนที่เพิ่มใน `frontend/e2e/completion.spec.ts`

**ข้อสังเกตที่ควรแจ้งอาจารย์**
- **G7** แยกหน้าแบบ mount ทีละหน้า (page nav) ไม่ได้ทำเป็น URL/route แยก เพราะทั้งแอปยังไม่มี router เลย (การเลือกห้องเรียนก็เป็น state) ถ้าอาจารย์ต้องการ URL แยกจริง ๆ ต้องทำเป็นงาน routing แยกอีกงาน
- **G6** PRD วาดเป็นปุ่มวงกลมเปล่า `( )( )( )( )( )` แต่ยังคงข้อความกำกับแต่ละระดับไว้ (ย่อขนาดลง) เพื่อไม่ให้เสีย accessibility และยังบอกความหมาย 1–5 ได้
- **G4** เพิ่มปุ่ม Save ตาม PRD แต่ไม่ได้ถอด autosave ออก เพราะ autosave มีเทสคุมอยู่และช่วยกันคำตอบหายจริง
- **G10** โชว์ชื่อเฉพาะในหน้า Report ของอาจารย์ (ผ่าน `require_owner`) ส่วนไฟล์ Export ยังใช้ ID ตามเดิม เพื่อไม่ให้อีเมลนักศึกษาหลุดลงไฟล์ที่ FR-EXPORT-03 กำหนดให้เป็นชื่อแฝง

### การ merge `develop`

merge `develop` (`77f9423`) เข้ามาแล้ว — develop เปลี่ยนหัว disclosure ไปใช้ `DisclosureSummary` ร่วมกันและรื้อ instructor pair planner ใหม่
conflict มีจุดเดียวคือหัวของ evaluation section ซึ่ง branch นี้เปลี่ยนเป็นหน้าแยกไปแล้ว (G7) จึงคงโครงหน้าแยกไว้และให้ wrapper ใช้ `DisclosureSummary` ของ develop
เทสของ develop (`instructor-pair-planner.spec.ts`) ผ่านด้วยโครงใหม่นี้ และ layout แถวเดียว (G6) ที่ผมแก้ในหน้าประเมินของอาจารย์ยังอยู่ครบหลัง merge

---

## 5. ช่องว่างในการเทส (เทสเขียวหมด แต่ไม่ได้คุมเรื่องเหล่านี้)

**นี่คือความเสี่ยงที่ควรบอกอาจารย์** — ผ่าน 120 เทสไม่ได้แปลว่าคุมครบ

| เรื่อง | ความเสี่ยง |
|---|---|
| **Deadline ปิดแล้ว (`is_open: false`) ที่ระดับ UI** | **ไม่มี E2E/fixture ไหนทดสอบเลย** — ทุก fixture ใช้ deadline อนาคต (`completion.spec.ts:32`, `evaluation-responsiveness.spec.ts:13`, `scale.spec.ts:14`) ทั้งที่ DoD §6 บังคับ 2 ข้อเรื่องนี้ (ฝั่ง API มีคุมที่ `test_evaluation_api.py:84-95`) |
| **Re-submission** | ทดสอบแค่ submit ครั้งเดียวในหน้า UI ไม่มีการ submit ซ้ำ (DoD §6 บังคับ) |
| `POINTS` choice 2 และ 4 | `0.75/0.25` และ `0.25/0.75` **ไม่เคยถูก assert** — `test_scoring.py` คุมแค่ 1, 3, 5 |
| Individual participation exemption กลุ่ม <3 | คุมแค่ฝั่ง pairing ไม่คุมที่ระดับ report (`reports.py:159`) |
| FR-PAIR-10 + FR-REPORT-03 instructor evaluation UI | ไม่มี spec ไหนแตะ `InstructorEvaluation` เลย |
| Coverage table 9 ฟิลด์ | `<details>` ของ coverage ไม่เคยถูกเปิดใน E2E |

~~`group_final`/`individual_final` ไม่มีเทสอ้างถึง~~ → ปิดแล้ว (เทสใหม่คุม G1 ทั้งฝั่ง API และ UI)

---

## 6. Release gates ที่ต้องใช้เจ้าของโปรเจกต์/อาจารย์เอง

1. **Google Login จริง** ทั้ง Instructor และ Student บน production origin — ยังไม่ทำ (`TASKS.md:100`, DoD §13)
2. **ยืนยัน Vercel production revision** ว่าเป็น `d61ab2b` หรือลูกหลาน (`RELEASE_VERIFICATION.md:35`)
3. **Product owner acceptance** + แนบตัวอย่าง CSV/XLSX, account matrix, known limitations (`DEFINITION_OF_DONE.md:149-158`)

---

*รายงานนี้สร้างจากการอ่านโค้ด (ทุกข้ออ้าง file:line) + รันเทสจริงทั้ง 7 ชุดเมื่อ 2026-10-19*
*การตรวจรอบแรกทำบน `d2c3695` โดยไม่แก้โค้ด จากนั้นแก้ G1–G10 บน branch `fix-fr` merge `develop` (`77f9423`) เข้ามา แล้วรันทั้ง 7 ชุดซ้ำจนเขียวหมด 120 เทส*

---

## ภาคผนวก — การแปลงเลข FR จาก v1.3 เป็น v2.0

ใช้ตารางนี้เมื่อย้อนอ่านรายงานรุ่นก่อน หรือเทียบกับ `git show HEAD:project-idea/pairwise_evaluation_prd.md`

| v1.3 | v2.0 | หมายเหตุ |
|---|---|---|
| FR-AUTH-02 | FR-AUTH-03 | จับคู่ roster ด้วยอีเมลที่ normalize แล้ว |
| FR-AUTH-03 | FR-AUTHZ-01 | v2.0 แยกหมวด authorization ออกมา |
| FR-AUTH-04 | FR-AUTHZ-03 | |
| FR-AUTH-05 | FR-AUTHZ-01 | v2.0 ไม่มี `INSTRUCTOR_EMAILS` — ใช้ role ต่อ classroom (FR-CLASS-06) + hosted domain (FR-AUTH-02) แทน |
| FR-CLASS-03 | FR-CLASS-06 | |
| FR-CLASS-04 | FR-AUTHZ-02 | v2.0 ต้องตอบ 404 ไม่ใช่ 403 |
| FR-ASSIGN-04 | FR-ASSIGN-03 | |
| FR-ASSIGN-05 | FR-ASSIGN-02 + FR-PAIR-12 | |
| FR-PAIR-02 | FR-PAIR-05 | |
| FR-PAIR-03 | FR-PAIR-07 | |
| FR-PAIR-04 / FR-PAIR-07 | FR-PAIR-02 / FR-PAIR-03 | |
| FR-PAIR-08 | FR-PAIR-06 | **เลข FR-PAIR-08 ของ v2.0 เป็นเรื่องอื่น** (สุ่มตำแหน่งซ้าย-ขวา ยังไม่ทำ) |
| FR-PAIR-09..14 | FR-PAIR-11 + FR-AUDIT-02 | **เลข FR-PAIR-14 ของ v2.0 เป็นเรื่องอื่น** (เพดาน workload ฝั่ง individual) — จุดนี้คือที่มาของความสับสน |
| FR-EVAL-06 | FR-EVAL-05 | |
| FR-EVAL-07 / FR-EVAL-10 | FR-EVAL-11 | |
| FR-EVAL-08 | FR-PAIR-03 | |
| FR-EVAL-09 | FR-EVAL-02 | |
| FR-EVAL-11 | FR-EVAL-08 | |
| FR-EVAL-12 | FR-EVAL-09 | |
| FR-EVAL-13 | FR-EVAL-10 | countdown |
| FR-EVAL-14..17 | FR-EVAL-06 | re-submit ไม่จำกัด |
| FR-SCORE-03 | FR-SCORE-02 | |
| FR-SCORE-06..09 | FR-SCORE-03 | |
| FR-SCORE-10 | FR-SCORE-06 | |
| FR-SCORE-11/12/14 | FR-EVAL-06 + FR-REPORT-06 | |
| FR-SCORE-13 | FR-SCORE-07 | label "ชั่วคราว" |
| FR-SCORE-15/16/18 | FR-SCORE-04 | |
| FR-SCORE-17 | FR-EVAL-07 | progress ต่อ criterion |
| FR-SCORE-19/20 | FR-REPORT-06 + FR-ANON-01 | |
| FR-SCORE-21 | FR-EXPORT-03 | |
| FR-REPORT-04 | FR-PAIR-10 | ปุ่ม "ส่งประเมินเพิ่ม" |
| FR-REPORT-05 | FR-REPORT-03 | ปุ่ม "ประเมินเอง" |
| FR-REPORT-07 | FR-REPORT-06 ⚠️ | v2.0 FR-ANON-03 **ห้าม** แสดง delta รายวัน ซึ่ง v1.3 บังคับให้แสดง |
| FR-REPORT-08 | FR-ANON-01 | |
| FR-EXPORT-03/04/05 | FR-EXPORT-03 / FR-EXPORT-05 | |

### requirement ที่ v2.0 เปลี่ยน — ✅ เดิมใช้ยืนยันไม่ได้

| v2.0 | v1.3 เคยกำหนด | v2.0 กำหนดใหม่ |
|---|---|---|
| FR-EVAL-03 | radio 5 ระดับ มีตัวกลาง "เท่ากัน" | 6-point forced choice ไม่มีตัวกลาง (D1) |
| FR-SCORE-02 | normalize ผลรวมทุก item = 1.0 | band mapping `floor + (ceiling − floor) × q` (D2, §9.3) |
| FR-SCORE-04 | ไม่ submit → participation = 0 เป็นคะแนนส่วนแยก | participation multiplier `M` คูณคะแนนทั้งก้อน (D5, §9.4) |
| FR-SCORE-03 | instructor vote นับเป็น vote ซ้ำหลายเสียง | float ใน weighted mean ไม่บิด comparison count (D6) |
| FR-SCORE-06 | คำนวณและ**แสดง**คะแนน individual รายวัน | recompute รายวันได้ แต่ห้ามแสดง delta (FR-ANON-03) |
| FR-EXPORT-02 | Excel 3 sheet | 4 sheet รวม Metadata ที่ระบุเวอร์ชันสูตร |

### ข้อกำหนดของ v2.0 ที่รายงานนี้ไม่ได้ตรวจเลย

v2.0 เพิ่มหมวดที่ v1.3 ไม่มี จึงไม่มีแถวใดในรายงานนี้ครอบคลุม:
FR-PAIR-04/05/08/09/13/14/15 (feasibility, สุ่มตำแหน่ง, เพดาน workload, เตือนขนาดกลุ่ม) ·
FR-SCORE-05/08/09 (`LOW_CONFIDENCE`, override, snapshot) · FR-ANON-02/03/04 (k-anonymity, ห้าม delta) ·
§10 FR-QS-01/02/03 · §7.10 FR-APPEAL-01/02 และ FR-AUDIT-01/03 · §7.9 FR-NOTIF-01…06 ·
FR-PRIV-01…04 · §15 FR-A11Y-01…07 · §12 FR-API-01…05 · §13 NFR ทุกข้อที่เขียนใหม่ให้วัดได้

ดู §19.1 ของ PRD สำหรับสถานะล่าสุดของแต่ละข้อ
