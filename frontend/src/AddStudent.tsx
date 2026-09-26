import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { useState, type FormEvent } from 'react'
import { addStudent } from './api'
import { useLanguage } from './i18n'
import { useAsyncLock } from './useAsyncLock'

export function AddStudent({ classroomId }: { classroomId: number }) {
  const { language } = useLanguage()
  const [email, setEmail] = useState('')
  const [groupName, setGroupName] = useState('')
  const [status, setStatus] = useState('')
  const action = useAsyncLock()
  const saving = action.busy

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!action.begin()) return
    setStatus('')
    try {
      const student = await addStudent(classroomId, email.trim(), groupName.trim())
      setEmail('')
      setStatus(language === 'th' ? `เพิ่ม ${student.email} ในกลุ่ม ${student.group_name} แล้ว` : `Added ${student.email} to ${student.group_name}.`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : language === 'th' ? 'เพิ่มนักศึกษาไม่สำเร็จ' : 'Could not add student.')
    } finally {
      action.finish()
    }
  }

  return <form className="add-student-form" onSubmit={(event) => void submit(event)}>
    <strong>{language === 'th' ? 'เพิ่มนักศึกษาทีละคน' : 'Add a student'}</strong>
    <label>{language === 'th' ? 'อีเมล Google ของนักศึกษา' : 'Student Google email'}
      <Input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
    </label>
    <label>{language === 'th' ? 'ชื่อกลุ่ม' : 'Group name'}
      <Input required value={groupName} onChange={(event) => setGroupName(event.target.value)} />
    </label>
    <Button type="submit" disabled={saving} aria-busy={saving}>{saving ? (language === 'th' ? 'กำลังเพิ่มนักศึกษา...' : 'Adding student...') : (language === 'th' ? 'เพิ่มนักศึกษา' : 'Add student')}</Button>
    {status && <p role="status">{status}</p>}
  </form>
}
