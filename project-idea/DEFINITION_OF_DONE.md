# Definition of Done — PairEval

เอกสารนี้ใช้ตรวจรับ PairEval รุ่นแรกตาม PRD และข้อตัดสินใจของโครงการ งานถือว่าเสร็จเมื่อ checklist ที่อยู่ในขอบเขตรุ่นแรกผ่านทั้งหมด พร้อมหลักฐานการทดสอบที่ทำซ้ำได้

## 1. ขอบเขตรุ่นแรก

- [ ] ผู้ใช้เข้าสู่ระบบด้วย Google Account และระบบแยกสิทธิ์ Instructor กับ Student จากอีเมลที่ยืนยันแล้ว
- [ ] Instructor สร้างและจัดการ Classroom, roster และ Assignment ได้
- [ ] Student ทำ Group และ Individual Evaluation แบบ pairwise ได้
- [ ] ระบบคำนวณคะแนนการประเมินและคะแนนการมีส่วนร่วมได้
- [ ] Instructor ดูรายงานพื้นฐานและส่งออก CSV/Excel ได้
- [ ] ระบบใช้ PostgreSQL เป็นฐานข้อมูลหลักและรันในเครื่องได้ตาม README
- [ ] การให้คะแนนของ Instructor ใช้ pairwise เท่านั้นในรุ่นแรก

## 2. Authentication และ Authorization

- [ ] ระบบใช้ Google OAuth 2.0 และ Backend ตรวจสอบ Google ID token ทุกครั้งที่เรียก protected API
- [ ] ไม่มีหน้า Register หรือระบบรหัสผ่านแยก
- [ ] อีเมล Instructor ต้องอยู่ใน `INSTRUCTOR_EMAILS`
- [ ] Student เข้าได้เฉพาะ Classroom ที่มีอีเมลตรงกับ roster CSV
- [ ] Student หนึ่งคนอยู่ได้หลาย Classroom ด้วย Google email เดียวกัน
- [ ] Instructor และ Student ไม่สามารถอ่านหรือแก้ข้อมูลของ Classroom ที่ไม่มีสิทธิ์
- [ ] Token ผิด, หมดอายุ หรือไม่มี token ต้องได้ HTTP 401
- [ ] การกระทำที่ role ไม่อนุญาตต้องได้ HTTP 403
- [ ] Logout ล้าง credential ใน Frontend และ protected API ใช้งานต่อไม่ได้

## 3. Classroom และ Roster

- [ ] Instructor ที่ได้รับอนุมัติสร้าง Classroom ได้และเป็นเจ้าของห้องนั้น
- [ ] Classroom รองรับ Instructor มากกว่าหนึ่งคน
- [ ] เพิ่ม Instructor ได้เฉพาะอีเมลที่อยู่ใน allowlist
- [ ] ระบบไม่อนุญาตให้ลบ Instructor คนสุดท้ายของ Classroom
- [ ] Import CSV รองรับ columns `email,groupname`
- [ ] ระบบตรวจ header, email, แถวซ้ำ และข้อมูลกลุ่ม พร้อมแจ้งข้อผิดพลาดที่แก้ไขได้
- [ ] Import ที่ไม่ผ่าน validation ไม่ทิ้งข้อมูลบางส่วนไว้ในฐานข้อมูล
- [ ] Pending Student membership เปิดใช้งานเมื่อ Google email เจ้าของบัญชีเข้าสู่ระบบครั้งแรก
- [ ] Instructor ดูรายชื่อนักศึกษาและกลุ่มใน Classroom ของตนเองได้

## 4. Assignment และ Criteria

- [ ] Instructor สร้าง Assignment พร้อมชื่อ คะแนนเต็ม และ Instructor weight ได้
- [ ] กำหนดคะแนนเต็ม Group, Individual และคะแนนการมีส่วนร่วมแยกกันได้
- [ ] Group และ Individual มี deadline แยกกัน
- [ ] Group criteria และ Individual criteria มีชื่อและน้ำหนักของตนเอง
- [ ] น้ำหนัก criteria ของแต่ละส่วนต้องรวมเป็น 100% ก่อน Publish
- [ ] Instructor แก้ setup ได้ก่อน Publish หรือก่อนเงื่อนไข deadline ที่ระบบกำหนด
- [ ] Student เห็นเฉพาะ Assignment ที่ Publish แล้ว
- [ ] Publish ไม่สำเร็จเมื่อ Classroom มีน้อยกว่า 3 กลุ่ม
- [ ] กลุ่มที่มีสมาชิกน้อยกว่า 3 คนไม่เปิด Individual Evaluation และสมาชิกไม่ถูกหักคะแนนจากการไม่ประเมินส่วนนั้น

