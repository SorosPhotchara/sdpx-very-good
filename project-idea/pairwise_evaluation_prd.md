# Product Requirements Document
## Pairwise Evaluation System (PairEval)

**Version:** 1.3
**Date:** October 2026
**Status:** DoD-aligned draft; implementation gaps tracked in TASKS.md

---

## 1. Overview

### 1.1 Product Vision

PairEval เป็นระบบประเมินผลนักศึกษาแบบ Pairwise Comparison ที่ช่วยให้การให้คะแนนมีความเป็นธรรมและลดอคติ โดยแทนที่การให้คะแนนตัวเลขโดยตรง ด้วยการเปรียบเทียบคู่ (A vs B) แล้วคำนวณคะแนนจากผลรวม ระบบรองรับทั้งการประเมินระดับกลุ่มและระดับบุคคล

### 1.2 Target Users

| User Role | Description |
|---|---|
| Instructor | อาจารย์ผู้สอน (มีได้มากกว่า 1 คนต่อ Classroom) |
| Student | นักศึกษาในชั้นเรียน |

### 1.3 Key Principles

- การประเมินเป็นแบบ **Pairwise Comparison** เท่านั้น (ไม่มีการให้คะแนนตรง)
- ทุก combination ที่ถูกต้องต้องได้รับมอบหมายให้ Student ผู้ประเมินที่เข้าเกณฑ์ไม่ซ้ำกัน `min(5, จำนวนผู้ประเมินที่เข้าเกณฑ์)` คนต่อ criterion ก่อนกระจายงานให้ใกล้เคียงกัน; ถ้ามีไม่ถึง 5 คนยัง Publish ได้ และ Report แสดงจำนวนที่ทำได้จริง จำนวนที่ส่งจริง และจำนวนที่ขาดจาก 5 คน
- นักศึกษา/กลุ่มห้ามประเมินตนเอง
- ระบบ Save ก่อน Submit ได้
- **Individual Score** อัปเดตแบบ rolling ทุกวัน เจ้าตัวเห็น progress ได้ตลอดจนถึง deadline
- **Instructor evaluation weight** กำหนดได้ต่อ Assignment (ค่า default = 1.0 แต่ปรับได้)
- รองรับ Export คะแนนเป็น CSV และ Excel
- **Peer anonymity:** นักศึกษาไม่เห็นว่าใครประเมินตนเอง (anonymous evaluations)
- **Partial submission:** ได้คะแนนการมีส่วนร่วมแยกตามสัดส่วน assigned pairs ที่ Submit ก่อน deadline; หลัง deadline ส่งเพิ่มไม่ได้
- **Re-submission:** นักศึกษา submit ใหม่ได้ทุกวันก่อน deadline โดยใช้คะแนน submission ล่าสุด
- **Group re-assignment:** เปลี่ยนกลุ่มได้ก่อน deadline โดยคง pair ที่ยังถูกต้องและ supersede เฉพาะ pair ที่ใช้ไม่ได้
- **Instructor weight:** ใช้ค่าเดียวสำหรับทั้ง Group และ Individual criteria

---

## 2. User Stories

### 2.1 Instructor

| ID | Story |
|---|---|
| I-01 | ในฐานะอาจารย์ ฉันต้องการสร้าง Classroom และเพิ่มนักศึกษาผ่าน CSV (columns: email, groupname) |
| I-02 | ในฐานะอาจารย์ ฉันต้องการเพิ่มอาจารย์ท่านอื่นเข้า Classroom ได้ |
| I-03 | ในฐานะอาจารย์ ฉันต้องการสร้าง Assignment พร้อมกำหนด criteria การให้คะแนน |
| I-04 | ในฐานะอาจารย์ ฉันต้องการกำหนดคะแนนรวม แบ่งเป็น Group Score และ Individual Score |
| I-05 | ในฐานะอาจารย์ ฉันต้องการกำหนด % น้ำหนักของแต่ละ criteria ภายใน Group/Individual |
| I-06 | ในฐานะอาจารย์ ฉันต้องการกำหนด Deadline สำหรับการประเมิน |
| I-07 | ในฐานะอาจารย์ ฉันต้องการประเมินแต่ละกลุ่มด้วย pairwise |
| I-08 | ในฐานะอาจารย์ ฉันต้องการส่งบางคู่ให้ evaluator เพิ่มเติม X คน (เช่น 3 คน) |
| I-09 | ในฐานะอาจารย์ ฉันต้องการดู Report คะแนนรวมของทุกกลุ่มและทุกคน |
| I-10 | ในฐานะอาจารย์ ฉันต้องการดู Report ครอบคลุม: ทุก pair, จำนวน evaluation, คะแนนรวมต่อ criteria |
| I-11 | ในฐานะอาจารย์ ฉันต้องการกำหนด Instructor Evaluation Weight สำหรับแต่ละ Assignment |
| I-12 | ในฐานะอาจารย์ ฉันต้องการ Export คะแนนทั้งหมดเป็น CSV หรือ Excel |
| I-13 | ในฐานะอาจารย์ ฉันต้องการย้ายกลุ่มนักศึกษาก่อน deadline โดยรักษา pair และ submission ที่ยังถูกต้อง |

