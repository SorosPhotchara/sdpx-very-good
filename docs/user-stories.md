# User Stories

> ที่มา: [prd.md](prd.md) (PRD v2.0) · คำถามที่ยังค้าง: [open-questions.md](open-questions.md)

---

## US-AUTH-01 — Login ด้วย Google Account ของมหาวิทยาลัย

**Requirement:** FR-AUTH-01, FR-AUTH-02, FR-AUTH-03, FR-CLASS-04
**Endpoints:** `GET /api/auth/google/start`, `GET /api/auth/google/callback`, `GET /api/auth/me`, `GET /api/classrooms` ([openapi.yaml](openapi.yaml))

### User Story

As a student or Instructor, I want to login with my University Google Account, so that I don't need to create any account.

### Acceptance Criteria

- Given the user is not logged in, when they open any page other than the login page,
  then they are redirected to the login page, which has a "Sign in with Google" button and no password field.
- Given the user signs in with an email outside the allowed university domain (`somebody@gmail.com`), when Google returns them to the system,
  then login is rejected with a message saying only university accounts are allowed, and no session is created.
- Given the roster contains `Somchai+pw@kmitl.ac.th`, when the user signs in as `somchai@kmitl.ac.th`,
  then the account is matched to that roster entry, the classroom appears on the dashboard, and no duplicate user is created.

### รอคำตอบก่อนแก้ AC

| เรื่อง | ผลต่อ AC |
|---|---|
| FR-AUTH-03 บอกให้ตัด dot เฉพาะ gmail แต่ตัวอย่างในข้อเดียวกันตัด dot ของอีเมลมหาวิทยาลัยด้วย | ถ้าตัด dot ทุก domain ต้องเพิ่ม AC เรื่อง dot |

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้ (email normalization: ตัวพิมพ์เล็กใหญ่ และ `+tag`)
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-AUTH-02 — กดยกเลิกหรือเกิด error ที่หน้า Google sign-in

**Requirement:** FR-AUTH-01, NFR-OBS-01
**Endpoints:** `GET /api/auth/google/start`, `GET /api/auth/google/callback` ([openapi.yaml](openapi.yaml))

### User Story

As a student or Instructor who cancels on the Google sign-in screen, I want to return to Pairwise with a clear message and a way to try again,
so that I'm not stuck in a redirect loop and can sign in with the correct account.

### Acceptance Criteria

- Given the user presses Cancel on the Google consent screen, when Google redirects them back with `error=access_denied`,
  then they see the login page with the message "You have not signed in" and a "Sign in with Google" button,
  no session is created, and the system does not redirect them to Google again automatically.
- Given the user is on the login page after cancelling, when they press "Sign in with Google" again,
  then Google shows the account chooser so they can pick a different account.
- Given Google returns an error other than `access_denied` (e.g. `server_error`), when the user is redirected back,
  then they see "Couldn't sign in with Google. Please try again." with a retry button, no session is created,
  and the error is logged with a `requestId`.
- Given the sign-in callback arrives with a missing `state`, or a `state` different from the one the system issued, when it is processed,
  then login is rejected and no session is created.

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้ (ตรวจ `state` และแยกประเภท error จาก Google)
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-CLASS-01 — Import roster จาก CSV

**Requirement:** FR-CLASS-01, FR-CLASS-02, FR-CLASS-03, FR-CLASS-04, FR-AUTH-03, FR-SEC-04, FR-AUTHZ-01/02

### User Story

As an Instructor, I want to create a classroom and import the student list as a CSV
(`email`, `group_name`, `student_id` optional, `display_name` optional),
so that setting up a class is faster than adding students one by one.

### กติกาที่ใช้ร่วมกันทุก AC

