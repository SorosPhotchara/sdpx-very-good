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
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog'

export function ClassroomRoster({ classroomId }: { classroomId: number }) {
  const { language, date } = useLanguage()
  const text = (th: string, en: string) => language === 'th' ? th : en
  const resource = useResource(`roster:${classroomId}`, async () => {
    const [students, groups] = await Promise.all([getStudents(classroomId), getGroups(classroomId)])
    return { students, groups }
  })
  const { students = [], groups = [] } = resource.data ?? {}
  const [search, setSearch] = useState('')
  const [target, setTarget] = useState<Student | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [status, setStatus] = useNotice()
  const [removeError, setRemoveError] = useNotice()
  const action = useAsyncLock()

  // group_name is denormalised on the student row and goes stale after a move, so
  // prefer the group the id still points at.
  const groupLabel = (student: Student) =>
    groups.find(group => group.id === student.group_id)?.name ?? student.group_name ?? '—'
  const filteredStudents = students.filter(student =>
    `${student.email} ${student.display_name ?? ''}`.toLowerCase().includes(search.trim().toLowerCase()),
  )

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

  return <section className="classroom-roster mt-3 min-w-0 rounded-xl border p-3 text-sm" aria-label={text('รายชื่อนักศึกษา', 'Classroom roster')}>
    <div className="flex min-w-0 items-center justify-between gap-2">
      <div className="min-w-0">
        <h3 className="font-medium">{text('รายชื่อนักศึกษา', 'Classroom roster')}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{text(`มีนักศึกษา ${students.length} คน`, `${students.length} students`)}</p>
      </div>
      <Dialog onOpenChange={open => { if (open) setSearch('') }}>
        <DialogTrigger asChild>
          <Button type="button" variant="outline" className="shrink-0" data-testid="open-roster-dialog">{text('จัดการรายชื่อ', 'Manage roster')}</Button>
        </DialogTrigger>
        <DialogContent data-testid="roster-dialog" className="flex max-h-[min(88dvh,48rem)] flex-col gap-0 p-0">
          <DialogHeader className="relative border-b px-4 py-4 pr-14 sm:px-6">
            <DialogTitle>{text('รายชื่อนักศึกษา', 'Student roster')}</DialogTitle>
            <DialogDescription>{text(`ค้นหาและจัดการนักศึกษา ${students.length} คนในห้องนี้`, `Search and manage ${students.length} students in this classroom`)}</DialogDescription>
            <DialogClose asChild><Button type="button" variant="ghost" size="icon" className="absolute right-3 top-3" aria-label={text('ปิดหน้าต่าง', 'Close dialog')}>×</Button></DialogClose>
          </DialogHeader>
          <div className="flex gap-2 border-b p-4 sm:px-6">
            <Input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder={text('ค้นหาจากอีเมลหรือชื่อ', 'Search email or name')} aria-label={text('ค้นหานักศึกษา', 'Search students')} data-testid="search-roster" />
            <Button type="button" variant="outline" className="shrink-0" data-testid="refresh-roster" disabled={action.busy || resource.loading} onClick={() => void resource.refresh()}>{text('โหลดใหม่', 'Refresh')}</Button>
          </div>
          {resource.error && <p className="px-4 pt-3 text-sm text-destructive sm:px-6" role="alert">{resource.error}</p>}
          <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6" data-testid="roster-list-scroll">
            {resource.loading && <p role="status">{text('กำลังโหลดรายชื่อ...', 'Loading roster...')}</p>}
            {!resource.loading && students.length === 0 && <p data-testid="roster-empty" className="py-8 text-center text-muted-foreground">{text('ยังไม่มีนักศึกษาในห้องนี้', 'No students in this classroom yet.')}</p>}
            {!resource.loading && students.length > 0 && filteredStudents.length === 0 && <p className="py-8 text-center text-muted-foreground">{text('ไม่พบนักศึกษาที่ตรงกับคำค้น', 'No students match your search.')}</p>}
            <ul data-testid="roster-list" className="grid min-w-0 gap-2" aria-label={text('นักศึกษาในห้องนี้', 'Students in this classroom')}>
              {filteredStudents.map(student => <li key={student.id} data-testid={`roster-row-${student.id}`} className="flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1">
                  <p className="break-all font-medium leading-5" title={student.email}>{student.email}</p>
                  <p className="mt-1 break-words text-sm text-muted-foreground">{student.display_name || text('ยังไม่ระบุชื่อ', 'Name not provided')}</p>
                  <div className="mt-2 flex min-w-0 flex-wrap items-center gap-1.5 text-xs">
                    <span className="max-w-full break-words rounded-full bg-muted px-2 py-1">{groupLabel(student)}</span>
                    <span className={student.activated_at ? 'rounded-full bg-primary/10 px-2 py-1 text-primary' : 'rounded-full bg-amber-50 px-2 py-1 text-amber-900'}>
                      {student.activated_at ? text(`เข้าใช้แล้ว ${date(student.activated_at)}`, `Active ${date(student.activated_at)}`) : text('ยังไม่เคยเข้าใช้งาน', 'Not activated')}
                    </span>
                  </div>
                </div>
                <Button type="button" variant="outline" className="min-h-11 shrink-0 border-destructive/40 text-destructive hover:bg-destructive hover:text-destructive-foreground sm:min-h-9" data-testid={`remove-student-${student.id}`} aria-label={text(`ลบนักศึกษา ${student.email}`, `Remove student ${student.email}`)} disabled={action.busy} onClick={() => { setTarget(student); setConfirmation(''); setRemoveError('') }}>{text('ลบออกจากห้อง', 'Remove')}</Button>
              </li>)}
            </ul>
          </div>
          <div className="border-t px-4 py-3 text-xs text-muted-foreground sm:px-6">{text('การลบจะนำอีเมลนี้ออกจากห้องเรียน', 'Removing a student removes this email from the classroom.')}</div>
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
        </DialogContent>
      </Dialog>
    </div>
    <ToastNotice notice={status} />
  </section>
}