### 2.2 Student

| ID | Story |
|---|---|
| S-01 | ในฐานะนักศึกษา ฉันต้องการ Login ด้วย Google Account และเห็น Classroom ที่ตัวเองสังกัด |
| S-02 | ในฐานะนักศึกษา ฉันต้องการประเมินกลุ่มอื่น (Group Evaluation) ผ่าน Pairwise comparison |
| S-03 | ในฐานะนักศึกษา ฉันต้องการประเมินเพื่อนร่วมกลุ่ม (Individual Evaluation) ผ่าน Pairwise comparison |
| S-04 | ในฐานะนักศึกษา ฉันต้องการ Save คำตอบก่อน Submit |
| S-05 | ในฐานะนักศึกษา ฉันต้องการเห็นคะแนนกลุ่มของตัวเอง (หลัง deadline หรือแบบ rolling) |
| S-06 | ในฐานะนักศึกษา ฉันต้องการเห็นคะแนนส่วนบุคคลของตัวเอง แบบ real-time ทุกวัน |
| S-07 | ในฐานะนักศึกษาที่ไม่ประเมิน ฉันยอมรับว่าจะได้คะแนนการมีส่วนร่วม 0 ยกเว้นส่วน Individual ที่ได้รับการยกเว้น |
| S-08 | ในฐานะนักศึกษา ฉันต้องการ re-submit คำตอบได้ทุกวันก่อน deadline โดยระบบใช้คะแนน submission ล่าสุด |
| S-09 | ในฐานะนักศึกษา ฉันไม่ต้องการเห็นว่าใครประเมินตัวฉัน (anonymous) |

---

## 3. System Architecture Overview

```
[Student / Instructor]
        |
   Google OAuth
        |
  [Web Application]
   /            \
[Evaluation UI]  [Report UI]
        |
  [API Layer]
   /      \
[Pairing   [Scoring
 Engine]    Engine]
        |
   [Database]
```

---

## 4. Functional Requirements

### 4.1 Authentication

- **FR-AUTH-01:** Login ด้วย Google OAuth 2.0 เท่านั้น
- **FR-AUTH-02:** ระบบตรวจสอบ email กับรายชื่อใน Classroom โดยอัตโนมัติ
- **FR-AUTH-03:** Instructor มีสิทธิ์แตกต่างจาก Student โดยสิ้นเชิง
- **FR-AUTH-04:** Instructor คนเดียวกันสามารถเป็น Instructor ในหลาย Classroom
- **FR-AUTH-05:** อีเมล Instructor ต้องอยู่ใน `INSTRUCTOR_EMAILS` ก่อนรับสิทธิ์ และ Backend ตรวจ Google ID token ทุกครั้งที่เรียก protected API

### 4.2 Classroom Management

- **FR-CLASS-01:** Instructor สร้าง Classroom พร้อม upload CSV (columns: `email`, `groupname`)
- **FR-CLASS-02:** ระบบ parse CSV และจัดกลุ่มนักศึกษาตาม `groupname` อัตโนมัติ
- **FR-CLASS-03:** Instructor เพิ่มได้เฉพาะอีเมลใน allowlist และห้ามลบ Instructor คนสุดท้ายของ Classroom
- **FR-CLASS-04:** Student เห็นเฉพาะ Classroom ที่ email ตนเองอยู่ใน CSV

### 4.3 Assignment Management