## 5. Pairing Engine

- [ ] Group pairs ครอบคลุมทุก combination ที่ถูกต้องอย่างน้อย 5 evaluations ต่อ criterion
- [ ] ผู้ประเมินไม่ได้รับ pair ที่มีกลุ่มของตนเอง
- [ ] Individual pairs มีเฉพาะสมาชิกภายในกลุ่มเดียวกัน
- [ ] ผู้ประเมิน Individual ไม่พบตนเองอยู่ใน pair
- [ ] ระบบให้ความสำคัญกับ coverage ครบ 5 ครั้งก่อน แล้วจึงกระจายจำนวนงานให้ใกล้เคียงกัน
- [ ] Pairing ให้ผลที่ทำซ้ำได้เมื่อกำหนด seed เดียวกันสำหรับการทดสอบ
- [ ] รองรับ Classroom ขนาด 200 คน 10 กลุ่มโดยไม่สร้าง pair ที่ละเมิดข้อกำหนด
- [ ] Instructor ส่ง pair เพิ่มให้ evaluator เพิ่มเติมได้โดยไม่มอบ pair ที่ขัดกับข้อจำกัด

## 6. Evaluation และ Submission

- [ ] หน้า Group และ Individual Evaluation แยกจากกันและแสดงทุก criterion ที่เกี่ยวข้อง
- [ ] แต่ละ pair เลือกได้ 5 ระดับ: `1/0`, `.75/.25`, `.5/.5`, `.25/.75`, `0/1`
- [ ] Save Draft ไม่ถูกนำไปคำนวณจนกว่าจะ Submit
- [ ] Submit บางคู่ได้และระบบคำนวณ partial credit ตามสัดส่วนคู่ที่ส่ง
- [ ] Re-submit ได้ก่อน deadline โดย snapshot ล่าสุดทั้งหน้าแทน submission ก่อนหน้า
- [ ] การ Submit รวม draft ล่าสุดของทุกคู่ในหน้านั้น
- [ ] หน้า Evaluation แสดง progress, deadline และเวลาของ submission ล่าสุด
- [ ] หลัง deadline ไม่สามารถ Save หรือ Submit เพิ่มได้
- [ ] Group และ Individual บังคับ deadline และเก็บ submission แยกกัน
- [ ] Student ไม่เห็นตัวตนหรือคำตอบรายคนของ evaluator คนอื่น

## 7. Group Reassignment

- [ ] Instructor ย้าย Student ระหว่างกลุ่มได้เฉพาะก่อน deadline
- [ ] ระบบแสดงคำเตือนก่อนย้ายเมื่อ pair หรือ submission ได้รับผลกระทบ
- [ ] Pair เดิมที่ยังถูกต้องคงอยู่ และ pair ที่ใช้ไม่ได้ถูก supersede โดยไม่ลบประวัติ
- [ ] Submission ของ pair ที่ถูก supersede ไม่นำไปคำนวณ
- [ ] Student ที่ได้รับผลกระทบเห็น notification ให้ทำรายการใหม่
- [ ] ระบบเก็บประวัติผู้สั่งย้าย เวลา กลุ่มเดิม และกลุ่มใหม่สำหรับ audit

## 8. Scoring

- [ ] คะแนน pairwise ถูกคำนวณตามค่าของตัวเลือก 5 ระดับที่กำหนด
- [ ] คะแนนแต่ละ criterion normalize ให้ผลรวมของ item ที่มีข้อมูลเท่ากับ 1
- [ ] Weighted score ใช้น้ำหนัก criterion และคะแนนเต็มของส่วนนั้นอย่างถูกต้อง
- [ ] Instructor vote ใช้ `instructor_weight` เดียวกันกับ Group และ Individual
- [ ] รายการที่ยังไม่มีผลประเมินแสดงว่า “ยังไม่มีข้อมูล” ก่อนสรุป final
- [ ] เมื่อ final ระบบจัดการรายการที่ไม่มีผลตามกติกาคะแนนศูนย์อย่างสม่ำเสมอ
- [ ] คะแนนการมีส่วนร่วมเป็นคะแนนแยก และคิดตามจำนวน assigned pairs ที่ Student submit
- [ ] Student ที่ส่งบางส่วนได้ participation partial credit ตาม completion ratio
- [ ] Student ที่ไม่ Submit ได้ participation score เป็น 0 ยกเว้นส่วน Individual ที่ได้รับการยกเว้น
- [ ] คะแนนระหว่างช่วงประเมินมีสถานะ Interim และ final หลัง deadline
- [ ] Student เห็นเฉพาะคะแนนกลุ่มของตนและคะแนน Individual ของตน

