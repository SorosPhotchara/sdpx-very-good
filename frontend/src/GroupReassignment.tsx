import { useState } from 'react'
import { getGroups, getNotifications, getReassignments, getStudents, reassignStudent } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { Button } from './components/ui/button'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from './components/ui/alert-dialog'

export function GroupReassignment({ classroomId, isInstructor }: { classroomId: number; isInstructor: boolean }) {
  const { t, language, date } = useLanguage()
  const [activated, setActivated] = useState(false)
  const resource = useResource(`${classroomId}:${isInstructor}`, async () => {
    if (isInstructor) {
      const [students, groups, history] = await Promise.all([getStudents(classroomId), getGroups(classroomId), getReassignments(classroomId)])
      return { students, groups, history, notifications: [] }
    }
    return { students: [], groups: [], history: [], notifications: await getNotifications(classroomId) }
  }, !isInstructor || activated)
  const { students = [], groups = [], history = [], notifications = [] } = resource.data ?? {}
  const [studentId, setStudentId] = useState(0)
  const [groupId, setGroupId] = useState(0)
  const [message, setMessage] = useState('')
  const [confirmMove, setConfirmMove] = useState(false)
  const action = useAsyncLock()
  const moving = action.busy

  async function move() {
    if (!action.begin()) return
    setConfirmMove(false)
    try {
      const result = await reassignStudent(classroomId, studentId, groupId)
      await resource.refresh()
      setMessage(language === 'th' ? 'ย้ายแล้ว ปรับคู่ ' + result.changed_pairs + ' รายการ และแจ้งนักศึกษา ' + result.notified_students + ' คน' : 'Moved student. ' + result.changed_pairs + ' pair records changed; ' + result.notified_students + ' students notified.')
    } catch (error) { setMessage(error instanceof Error ? error.message : t('Could not move student.')) }
    finally { action.finish() }
  }

  if (!isInstructor) return resource.error ? <p role="alert">{resource.error}</p> : notifications.length ? <div className="mt-3 text-sm"><h3 className="font-medium">{t('Notifications')}</h3>{notifications.map((item) => <p key={item.id}>{item.message} ({date(item.created_at)})</p>)}</div> : null
  return <details onToggle={(event) => { if (event.currentTarget.open) setActivated(true) }} className="group-reassignment mt-3 rounded-xl border p-3 text-sm">
    <summary className="cursor-pointer font-medium">{t('Move student between groups')}</summary>
    <Button type="button" variant="outline" disabled={moving || resource.loading} className="mt-2" onClick={() => void resource.refresh()}>{t('Refresh roster and history')}</Button>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดรายชื่อ...' : 'Loading roster...'}</p>}
    {resource.error && <p role="alert">{resource.error}</p>}
    <div className="group-reassignment-controls mt-2">
      <select disabled={moving} aria-label={t('Choose student')} value={studentId} onChange={(event) => setStudentId(Number(event.target.value))} className="rounded border p-2"><option value={0}>{t('Choose student')}</option>{students.map((item) => <option key={item.id} value={item.id}>{item.email} ({item.group_name})</option>)}</select>
      <select disabled={moving} aria-label={t('Target group')} value={groupId} onChange={(event) => setGroupId(Number(event.target.value))} className="rounded border p-2"><option value={0}>{t('Target group')}</option>{groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <AlertDialog open={confirmMove} onOpenChange={setConfirmMove}>
        <AlertDialogTrigger asChild><Button type="button" disabled={moving || !studentId || !groupId || students.find((item) => item.id === studentId)?.group_id === groupId} aria-busy={moving}>{moving ? (language === 'th' ? 'กำลังย้าย...' : 'Moving...') : t('Move')}</Button></AlertDialogTrigger>
        <AlertDialogContent data-testid="group-move-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>{t('Move student between groups')}</AlertDialogTitle>
            <AlertDialogDescription>{t('Move this student and update affected pair assignments?')}<br /><strong>{students.find((item) => item.id === studentId)?.email} → {groups.find((item) => item.id === groupId)?.name}</strong></AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{language === 'th' ? 'ยกเลิก' : 'Cancel'}</AlertDialogCancel>
            <AlertDialogAction disabled={moving} onClick={() => void move()}>{language === 'th' ? 'ยืนยันการย้าย' : 'Confirm move'}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    {history.length > 0 && <div className="mt-3"><h4 className="font-medium">{t('Recent moves')}</h4>{history.slice(0, 10).map((item) => <p key={item.id}>{t('Student')} #{item.student_id}: {t('Group')} #{item.old_group_id} → #{item.new_group_id} ({date(item.changed_at)})</p>)}</div>}
    {message && <p role="status" className="mt-2">{message}</p>}
  </details>
}