- **FR-ASSIGN-01:** Instructor สร้าง Assignment โดยกำหนด:
  - ชื่อ Assignment
  - คะแนนรวม (เช่น 20 คะแนน) = Group work + Individual work + Group participation + Individual participation
  - คะแนนเต็ม Group work (เช่น 12 คะแนน)
  - คะแนนเต็ม Individual work (เช่น 4 คะแนน)
  - คะแนนเต็มการมีส่วนร่วม Group และ Individual แยกกัน (เช่น 2 + 2 คะแนน)
  - Deadline สำหรับ Group Evaluation
  - Deadline สำหรับ Individual Evaluation
- **FR-ASSIGN-02:** ภายใน Group Score กำหนด Criteria + % น้ำหนัก (รวมต้องได้ 100%)
  - ตัวอย่าง: UI 40%, Completeness 35%, Innovation 25%
- **FR-ASSIGN-03:** ภายใน Individual Score กำหนด Criteria + % น้ำหนัก (รวมต้องได้ 100%)
  - ตัวอย่าง: Teamwork 50%, Management 50%
- **FR-ASSIGN-04:** Instructor แก้ setup ได้ก่อน Publish หรือก่อนเงื่อนไข deadline ที่ระบบกำหนด; Student เห็นเฉพาะ Assignment ที่ Publish แล้ว
- **FR-ASSIGN-05:** Publish ต้องผ่านการตรวจว่าน้ำหนัก criteria แต่ละส่วนรวม 100% และ Classroom มีอย่างน้อย 3 กลุ่ม; กลุ่มที่มีสมาชิกน้อยกว่า 3 คนไม่เปิด Individual Evaluation และสมาชิกไม่เสียคะแนนการมีส่วนร่วมส่วนนั้น

### 4.4 Pairing Engine

#### 4.4.1 Group Evaluation Pairs

- **FR-PAIR-01:** สำหรับแต่ละ Criteria ของ Group Evaluation ระบบสุ่มคู่กลุ่ม (A vs B) โดย:
  - ไม่จับคู่กลุ่มกับตัวเอง
  - ครอบคลุมทุก Combination (nC2 pairs)
  - การจัดสรรเริ่มต้นของแต่ละ combination/criterion ใช้ Student ผู้ประเมินที่เข้าเกณฑ์ไม่ซ้ำกัน `min(5, จำนวนผู้ประเมินที่เข้าเกณฑ์)` คน
- **FR-PAIR-02:** จำนวนคู่ต่อ evaluator ต่อ criterion ปรับตาม coverage ที่ต้องการและจำนวนผู้ประเมินที่มี ไม่จำกัดตายตัวที่ 5 คู่
- **FR-PAIR-03:** Student หนึ่งคนมีคู่/criterion เดิมที่ยังมีผลได้ไม่เกินหนึ่งรายการ; คู่ที่ supersede แล้วอยู่ในประวัติแต่ไม่นับเป็นเสียงเพิ่ม ระบบให้ coverage ตามเป้าหมายที่ทำได้จริงก่อน แล้วกระจายจำนวนงานต่อ evaluator ให้ใกล้เคียงกัน
- **FR-PAIR-04:** กลุ่มของ evaluator ห้ามประเมินกลุ่มตัวเอง

#### 4.4.2 Individual Evaluation Pairs

- **FR-PAIR-05:** สำหรับแต่ละ Criteria ของ Individual Evaluation นักศึกษาแต่ละคนประเมิน **เพื่อนร่วมกลุ่มเท่านั้น**
- **FR-PAIR-06:** ระบบจัดคู่บุคคลภายในกลุ่มตามเป้าหมาย coverage ก่อน แล้วกระจายงานต่อ evaluator ให้ใกล้เคียงกัน
- **FR-PAIR-07:** ไม่มีการประเมินตนเอง (ห้าม self-evaluation)
- **FR-PAIR-08:** ทุก combination ภายในกลุ่มได้รับมอบหมายให้ Student ที่เข้าเกณฑ์ไม่ซ้ำกัน `min(5, จำนวนผู้ประเมินที่เข้าเกณฑ์)` คนต่อ criterion; กลุ่มที่มีสมาชิก 3 คนจึงมีผู้ประเมินที่เข้าเกณฑ์เพียง 1 คนต่อคู่

