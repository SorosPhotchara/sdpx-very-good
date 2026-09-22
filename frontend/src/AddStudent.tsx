import { useState, type FormEvent } from 'react'
import { addStudent } from './api'
import { useLanguage } from './i18n'

export function AddStudent({ classroomId }: { classroomId: number }) {
  const { language } = useLanguage()
  const [email, setEmail] = useState('')
  const [groupName, setGroupName] = useState('')
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    setStatus('')
    try {
      const student = await addStudent(classroomId, email.trim(), groupName.trim())
      setEmail('')
      setStatus(language === 'th' ? `เพิ่ม ${student.email} ในกลุ่ม ${student.group_name} แล้ว` : `Added ${student.email} to ${student.group_name}.`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : language === 'th' ? 'เพิ่มนักศึกษาไม่สำเร็จ' : 'Could not add student.')
    } finally {
      setSaving(false)
    }
  }

  return <form className="add-student-form" onSubmit={(event) => void submit(event)}>
    <strong>{language === 'th' ? 'เพิ่มนักศึกษาทีละคน' : 'Add a student'}</strong>
    <label>{language === 'th' ? 'อีเมล Google ของนักศึกษา' : 'Student Google email'}
      <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
    </label>
    <label>{language === 'th' ? 'ชื่อกลุ่ม' : 'Group name'}
      <input required value={groupName} onChange={(event) => setGroupName(event.target.value)} />
    </label>
    <button type="submit" disabled={saving}>{language === 'th' ? 'เพิ่มนักศึกษา' : 'Add student'}</button>
    {status && <p role="status">{status}</p>}
  </form>
}