- **เลขแถว** = เลขแถวที่ Excel แสดง — header คือ row 1 ข้อมูลแถวแรกคือ row 2
- **Normalize อีเมล** ใช้กฎเดียวกับ FR-AUTH-03 (lowercase, ตัด dot ใน gmail, ตัด `+tag`)
- **Normalize ชื่อกลุ่ม** = trim, ยุบช่องว่างซ้อนเหลือช่องเดียว, เทียบแบบไม่สนตัวพิมพ์ — ชื่อที่แสดงใช้ตัวสะกดจากแถวแรกที่เจอ
- **Atomic:** ถ้ามี error แม้แต่ข้อเดียว ไม่มีข้อมูลใดถูกบันทึก (รวมถึง classroom, group, user `PENDING`)

### Acceptance Criteria

**Header**

1. Given CSV ที่ header ต่างกันแค่ตัวพิมพ์ (`Email`, `GROUP_NAME`), When import, Then header ถูกยอมรับ
2. Given header มีช่องว่างหน้า/หลัง (` email `) หรือสลับลำดับคอลัมน์, When import, Then ยอมรับ
3. Given ไม่มีคอลัมน์ `student_id` และ `display_name`, When import, Then ยอมรับ
4. Given มีคอลัมน์ที่ไม่รู้จัก (เช่น `phone`), When import, Then ข้ามคอลัมน์นั้น และรายงานเตือนชื่อคอลัมน์ที่ถูกข้าม
5. Given ไม่มีคอลัมน์ `email` หรือ `group_name` หรือมี header ซ้ำ, When import, Then reject ทั้งไฟล์และระบุชื่อคอลัมน์ที่ขาด/ซ้ำ

**รูปแบบไฟล์**

6. Given ไฟล์ UTF-8 with BOM (แบบที่ Excel และ FR-EXPORT-01 สร้าง), When import, Then อ่าน header แรกเป็น `email` ได้ถูกต้อง
7. Given ไฟล์ที่ไม่ใช่ UTF-8 ที่ถูกต้อง (เช่น Windows-874), When import, Then reject พร้อมข้อความให้ save เป็น "CSV UTF-8"
8. Given `display_name` อยู่ในเครื่องหมายคำพูดและมี comma (`"Somchai, A."`) หรือไฟล์ใช้ CRLF, When import, Then อ่านค่าได้ครบและคอลัมน์ไม่เลื่อน
9. Given มีแถวว่างทั้งแถว (`,,,`) ท้ายไฟล์หรือกลางไฟล์, When import, Then ข้ามแถวนั้นโดยไม่นับเป็น error — เลขแถวที่รายงานยังตรงกับ Excel
10. Given ไฟล์ว่าง หรือมีแต่ header, When import, Then reject ด้วยข้อความ "ไม่มีรายชื่อนักศึกษา" และไม่สร้าง classroom
11. Given ไฟล์เกิน 1 MB หรือเกิน 1,000 แถวข้อมูล, When import, Then reject พร้อมบอกเพดาน — ไม่ใช่ 413/timeout ที่ไม่มีข้อความ

**ข้อมูลรายแถว**

12. Given CSV 100 แถว มี row 42 อีเมลผิดรูปแบบ, When import, Then ไม่มีแถวใดถูกบันทึก และรายงานระบุ "row 42"
13. Given มีหลายแถวผิด (row 42 อีเมลผิด, row 58 `group_name` ว่าง), When import, Then รายงาน **ทุกแถว** ในครั้งเดียว จัดกลุ่มตามประเภท error (FR-CLASS-03) — แสดงสูงสุด 100 รายการพร้อมจำนวนที่เหลือ
14. Given row 12 = `Somchai.A+x@gmail.com` และ row 57 = `somchaia@gmail.com`, When import, Then reject เป็นอีเมลซ้ำ และระบุทั้ง row 12 และ row 57
15. Given row 5 = `Group 1` และ row 9 = `group 1 `, When import, Then ทั้งสองแถวอยู่กลุ่มเดียวกัน
16. Given `student_id` = `0012345`, When import, Then เก็บเป็น `0012345` (string ไม่ตัด 0 นำหน้า)
17. Given `student_id` อยู่ในรูป scientific notation (`6.5E+09`), When import, Then reject แถวนั้นพร้อมข้อความว่า Excel แปลงรหัสเป็นตัวเลข
18. Given `display_name` ขึ้นต้นด้วย `=`, `+`, `-` หรือ `@`, When import แล้ว export, Then ค่าถูก escape ไม่ถูกตีความเป็นสูตร (FR-SEC-04) — ชื่อที่ขึ้นต้นด้วย `-` ต้องไม่ถูก reject