#### 4.4.3 Group Re-assignment

- **FR-PAIR-09:** Instructor สามารถเปลี่ยนกลุ่มนักศึกษาได้ก่อน deadline
- **FR-PAIR-10:** เมื่อย้ายกลุ่ม ระบบคง pair เดิมที่ยังถูกต้อง และสร้าง pair ทดแทนเฉพาะส่วนที่ได้รับผลกระทบ
- **FR-PAIR-11:** Pair ที่ใช้ไม่ได้ถูก supersede โดยไม่ลบประวัติ; submission ของ pair นั้นไม่นำไปคำนวณ
- **FR-PAIR-12:** ระบบเตือน Instructor ก่อนย้ายเมื่อ pair หรือ submission ได้รับผลกระทบ
- **FR-PAIR-13:** Student ที่ได้รับผลกระทบเห็น notification ให้ทำรายการใหม่
- **FR-PAIR-14:** ระบบบันทึกผู้สั่งย้าย เวลา กลุ่มเดิม และกลุ่มใหม่สำหรับ audit

#### 4.4.4 Coverage Algorithm (Conceptual)

```
Input: N items (groups or individuals), desired_coverage = 5

total_pairs = N*(N-1)/2
For each criterion and subject pair:
  eligible = distinct eligible student evaluators
  target_evaluations = min(desired_coverage, len(eligible))
  assign target_evaluations different students, lowest workload first

Publish may proceed with target_evaluations < 5 when other publication rules pass
Keep at most one active assignment per student and criterion/subject pair
Balance workload after achievable coverage; use a seed for reproducible tests
Track distinct submitted student votes separately from assignments and instructor votes
```

### 4.5 Evaluation UI

#### 4.5.1 Group Evaluation Page

- **FR-EVAL-01:** หน้าเดียวแสดงทุก Criteria ของ Group Evaluation
- **FR-EVAL-02:** แต่ละ Criteria แสดงคู่ที่ได้รับมอบหมาย เรียงต่อกัน รูปแบบ:

```
[Criteria Name]
 Group A  ( ) ( ) ( ) ( ) ( )  Group B
 Group C  ( ) ( ) ( ) ( ) ( )  Group D
...

Example:
User Experience:
 Group A  ( ) ( ) ( ) ( ) ( )  Group B
 Group C  ( ) ( ) ( ) ( ) ( )  Group D
...

Completeness:
 Group A  ( ) ( ) ( ) ( ) ( )  Group D
 Group B  ( ) ( ) ( ) ( ) ( )  Group E
...
```

- **FR-EVAL-03:** Radio buttons 5 ระดับ (1=ซ้ายดีกว่ามาก, 3=เท่ากัน, 5=ขวาดีกว่ามาก)
- **FR-EVAL-04:** ปุ่ม **Save** บันทึก draft ได้ตลอดเวลาก่อน submit
- **FR-EVAL-05:** ปุ่ม **Submit** ส่ง draft ล่าสุดของทุกคู่ในหน้านั้น; แก้และ Submit ใหม่ได้ก่อน deadline
- **FR-EVAL-06:** ระบบเตือนหากยังมีคู่ที่ยังไม่ได้ประเมิน

#### 4.5.2 Individual Evaluation Page

- **FR-EVAL-07:** หน้าแยกต่างหากจาก Group Evaluation
- **FR-EVAL-08:** แสดงเฉพาะเพื่อนในกลุ่มตัวเอง
- **FR-EVAL-09:** แต่ละ Criteria แสดงคู่ที่ได้รับมอบหมาย รูปแบบเดียวกับ Group
- **FR-EVAL-10:** ปุ่ม Save / Submit แยกกันจาก Group Evaluation

#### 4.5.3 Deadline Enforcement

- **FR-EVAL-11:** หลัง Deadline ระบบปิดทั้ง Save และ Submit
- **FR-EVAL-12:** Draft ที่ Save ไว้แต่ยังไม่ Submit ไม่นับเป็นการประเมินและไม่เพิ่มคะแนนการมีส่วนร่วม
- **FR-EVAL-13:** แสดง Countdown timer และ Deadline ชัดเจน

#### 4.5.4 Re-submission Policy

