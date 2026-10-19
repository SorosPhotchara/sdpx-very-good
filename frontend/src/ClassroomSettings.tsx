import { useState, type FormEvent } from 'react'
import { type Classroom } from './api'
import { useLanguage } from './i18n'
import { useAsyncLock } from './useAsyncLock'
import { ToastNotice, useNotice } from './components/ui/toast'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Label } from './components/ui/label'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from './components/ui/alert-dialog'

export function ClassroomSettings({ classroom, onRename, onDelete }: {
  classroom: Classroom
  onRename: (name: string) => Promise<void>
  onDelete: () => Promise<void>
}) {
  const { language } = useLanguage()
  const text = (th: string, en: string) => language === 'th' ? th : en
  const [name, setName] = useState(classroom.name)
  const [confirmation, setConfirmation] = useState('')
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useNotice()
  const [deleteError, setDeleteError] = useNotice()
  const action = useAsyncLock()

  async function rename(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || !action.begin()) return
    setStatus('')
    try { await onRename(name.trim()); setStatus(text('เปลี่ยนชื่อห้องแล้ว', 'Classroom renamed.')) }
    catch (error) { setStatus(error instanceof Error ? error.message : text('เปลี่ยนชื่อไม่สำเร็จ', 'Rename failed.'), 'error') }
    finally { action.finish() }
  }

  async function remove() {
    if (confirmation.trim() !== classroom.name || !action.begin()) return
    setDeleteError('')
    try { await onDelete(); setOpen(false) }
    catch (error) { setDeleteError(error instanceof Error ? error.message : text('ลบห้องไม่สำเร็จ', 'Deletion failed.'), 'error') }
    finally { action.finish() }
  }

  return <section className="classroom-settings" aria-label={text('ชื่อห้องและการลบ', 'Classroom name and deletion')}>
    <form onSubmit={event => void rename(event)}>
      <Label htmlFor="classroom-name">{text('ชื่อห้องเรียน', 'Classroom name')}</Label>
      <Input id="classroom-name" data-testid="classroom-name" required value={name} disabled={action.busy} onChange={event => setName(event.target.value)} />
      <Button type="submit" variant="outline" data-testid="rename-classroom" disabled={action.busy || !name.trim() || name.trim() === classroom.name} aria-busy={action.busy}>{text('บันทึกชื่อห้อง', 'Save classroom name')}</Button>
    </form>
    <ToastNotice notice={status} />
    <AlertDialog open={open} onOpenChange={value => { if (!action.busy) { setOpen(value); setConfirmation(''); setDeleteError('') } }}>
      <AlertDialogTrigger asChild><Button type="button" variant="outline" className="text-destructive" data-testid="delete-classroom" disabled={action.busy}>{text('ลบห้องเรียน', 'Delete classroom')}</Button></AlertDialogTrigger>
      <AlertDialogContent data-testid="delete-classroom-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>{text('ลบห้องเรียน', 'Delete classroom')}: {classroom.name}</AlertDialogTitle>
          <AlertDialogDescription>{text('ห้องนี้จะถูกนำออกและกู้คืนไม่ได้ ข้อมูลการประเมินและประวัติจะเก็บไว้เพื่อตรวจสอบอย่างน้อยหนึ่งปีการศึกษา ห้องอื่นไม่ได้รับผลกระทบ', 'This classroom is removed and cannot be restored. Evaluation and audit records are retained for at least one academic year. Other classrooms are unaffected.')}</AlertDialogDescription>
        </AlertDialogHeader>
        <Label htmlFor="confirm-classroom-name">{text('พิมพ์ชื่อห้องเพื่อยืนยัน', 'Type classroom name to confirm')}</Label>
        <Input id="confirm-classroom-name" data-testid="confirm-classroom-name" value={confirmation} disabled={action.busy} onChange={event => setConfirmation(event.target.value)} autoComplete="off" />
        <ToastNotice notice={deleteError} assertive />
        <AlertDialogFooter>
          <AlertDialogCancel disabled={action.busy}>{text('ยกเลิก', 'Cancel')}</AlertDialogCancel>
          <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" data-testid="confirm-delete-classroom" disabled={action.busy || confirmation.trim() !== classroom.name} aria-busy={action.busy} onClick={event => { event.preventDefault(); void remove() }}>{text(action.busy ? 'กำลังดำเนินการ...' : 'ลบห้องเรียน', action.busy ? 'Working...' : 'Delete classroom')}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </section>
}
