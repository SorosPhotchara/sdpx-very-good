import { useState } from 'react'
import { getGroups, getStudents, removeStudent, type Student } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { ToastNotice, useNotice } from './components/ui/toast'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Label } from './components/ui/label'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './components/ui/alert-dialog'

export function ClassroomRoster({ classroomId }: { classroomId: number }) {
  const { language, date } = useLanguage()
  const text = (th: string, en: string) => language === 'th' ? th : en
  const resource = useResource(`roster:${classroomId}`, async () => {
    const [students, groups] = await Promise.all([getStudents(classroomId), getGroups(classroomId)])
    return { students, groups }
  })
  const { students = [], groups = [] } = resource.data ?? {}
  const [target, setTarget] = useState<Student | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [status, setStatus] = useNotice()
  const [removeError, setRemoveError] = useNotice()
  const action = useAsyncLock()

  // group_name is denormalised on the student row and goes stale after a move, so
  // prefer the group the id still points at.
  const groupLabel = (student: Student) =>
    groups.find(group => group.id === student.group_id)?.name ?? student.group_name ?? '—'

  async function remove() {
    if (!target || confirmation.trim().toLowerCase() !== target.email || !action.begin()) return
    setRemoveError('')
    try {
      await removeStudent(classroomId, target.id, target.email)
      setTarget(null)
      setConfirmation('')
      await resource.refresh()
      setStatus(text('นำนักศึกษาออกจากห้องแล้ว', 'Student removed from the classroom.'))
    } catch (error) {
      setRemoveError(error instanceof Error ? error.message : text('นำนักศึกษาออกไม่สำเร็จ', 'Could not remove student.'), 'error')
    } finally { action.finish() }
  }

  return <section className="classroom-roster mt-3 rounded-xl border p-3 text-sm" aria-label={text('รายชื่อนักศึกษา', 'Classroom roster')}>
    <h3 className="font-medium">{text('รายชื่อนักศึกษา', 'Classroom roster')}</h3>
    <Button type="button" variant="outline" className="mt-2" data-testid="refresh-roster" disabled={action.busy || resource.loading} onClick={() => void resource.refresh()}>{text('โหลดรายชื่อใหม่', 'Refresh roster')}</Button>
    {resource.loading && <p role="status">{text('กำลังโหลดรายชื่อ...', 'Loading roster...')}</p>}
    {resource.error && <p role="alert">{resource.error}</p>}
    {!resource.loading && students.length === 0
      ? <p data-testid="roster-empty" className="mt-2">{text('ยังไม่มีนักศึกษาในห้องนี้', 'No students in this classroom yet.')}</p>
      : <table data-testid="roster-table" className="mt-2 w-full border-collapse text-left">
        <thead>
          <tr>
            <th scope="col" className="border-b p-2">{text('อีเมล', 'Email')}</th>
            <th scope="col" className="border-b p-2">{text('ชื่อ', 'Name')}</th>
            <th scope="col" className="border-b p-2">{text('กลุ่ม', 'Group')}</th>
            <th scope="col" className="border-b p-2">{text('สถานะ', 'Status')}</th>
            <th scope="col" className="border-b p-2">{text('จัดการ', 'Actions')}</th>
          </tr>
        </thead>
        <tbody>
          {students.map(student => <tr key={student.id} data-testid={`roster-row-${student.id}`}>
            <td className="border-b p-2">{student.email}</td>
            <td className="border-b p-2">{student.display_name || '—'}</td>
            <td className="border-b p-2">{groupLabel(student)}</td>
            <td className="border-b p-2">{student.activated_at ? date(student.activated_at) : text('ยังไม่เข้าใช้งาน', 'Pending activation')}</td>
            <td className="border-b p-2"><Button type="button" variant="outline" className="text-destructive" data-testid={`remove-student-${student.id}`} disabled={action.busy} onClick={() => { setTarget(student); setConfirmation(''); setRemoveError('') }}>{text('นำออก', 'Remove')}</Button></td>
          </tr>)}
        </tbody>
      </table>}
    <ToastNotice notice={status} />
    <AlertDialog open={target !== null} onOpenChange={value => { if (!action.busy && !value) { setTarget(null); setConfirmation(''); setRemoveError('') } }}>
      <AlertDialogContent data-testid="remove-student-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>{text('นำนักศึกษาออกจากห้อง', 'Remove student from classroom')}</AlertDialogTitle>
          <AlertDialogDescription>{text('นักศึกษาคนนี้จะถูกนำออกจากห้องอย่างถาวร พร้อมกับการแจ้งเตือนและประวัติการย้ายกลุ่มของเขา ทำได้เฉพาะก่อนที่จะมีการสร้างการประเมิน', 'This student is permanently removed from the classroom, along with their notifications and group-move history. Only possible before any evaluation exists.')}<br /><strong>{target?.email}</strong></AlertDialogDescription>
        </AlertDialogHeader>
        <Label htmlFor="confirm-student-email">{text('พิมพ์อีเมลของนักศึกษาเพื่อยืนยัน', 'Type the student email to confirm')}</Label>
        <Input id="confirm-student-email" data-testid="confirm-student-email" value={confirmation} disabled={action.busy} onChange={event => setConfirmation(event.target.value)} autoComplete="off" />
        <ToastNotice notice={removeError} assertive />
        <AlertDialogFooter>
          <AlertDialogCancel disabled={action.busy}>{text('ยกเลิก', 'Cancel')}</AlertDialogCancel>
          <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" data-testid="confirm-remove-student" disabled={action.busy || !target || confirmation.trim().toLowerCase() !== target.email} aria-busy={action.busy} onClick={event => { event.preventDefault(); void remove() }}>{text(action.busy ? 'กำลังดำเนินการ...' : 'นำออกจากห้อง', action.busy ? 'Working...' : 'Remove student')}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </section>
}