- **FR-EVAL-14:** นักศึกษาสามารถ re-submit ได้กี่ครั้งก็ได้ก่อน deadline
- **FR-EVAL-15:** ระบบเก็บ submission ทุกครั้ง แต่ใช้เฉพาะ **submission ล่าสุด** (latest submitted_at) ในการคำนวณคะแนน
- **FR-EVAL-16:** หน้า Evaluation แสดง timestamp ของ submission ล่าสุด เพื่อให้นักศึกษาทราบว่าคำตอบล่าสุดถูกบันทึกแล้ว
- **FR-EVAL-17:** Group Evaluation และ Individual Evaluation มี re-submission policy แยกกัน (submit ใหม่ในหน้าใดก็ใช้ latest ของหน้านั้น)

### 4.6 Scoring Engine

#### 4.6.1 Pairwise Score Calculation

แต่ละผลการเปรียบเทียบ A vs B (1–5) แปลงเป็น point:

| เลือก | A ได้ | B ได้ |
|---|---|---|
| 1 (A ดีกว่ามาก) | 1.0 | 0.0 |
| 2 (A ดีกว่า) | 0.75 | 0.25 |
| 3 (เท่ากัน) | 0.5 | 0.5 |
| 4 (B ดีกว่า) | 0.25 | 0.75 |
| 5 (B ดีกว่ามาก) | 0.0 | 1.0 |

- **FR-SCORE-01:** คะแนนรวมต่อ item = sum ของ points ที่ได้รับ / จำนวนครั้งที่ถูกประเมิน
- **FR-SCORE-02:** normalize ให้ผลรวมของทุก item ใน criteria = 1.0 (relative score)
- **FR-SCORE-03:** คะแนน criteria × % น้ำหนัก × คะแนนสูงสุด (Group หรือ Individual) = คะแนนที่ได้

#### 4.6.2 Zero Score Rule

- **FR-SCORE-04:** นักศึกษาที่ไม่ Submit ได้คะแนนการมีส่วนร่วม 0; กลุ่มที่ยกเว้น Individual Evaluation ไม่ถูกหักคะแนนส่วนนั้น
- **FR-SCORE-05:** Draft ที่ยังไม่ Submit ไม่นำไปคำนวณคะแนนการประเมินหรือคะแนนการมีส่วนร่วม

#### 4.6.3 Instructor Evaluation Weight

- **FR-SCORE-06:** แต่ละ Assignment มี config `instructor_weight` (default = 1.0, ปรับได้ตอนสร้าง Assignment)
- **FR-SCORE-07:** เมื่อ Instructor ประเมิน 1 คู่ คะแนนของ Instructor นั้นถูกนับเทียบเท่า `instructor_weight` การประเมินของ student
  - ตัวอย่าง: `instructor_weight = 3` → การประเมิน 1 ครั้งของ Instructor นับเป็น 3 votes
- **FR-SCORE-08:** `instructor_weight` เป็น **ค่าเดียว** ใช้กับทั้ง Group และ Individual criteria ของ Assignment นั้น (ไม่แยกรายชนิด)
- **FR-SCORE-09:** ระบบแสดง effective vote count ใน Report เพื่อความโปร่งใส

#### 4.6.4 Individual Score Rolling Update

- **FR-SCORE-10:** คะแนน Individual ของนักศึกษาแต่ละคนคำนวณและแสดงผลทุกวัน (daily update) ตั้งแต่วันแรกที่มีการประเมินจนถึง deadline
- **FR-SCORE-11:** เพื่อนร่วมกลุ่มสามารถกรอกผล Individual Evaluation ได้ทุกวัน (re-open / update ได้จนถึง deadline)
- **FR-SCORE-12:** นักศึกษาเจ้าตัวเห็นเฉพาะคะแนนรวมของตัวเอง ไม่เห็นว่าใครให้คะแนนเท่าไร
- **FR-SCORE-13:** คะแนนที่แสดงระหว่าง deadline มี label "Interim — อาจเปลี่ยนแปลงได้" ชัดเจน
- **FR-SCORE-14:** คะแนน final คำนวณหลัง deadline จาก submission snapshot ล่าสุดของแต่ละหน้าที่ Submit แล้ว

#### 4.6.5 Participation Credit (Incomplete Submission)