## 9. Report และ Export

- [ ] Instructor ดู Group Summary และ Individual Summary ของ Assignment ได้
- [ ] Pair Coverage Report แสดงทุก pair, จำนวน evaluation และผลแยกตาม criterion
- [ ] Report แสดง effective vote count ที่รวม Instructor weight
- [ ] Instructor ตรวจ raw pair และ evaluator ได้ แต่นักศึกษาเข้าถึงข้อมูลนี้ไม่ได้
- [ ] Export CSV เลือกประเภท Group Summary, Individual Summary หรือ Raw Pairs ได้
- [ ] Export Excel มี sheet Group Summary, Individual Summary และ Raw Pairs
- [ ] ชื่อไฟล์เป็น `{classroom}_{assignment}_{type}_{YYYYMMDD}.{ext}`
- [ ] Export ป้องกัน spreadsheet formula injection ในข้อมูลที่ผู้ใช้อัปโหลด

## 10. UI และ Accessibility

- [ ] หน้าหลักและ flow สำคัญใช้งานได้ทั้งภาษาไทยและอังกฤษ
- [ ] UI ใช้งานได้ที่ความกว้าง mobile และ desktop โดยไม่มีข้อมูลสำคัญถูกตัด
- [ ] การทำงานสำคัญมี loading, success, empty และ error state
- [ ] ไม่มีการใช้ browser `alert`, `confirm` หรือ `prompt`
- [ ] Form มี label, keyboard navigation และ visible focus state
- [ ] Element ที่ automated test อ้างถึงมี `data-testid`

## 11. Security และ Data Integrity

- [ ] Secret และค่าเฉพาะเครื่องอยู่ใน `.env` และไม่ถูก commit
- [ ] CORS อนุญาตเฉพาะ Frontend origins ที่กำหนด
- [ ] Backend ตรวจ ownership ทุก endpoint ที่อ่านหรือแก้ Classroom data
- [ ] Database constraints ป้องกันข้อมูลซ้ำและ foreign key ที่ไม่ถูกต้อง
- [ ] การแก้ข้อมูลหลายตารางที่เกี่ยวข้องกันทำใน transaction เดียว
- [ ] ดาวน์โหลดรายงานต้องผ่าน authorization เช่นเดียวกับหน้า Report
- [ ] ข้อมูล evaluation และ audit เก็บได้อย่างน้อย 1 ปีการศึกษา

## 12. Performance และ Reliability

- [ ] หน้า Evaluation โหลดภายใน 2 วินาทีภายใต้ชุดข้อมูล 200 คน 10 กลุ่มในสภาพแวดล้อมทดสอบที่ระบุ
- [ ] Publish และสร้าง pair สำหรับชุดข้อมูลเป้าหมายเสร็จโดยไม่ timeout
- [ ] มีผล load test สำหรับ traffic ก่อน deadline และบันทึกจำนวนผู้ใช้พร้อมกันกับข้อจำกัดของเครื่องทดสอบ
- [ ] API validation failure ไม่ทำให้เกิด partial write หรือข้อมูลคะแนนเสียหาย
- [ ] Migration ใช้กับ PostgreSQL ฐานใหม่ได้ตั้งแต่ต้นจนถึง revision ล่าสุด

## 13. Verification และการส่งมอบ

- [ ] Backend automated tests ผ่านทั้งหมด
- [ ] Frontend tests, type check, lint และ production build ผ่านทั้งหมด
- [ ] มี automated tests สำหรับ authorization, pairing, submission snapshot, partial credit, scoring และ export
- [ ] Critical user flow ผ่านการทดสอบด้วย Google Login จริงทั้ง Instructor และ Student
- [ ] README อธิบาย clone, `.env`, database, migration และคำสั่งรัน FE/BE ได้ครบ
- [ ] `.env.example` มีทุกตัวแปรที่จำเป็นโดยไม่มี secret จริง
- [ ] API และ domain documentation ตรงกับ behavior รุ่นที่ส่งมอบ
- [ ] ไม่มี Critical หรือ High severity defect ที่ยังเปิดอยู่
- [ ] Product owner ตรวจหลักฐานและยอมรับทุกข้อในขอบเขตรุ่นแรก

## หลักฐานที่แนบตอนตรวจรับ

- Commit หรือ release revision ที่ตรวจรับ
- ผล automated tests พร้อมวันและ environment
- ผล performance/load test พร้อมขนาดข้อมูล
- Test account matrix สำหรับ Instructor และ Student
- ตัวอย่าง CSV/Excel export
- รายการข้อจำกัดที่ทราบและงานที่เลื่อนไปรุ่นถัดไป