**ผลลัพธ์และ user**

19. Given import ผ่าน, When เสร็จ, Then แสดงสรุปจำนวนนักศึกษาและรายชื่อกลุ่มพร้อมจำนวนสมาชิกต่อกลุ่ม
20. Given อีเมลที่ยังไม่มี user, When import ผ่าน, Then สร้าง user สถานะ `PENDING` (FR-CLASS-04)
21. Given อีเมลที่มี user อยู่แล้ว (จาก classroom อื่น), When import ผ่าน, Then ใช้ user เดิม ไม่สร้างใหม่ และไม่เขียนทับ `display_name` ของ user นั้น

**สิทธิ์และ concurrency**

22. Given ผู้ใช้เป็น Owner, Co-teacher หรือ TA ของ classroom (role matrix §3), When import, Then ทำได้
23. Given Student เรียก `POST /api/classrooms/{id}/roster:import` ตรง ๆ, Then ได้ 403
24. Given ผู้ใช้ไม่ได้อยู่ใน classroom นั้น, When import, Then ได้ 404 (FR-AUTHZ-02)
25. Given ส่ง request import เดียวกันซ้ำ 2 ครั้งพร้อมกัน (กดปุ่มสองที), When เสร็จ, Then มี roster ชุดเดียว ไม่มีกลุ่มซ้ำ

### รอคำตอบก่อนเขียน AC