- **FR-SCORE-15:** คะแนนการมีส่วนร่วมแยกจากคะแนน Group และ Individual; การ Submit บางคู่ก่อน deadline ได้ partial credit ตาม completion ratio

  ```
  completion_ratio = submitted_pairs / total_assigned_pairs
  participation_score = participation_max_score × completion_ratio
  ```

- **FR-SCORE-16:** คำนวณ completion ratio จาก assigned pairs ที่ต้องทำ โดยแยกส่วน Group และ Individual และยกเว้น Individual ของกลุ่มที่มีสมาชิกน้อยกว่า 3 คน
- **FR-SCORE-17:** หน้า Evaluation แสดง progress bar: `X / Y pairs submitted` แต่ละ criteria เพื่อให้นักศึกษาเห็น completion ของตัวเอง
- **FR-SCORE-18:** หากไม่มี submission เลย → participation score = 0 สำหรับส่วนที่ต้องประเมิน

#### 4.6.6 Peer Anonymity

- **FR-SCORE-19:** นักศึกษาเห็นเฉพาะคะแนนกลุ่มตนและคะแนน Individual ของตน ไม่เห็นผลราย evaluator
- **FR-SCORE-20:** Instructor เห็น evaluator ได้ใน Raw Pairs report แต่ไม่เปิดเผยต่อ student
- **FR-SCORE-21:** Instructor ตรวจตัวตน evaluator ได้ใน Raw Pairs report ที่ผ่าน authorization; ไฟล์ Export ใช้ชื่อแฝงและ Student ดาวน์โหลดไม่ได้

### 4.7 Report & Visibility

#### 4.7.1 Instructor Report

- **FR-REPORT-01:** ดูคะแนนรวมของทุกกลุ่มแยกตาม Assignment
- **FR-REPORT-02:** ดูคะแนนรวมรายบุคคลทุกคนใน Classroom
- **FR-REPORT-03:** ดู **Pair Coverage Report** แสดง:
  - ทุก pair ที่เป็นไปได้ (กลุ่ม + บุคคล)
  - ต่อคู่/criterion: `eligible_evaluators`, `target_evaluations = min(5, eligible_evaluators)`, `assigned_evaluators`, `votes` จาก Student ผู้ส่งคำตอบที่ไม่ซ้ำกัน, `missing_to_target = max(0, target_evaluations - votes)` และ `shortage_to_five = 5 - target_evaluations`
  - `instructor_votes` นับจำนวนคำตอบ Instructor ที่ส่งจริง; `effective_votes` รวม Student vote น้ำหนัก 1 และ Instructor vote ที่ถ่วง `instructor_weight`; `left_points`/`right_points` เป็นคะแนน pairwise สะสมของสองฝั่งหลังถ่วงน้ำหนัก โดยเรียงฝั่งตาม `left_id`/`right_id`; ทั้งสี่ค่าแสดงแยกจาก Student `votes` และ Instructor votes ไม่ลด `missing_to_target`
  - ผล Pairwise score สะสมของแต่ละ pair ต่อแต่ละ criteria
- **FR-REPORT-04:** ปุ่ม **"ส่งประเมินเพิ่ม"** สำหรับเลือก pair และส่งให้ Student ที่เข้าเกณฑ์ซึ่งยังไม่ได้รับคู่/criterion นั้น; ส่งเพิ่มเพื่อชดเชยผู้ที่ไม่ Submit ได้ แม้จำนวนที่มอบหมายเกินเป้าหมายเริ่มต้น
- **FR-REPORT-05:** ปุ่ม **"ประเมินเอง"** สำหรับ Instructor เปิดหน้า pairwise evaluation ของ pair นั้น

#### 4.7.2 Student Visibility

- **FR-REPORT-06:** นักศึกษาเห็นคะแนนรวมของกลุ่มตัวเอง (หลัง deadline หรือตามที่ Instructor กำหนด)
- **FR-REPORT-07:** นักศึกษาเห็นคะแนน Individual ของตัวเองแบบ rolling (daily update) พร้อม label "Interim" จนกว่าจะ final
- **FR-REPORT-08:** ไม่เปิดเผยคะแนนของกลุ่มอื่นหรือคนอื่นให้นักศึกษาดู

#### 4.7.3 Export

