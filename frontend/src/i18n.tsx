import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type Language = 'th' | 'en'

const th: Record<string, string> = {
  'Working...': 'กำลังดำเนินการ...', 'Loading...': 'กำลังโหลด...', 'Retry': 'ลองอีกครั้ง', 'Signing in...': 'กำลังเข้าสู่ระบบ...',
  'Administrator': 'ผู้ดูแลระบบ', 'Manage approved instructors': 'จัดการสิทธิ์อาจารย์',
  'Approved instructors can be invited into classrooms by a classroom instructor.': 'อาจารย์ที่อนุมัติแล้วสามารถถูกเชิญเข้าห้องเรียนโดยอาจารย์ประจำห้อง',
  'Instructor Google email': 'อีเมล Google ของอาจารย์', 'Approve instructor': 'อนุมัติอาจารย์',
  'Instructor approved.': 'อนุมัติอาจารย์แล้ว', 'Instructor access revoked.': 'ถอนสิทธิ์อาจารย์แล้ว',
  'Could not load instructors.': 'โหลดรายชื่ออาจารย์ไม่สำเร็จ', 'Could not approve instructor.': 'อนุมัติอาจารย์ไม่สำเร็จ',
  'Could not revoke instructor.': 'ถอนสิทธิ์อาจารย์ไม่สำเร็จ', 'Configured by administrator': 'กำหนดผ่าน environment',
  'Approved by': 'อนุมัติโดย', 'Revoke': 'ถอนสิทธิ์',
  'Ask an administrator to approve this instructor first': 'กรุณาให้ผู้ดูแลระบบอนุมัติอาจารย์รายนี้ก่อน',
  'Instructor is already approved': 'อาจารย์ได้รับอนุมัติแล้ว',
  'Classrooms': 'ห้องเรียน', 'Assignments': 'งานประเมิน', 'No assignments yet.': 'ยังไม่มีงานประเมิน',
  'Create assignment': 'สร้างงานประเมิน', 'Save assignment': 'บันทึกงานประเมิน', 'Cancel edit': 'ยกเลิกการแก้ไข',
  'Preview pairs': 'ดูตัวอย่างคู่', 'Edit': 'แก้ไข', 'Publish': 'เผยแพร่', 'Published': 'เผยแพร่แล้ว',
  'Title': 'ชื่องาน', 'Group evaluation': 'ประเมินกลุ่ม', 'Individual evaluation': 'ประเมินรายบุคคล',
  'Work score maximum': 'คะแนนผลงานเต็ม', 'Participation maximum': 'คะแนนการมีส่วนร่วมเต็ม',
  'Deadline': 'กำหนดส่ง', 'Criterion': 'เกณฑ์', 'Weight %': 'น้ำหนัก %', 'Remove': 'นำออก',
  'Add criterion': 'เพิ่มเกณฑ์', 'Instructor vote weight': 'น้ำหนักคะแนนอาจารย์',
  'Scores and coverage': 'คะแนนและความครอบคลุม', 'Refresh scores': 'อัปเดตคะแนน',
  'Student': 'นักศึกษา', 'Group work': 'ผลงานกลุ่ม', 'Individual work': 'ผลงานรายบุคคล',
  'Group participation': 'การมีส่วนร่วมกลุ่ม', 'Individual participation': 'การมีส่วนร่วมรายบุคคล',
  'No data': 'ยังไม่มีข้อมูล', 'Final': 'สรุปแล้ว', 'Interim — may change': 'ระหว่างดำเนินการ — อาจเปลี่ยนได้',
  'Criterion details and effective votes': 'รายละเอียดเกณฑ์และจำนวนคะแนนโหวต',
  'Section': 'ส่วน', 'Item ID': 'รหัสรายการ', 'Weighted score': 'คะแนนถ่วงน้ำหนัก',
  'Effective votes': 'จำนวนโหวตที่นับ', 'Pairs missing target coverage': 'คู่ที่ยังไม่ครบเป้าหมาย',
  'groups': 'กลุ่ม', 'students': 'นักศึกษา', 'pairs': 'คู่ประเมิน',
  'Strongly left': 'ซ้ายดีกว่ามาก', 'Slightly left': 'ซ้ายดีกว่าเล็กน้อย', 'Equal': 'เท่ากัน',
  'Slightly right': 'ขวาดีกว่าเล็กน้อย', 'Strongly right': 'ขวาดีกว่ามาก',
  'Progress': 'ความคืบหน้า', 'saved': 'บันทึกแล้ว', 'Last submitted': 'ส่งครั้งล่าสุด',
  'Not set': 'ยังไม่กำหนด', 'No pairs assigned for this section.': 'ยังไม่มีคู่ประเมินในส่วนนี้',
  'Submit saved answers': 'ส่งคำตอบที่บันทึก', 'Draft saved.': 'บันทึกร่างแล้ว',
  'Submit all currently saved answers for this section?': 'ส่งคำตอบที่บันทึกทั้งหมดในส่วนนี้หรือไม่?',
  'Instructor pairwise evaluation': 'อาจารย์ประเมินแบบเปรียบเทียบคู่',
  'Choose criterion': 'เลือกเกณฑ์', 'Group': 'กลุ่ม', 'Individual': 'รายบุคคล',
  'left item': 'รายการซ้าย', 'right item': 'รายการขวา', 'Assign to me': 'กำหนดให้ฉัน',
  'Vote saved.': 'บันทึกคะแนนแล้ว', 'Instructor pair assigned.': 'กำหนดคู่ให้อาจารย์แล้ว',
  'Move student between groups': 'ย้ายนักศึกษาระหว่างกลุ่ม', 'Refresh roster and history': 'อัปเดตรายชื่อและประวัติ',
  'Choose student': 'เลือกนักศึกษา', 'Target group': 'กลุ่มปลายทาง', 'Move': 'ย้าย',
  'Recent moves': 'การย้ายล่าสุด', 'Notifications': 'การแจ้งเตือน',
  'Move this student and update affected pair assignments?': 'ย้ายนักศึกษาและปรับคู่ประเมินที่เกี่ยวข้องหรือไม่?',
  'Could not load assignments.': 'โหลดงานประเมินไม่สำเร็จ', 'Assignment created.': 'สร้างงานประเมินแล้ว',
  'Assignment updated.': 'อัปเดตงานประเมินแล้ว', 'Could not create assignment.': 'สร้างงานประเมินไม่สำเร็จ',
  'Could not load assignment setup.': 'โหลดการตั้งค่างานไม่สำเร็จ', 'Pair operation failed.': 'ดำเนินการกับคู่ประเมินไม่สำเร็จ',
  'Could not load evaluation.': 'โหลดแบบประเมินไม่สำเร็จ', 'Draft could not be saved.': 'บันทึกร่างไม่สำเร็จ',
  'Submission failed.': 'ส่งคำตอบไม่สำเร็จ', 'Scores could not be loaded.': 'โหลดคะแนนไม่สำเร็จ',
  'Export failed.': 'ส่งออกรายงานไม่สำเร็จ', 'Could not load instructor evaluations.': 'โหลดคู่ประเมินของอาจารย์ไม่สำเร็จ',
  'Could not assign pair.': 'กำหนดคู่ไม่สำเร็จ', 'Could not save vote.': 'บันทึกคะแนนไม่สำเร็จ',
  'Could not load group updates.': 'โหลดข้อมูลกลุ่มไม่สำเร็จ', 'Could not move student.': 'ย้ายนักศึกษาไม่สำเร็จ',
  'Google sign-in is not configured.': 'ยังไม่ได้ตั้งค่าการเข้าสู่ระบบด้วย Google',
  'Google sign-in could not load.': 'โหลดการเข้าสู่ระบบด้วย Google ไม่สำเร็จ',
}

const Context = createContext<{ language: Language; setLanguage: (value: Language) => void }>({ language: 'th', setLanguage: () => {} })

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem('paireval-language') === 'en' ? 'en' : 'th')
  useEffect(() => { localStorage.setItem('paireval-language', language); document.documentElement.lang = language }, [language])
  return <Context.Provider value={{ language, setLanguage }}>{children}</Context.Provider>
}

export function useLanguage() {
  const { language, setLanguage } = useContext(Context)
  const t = (english: string) => language === 'th' ? (th[english] ?? english) : english
  const date = (value: string) => new Date(value).toLocaleString(language === 'th' ? 'th-TH' : 'en-US')
  return { language, setLanguage, t, date }
}