| เรื่อง | คำถาม |
|---|---|
| กลุ่มที่มีสมาชิก < 2 เป็น error (reject) หรือ warning | [Q4](open-questions.md#q4--กลุ่มที่มีสมาชิก--2-คน-reject-หรือเตือน) |
| Import ซ้ำเข้า classroom ที่มี roster แล้ว | [Q5](open-questions.md#q5--import-ซ้ำเข้า-classroom-ที่มี-roster-อยู่แล้ว) |
| อีเมลนอก domain / อีเมลของ staff ใน classroom | [Q6](open-questions.md#q6--อีเมลใน-csv-ที่ไม่ควรเป็นนักศึกษา) |

### Out of scope

- Upsert พร้อม diff (FR-CLASS-05, Should) — story แยก
- Import ไฟล์ `.xlsx` — ตรวจ content จริง ไฟล์ที่ไม่ใช่ CSV text ให้ reject

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้ — อย่างน้อย AC 1–18 (parser + validator)
- [ ] มี integration test ว่า import เป็น atomic (AC 12) และสิทธิ์ถูกต้อง (AC 23–24)
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-ASSIGN-01 — สร้าง Assignment และเกณฑ์การประเมิน

**Requirement:** FR-ASSIGN-01, FR-ASSIGN-02, FR-AUTHZ-01
**Endpoints:** `POST /api/assignments`, `GET /api/classrooms/{classroomId}/assignments`, `POST /api/assignments/{assignmentId}:publish` ([openapi.yaml](openapi.yaml))

### User Story

As an instructor (Owner or Co-teacher), I want to create an assignment with its maximum scores, deadlines, and evaluation criteria for each side,
so that students evaluate against clear criteria and the computed scores are weighted correctly.

### Acceptance Criteria

- Given the instructor fills in the name, description, artifact link, group_max_score, individual_max_score, and both deadlines,
  when they save, then the assignment is created with status `DRAFT` and appears in the classroom's assignment list.
- Given the group criteria are UX 40%, Completeness 35%, Innovation 20% (95% total), when the instructor publishes,
  then publishing is rejected with the message "Group criteria total 95%; must equal 100%", and the assignment stays in `DRAFT`.
- Given the group criteria total 99.99%, when the instructor publishes, then the weight check passes;
  given they total 99.98%, when the instructor publishes, then it is rejected.

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-PUBLISH-01 — ดู Feasibility แล้ว Publish

**Requirement:** FR-PAIR-01, FR-PAIR-04, FR-PAIR-05, FR-PAIR-07, §8.2
**Endpoints:** `GET /api/assignments/{assignmentId}/feasibility`, `POST /api/assignments/{assignmentId}:publish` ([openapi.yaml](openapi.yaml))

### User Story

As an instructor, I want to see the feasibility (coverage, workload per student, total comparisons) before publishing an assignment,
so that I know in advance how many pairs each student must evaluate, and if the target is impossible I get the reason in numbers instead of a silent reduction.

### Acceptance Criteria

- Given the instructor has reviewed the feasibility view, when they publish,
  then the assignment status becomes `PUBLISHED`, the number of pair assignments generated equals the total comparisons shown in the feasibility view,
  and no evaluator receives the same pair twice within a criterion.
- Given a classroom with 12 students in 3 groups (4 each) and target coverage = 5, when the instructor opens the feasibility view,
  then coverage is reduced to 4, workload is set to 1 pair per criterion, and the reason is shown in numbers:
  "Each pair has only 4 eligible evaluators, so the maximum coverage is 4 per pair (not 5)."

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-EVAL-01 — ประเมินคู่กลุ่ม (Group Evaluation)

**Requirement:** FR-EVAL-01, FR-EVAL-03, FR-EVAL-04, D1
**Endpoints:** `GET /api/assignments/{assignmentId}/my-evaluations?side=GROUP`, `PUT /api/comparisons/{pairAssignmentId}` ([openapi.yaml](openapi.yaml))

### User Story

As a student, I want to evaluate group pairs for every criterion on one page, using options with clear text labels, with my answers saved automatically,
so that I finish quickly, don't have to interpret numbers, and don't lose answers if my connection drops or I close the page midway.

### Acceptance Criteria

- Given the assignment has 3 group criteria (UX, Completeness, Innovation) and the student has 2 pairs per criterion,
  when they open the Group Evaluation page,
  then all 3 criteria appear on one page as 3 sections, each with 2 comparisons.
- Given a comparison on the Group Evaluation page, when it is displayed,
  then it has 6 options with no "equal" option, and every radio has a text accessible name
  ("Left much better" to "Right much better"), not just a number.
- Given the student selects an answer in a comparison, when no more than 2 seconds pass,
  then the draft is saved and "Saved at HH:MM" is shown;
  and after closing the browser and reopening the page, the previous answer is still there.

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-EVAL-02 — Submit และ re-submit คำตอบ

**Requirement:** FR-EVAL-05, FR-EVAL-06, FR-EVAL-08, FR-EVAL-09, FR-API-02
**Endpoints:** `POST /api/assignments/{assignmentId}/submissions` ([openapi.yaml](openapi.yaml))

### User Story

As a student, I want to submit my answers even if some are unanswered, and re-submit before the deadline,
so that I can hand in what I have finished, change answers when I change my mind, and be sure the system uses my latest answers.

### Acceptance Criteria

- Given the deadline for that side has passed, when the student presses Submit,
  then the request is rejected with error code `DEADLINE_PASSED`, the last submitted answers remain the ones used for scoring, and the page shows the answers read-only.
- Given the student presses Submit twice in a row with the same `Idempotency-Key`, when the system receives both requests,
  then only one submission is recorded and history grows by only 1 version.

### ยังไม่มี AC

พฤติกรรมหลักตาม user story ยังไม่มี AC — ควรเพิ่มก่อนเริ่ม Sprint:

- Submit ทั้งที่ยังตอบไม่ครบ (FR-EVAL-05)
- Re-submit แล้วคะแนนใช้คำตอบล่าสุด และเก็บทุกเวอร์ชัน (FR-EVAL-06)

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-SCORE-01 — นักศึกษาดูคะแนนของตัวเอง

**Requirement:** FR-REPORT-06, FR-ANON-01, FR-ANON-02, FR-ANON-03, FR-SCORE-06, FR-SCORE-07, FR-SCORE-13
**Endpoints:** `GET /api/assignments/{assignmentId}/my-score` ([openapi.yaml](openapi.yaml))

### User Story

As a student, I want to see my group score, my individual score, and my participation,
so that I know my evaluation results without anyone learning who scored whom.

### Acceptance Criteria

- Given 2 teammates have submitted evaluations that include me (k_min = 3), when I open my score page,
  then the individual score shows "Not enough data yet" instead of a number;
  and once a 3rd teammate submits, the individual score is shown as a number.
- Given the assignment is not finalized, when I open my score page,
  then every score carries the label "Interim — may change", my current participation (p) and multiplier (M) are shown,
  and only current values appear, with no history chart or change since yesterday.

### ต้องแก้ / รอคำตอบ

| เรื่อง | รายละเอียด |
|---|---|
| AC1 "once a 3rd teammate submits" | คะแนน interim คำนวณใหม่ตอน 02:00 หรือเมื่ออาจารย์กด (FR-SCORE-06) ไม่ใช่ทันที — ควรเขียนเป็น "once a 3rd teammate submits **and scores are next recomputed**" |
| k_min นับอาจารย์ด้วยไหม | AC นับเฉพาะ teammates — รอคำตอบ [Q3](open-questions.md#q3--comparison-ของอาจารย์นับเข้าเกณฑ์ขั้นต่ำหรือไม่) |
| นักศึกษาเห็นคะแนนกลุ่มเมื่อไหร่ | FR-REPORT-06 ไม่ระบุเวลา — ตอนนี้ spec แสดงคะแนนกลุ่ม interim ได้เลย ดูคำถามสำรองใน [open-questions.md](open-questions.md) |

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง

---

## US-REPORT-01 — อาจารย์ดูรายงาน Group Summary

**Requirement:** FR-REPORT-01, FR-SCORE-05, FR-SCORE-07, FR-AUTHZ-01, §9.5
**Endpoints:** `GET /api/assignments/{assignmentId}/reports/group` ([openapi.yaml](openapi.yaml))

### User Story

As an instructor, I want to see every group's score broken down by criterion, with comparison counts and flags,
so that I can check how much each group scored and why, and know which groups still lack enough data.

### Acceptance Criteria

- Given a group received fewer than 3 comparisons on UX (min_comparisons = 3),
  when the instructor opens the Group Summary report,
  then that group's UX cell carries the `LOW_CONFIDENCE` flag.
- Given the assignment is not finalized, when the instructor opens the report,
  then every score carries the label "Interim — may change".

### ยังไม่มี AC

- ตัวเลขคะแนนถูกต้องตาม §9.5 (Aurora: 5.328 / 4.305 / 3.165 = 12.798 / 15) — เป็น golden test ตาม NFR-MAINT-01 และเป็นเหตุผลหลักของ story ("how much each group scored")
- นักศึกษาเรียก endpoint นี้ตรง ๆ แล้วได้ 403 (FR-AUTHZ-01)

### Definition of Done

- [ ] Feature ทำงานได้ตาม acceptance criteria
- [ ] มี unit test ครอบคลุม business rule ของ story นี้
- [ ] มี E2E test สำหรับ AC อย่างน้อย 1 ข้อ (จะทำจริงใน WS-04)
- [ ] Code ผ่าน review จากสมาชิกในกลุ่ม
- [ ] Deploy ขึ้น staging แล้วเปิดใช้ได้จริง