- **FR-EXPORT-01:** Instructor สามารถ Export ผลคะแนนได้ 2 รูปแบบ: **CSV** และ **Excel (.xlsx)**
- **FR-EXPORT-02:** Export รายงานได้ 3 ระดับ:
  - **Group Summary:** กลุ่ม × criteria × weighted score
  - **Individual Summary:** นักศึกษา × criteria × weighted score + total
  - **Raw Pairs:** ทุก pair, evaluator แบบชื่อแฝง, score ที่ให้, timestamp
- **FR-EXPORT-03:** Excel export มี 3 sheet แยกกัน (Group Summary, Individual Summary, Raw Pairs)
- **FR-EXPORT-04:** CSV export มีให้เลือกว่าจะ export sheet ไหน
- **FR-EXPORT-05:** ชื่อไฟล์ใช้ format `{classroom}_{assignment}_{type}_{YYYYMMDD}.{ext}`

---

## 5. Data Model (Conceptual)

### Core Entities

```
Classroom
├── id, name, created_by
├── Instructors (many-to-many: User)
└── Students (CSV import: email → User, groupname)

Group
├── id, classroom_id, name
└── Members (User[])

Assignment
├── id, classroom_id, name, total_score
├── group_max_score, individual_max_score, group_participation_max, individual_participation_max
├── group_deadline, individual_deadline
├── instructor_weight  ← configurable, default 1.0
├── GroupCriteria[]  (name, weight%)
└── IndividualCriteria[]  (name, weight%)

PairAssignment
├── id, assignment_id, criteria_id
├── type: GROUP | INDIVIDUAL
├── item_a_id, item_b_id  (group_id or user_id)
└── assigned_to_user_id

EvaluationResponse
├── id, pair_assignment_id, evaluator_id
├── score (1–5)
├── saved_at, submitted_at
└── status: DRAFT | SUBMITTED

ComputedScore
├── id, assignment_id, criteria_id
├── item_id (group_id or user_id)
├── raw_score, normalized_score, weighted_score
├── is_final  (bool — false until deadline passed)
└── computed_at
```

---

## 6. Pairing Algorithm — Detailed Specification

### 6.1 Goal

ทุก combination ที่ถูกต้องได้รับมอบหมายให้ Student ผู้ประเมินที่เข้าเกณฑ์ไม่ซ้ำกัน `min(5, จำนวนผู้ประเมินที่เข้าเกณฑ์)` คนต่อ criterion; ถ้ามีน้อยกว่า 5 คนยัง Publish ได้ และต้องแสดงจำนวนที่ขาดจาก 5 คน ไม่ใช้คำตอบซ้ำจากคนเดิมแทนเสียงอิสระ

### 6.2 Algorithm Steps

```
1. Generate all valid pairs:
   - GROUP: all (Gi, Gj) where i≠j; evaluator's own group excluded when assigning
   - INDIVIDUAL: all (Pi, Pj) within same group where i≠j

2. For each criterion and pair, find distinct eligible Student evaluators:
   target_evaluations = min(5, len(eligible_evaluators))
   shortage_to_five = 5 - target_evaluations

3. Build assignment list:
   - Assign each pair to target_evaluations different eligible students
   - Prefer eligible students with the lowest workload; use the seed for ties
   - Constraint: evaluator cannot be assigned their own group/self
   - Keep at most one active pair per student/criterion/subject pair;
     superseded history does not contribute another vote

4. Reject Publish if Classroom has fewer than 3 nonempty groups; skip Individual
   Evaluation for groups with fewer than 3 members. Do not reject solely
   because target_evaluations is below 5.

5. Generate assignments at Publish using a seed for reproducible tests
   Store as PairAssignment records
```

### 6.3 Constraints

| Constraint | Rule |
|---|---|
| No self-evaluation | evaluator's group ≠ any item in pair (Group eval) |
| No self-evaluation | evaluator ≠ any person in pair (Individual eval) |
| Initial coverage | Each valid pair/criterion gets `min(5, distinct eligible students)` assignments; Publish remains possible below five |
| No duplicate votes | At most one active Student assignment per criterion/subject pair; only the latest effective submitted answer counts, while superseded history remains for audit |
| Balanced load | Reach achievable coverage first, then keep evaluator workloads close |

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | หน้า Evaluation โหลดภายใน 2 วินาที |
| Availability | 99.5% uptime ช่วงก่อน Deadline |
| Security | Google OAuth, HTTPS, user data isolation |
| Scalability | รองรับ 1 Classroom = 200 นักศึกษา, 10 กลุ่ม |
| Mobile | Responsive design รองรับ mobile (เลือก radio button ง่าย) |
| Data Retention | เก็บ evaluation data ≥ 1 ปีการศึกษา |

---

## 8. Screen Flow

```
Login (Google)
    ↓
Dashboard (Classroom List)
    ↓
Classroom Detail
    ├── [Instructor] → Manage Students / Create Assignment / View Reports
    └── [Student]   → Assignment List
                            ↓
                    Assignment Detail
                    ├── Group Evaluation Page (1 page, all group criteria)
                    │       → Save / Submit
                    └── Individual Evaluation Page (1 page, all individual criteria)
                            → Save / Submit
```

---

## 9. Edge Cases & Rules Summary

| Case | Behavior |
|---|---|
| นักศึกษาไม่ Submit เลย | ได้คะแนนการมีส่วนร่วม 0 ยกเว้นส่วน Individual ที่ได้รับการยกเว้น |
| กลุ่มมีสมาชิกน้อยกว่า 3 คน | ไม่มี Individual Evaluation และไม่เสียคะแนนการมีส่วนร่วมส่วนนั้น |
| Classroom มีน้อยกว่า 3 กลุ่ม | Publish ไม่สำเร็จ |
| ผู้ประเมินที่เข้าเกณฑ์ไม่ถึง 5 คนต่อคู่/criterion | Publish ได้ถ้าเงื่อนไขอื่นผ่าน; แสดง `shortage_to_five` และไม่นับคนเดิมซ้ำเป็นหลายเสียง |
| Instructor ประเมินเอง | ใช้ pairwise และนับด้วย `instructor_weight` ของ Assignment |
| เพิ่ม evaluator เสริม | ส่งให้ Student ที่เข้าเกณฑ์และยังไม่ได้รับคู่/criterion นั้น; ถ้าไม่มีคนเหลือ ให้แสดงว่าเพิ่มไม่ได้ |
| ผลรวม Criteria weight ≠ 100% | Publish ไม่สำเร็จ |
| Email ใน CSV ไม่มีในระบบ | เพิ่ม record pending → activate เมื่อ user นั้น login ครั้งแรก |

---

## 10. Decisions Log

| # | เรื่อง | Decision | Version |
|---|---|---|---|
| 1 | **Instructor weight** | กำหนดได้ต่อ Assignment, default = 1.0, ค่าเดียวสำหรับ Group + Individual | v1.1 |
| 2 | **Individual visibility** | Rolling daily พร้อม label "Interim" จนกว่าจะ final หลัง deadline | v1.1 |
| 3 | **Export format** | รองรับทั้ง CSV และ Excel (.xlsx), 3 ระดับ report | v1.1 |
| 4 | **Peer anonymity** | ไม่เปิดเผย evaluator แก่นักศึกษา (anonymous ทุกกรณี) | v1.2 |
| 5 | **Partial submission** | คะแนนการมีส่วนร่วมแยกตาม completion_ratio ก่อน deadline | v1.3 |
| 6 | **Group re-assignment** | ย้ายก่อน deadline; คง pair ที่ถูกต้องและ supersede เฉพาะ pair ที่ใช้ไม่ได้ | v1.3 |
| 7 | **Re-submission** | Submit ใหม่ได้ทุกวันก่อน deadline — ใช้ submission ล่าสุดในการคำนวณ | v1.2 |
| 8 | **Instructor weight scope** | ใช้ค่าเดียวกันสำหรับทั้ง Group และ Individual | v1.2 |

## 11. PRD Status

✅ **Open Questions ทั้งหมดได้รับการตัดสินใจแล้ว** — PRD พร้อมส่ง Development Team

### Recommended Next Steps

1. **Technical Design Review** — ทีม dev review Data Model และ Pairing Algorithm
2. **UI/UX Wireframe** — ออกแบบหน้า Evaluation (Group/Individual) และ Report
3. **API Contract** — กำหนด endpoints และ request/response schema
4. **Security Review** — ทบทวน anonymity implementation และ data isolation
5. **Performance Testing Plan** — วาง load test scenario สำหรับช่วงก่อน deadline

---

*Document prepared for development team review.*
