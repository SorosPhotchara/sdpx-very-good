import { useEffect, useState } from 'react'
import { getGroups, getNotifications, getReassignments, getStudents, reassignStudent, type Group, type Student } from './api'
import { useLanguage } from './i18n'

export function GroupReassignment({ classroomId, isInstructor }: { classroomId: number; isInstructor: boolean }) {
  const { t, language, date } = useLanguage()
  const [students, setStudents] = useState<Student[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [history, setHistory] = useState<{ id: number; student_id: number; old_group_id: number; new_group_id: number; changed_at: string }[]>([])
  const [notifications, setNotifications] = useState<{ id: number; message: string; created_at: string }[]>([])
  const [studentId, setStudentId] = useState(0)
  const [groupId, setGroupId] = useState(0)
  const [message, setMessage] = useState('')
  const [confirmMove, setConfirmMove] = useState(false)

  async function refresh() {
    try {
      if (isInstructor) {
        const [roster, availableGroups, changes] = await Promise.all([getStudents(classroomId), getGroups(classroomId), getReassignments(classroomId)])
        setStudents(roster); setGroups(availableGroups); setHistory(changes)
      } else setNotifications(await getNotifications(classroomId))
    } catch (error) { setMessage(error instanceof Error ? error.message : t('Could not load group updates.')) }
  }
  useEffect(() => { void refresh() }, [classroomId, isInstructor])

  async function move() {
    setConfirmMove(false)
    try {
      const result = await reassignStudent(classroomId, studentId, groupId)
      await refresh()
      setMessage(language === 'th' ? 'ย้ายแล้ว ปรับคู่ ' + result.changed_pairs + ' รายการ และแจ้งนักศึกษา ' + result.notified_students + ' คน' : 'Moved student. ' + result.changed_pairs + ' pair records changed; ' + result.notified_students + ' students notified.')
    } catch (error) { setMessage(error instanceof Error ? error.message : t('Could not move student.')) }
  }

  if (!isInstructor) return notifications.length ? <div className="mt-3 text-sm"><h3 className="font-medium">{t('Notifications')}</h3>{notifications.map((item) => <p key={item.id}>{item.message} ({date(item.created_at)})</p>)}</div> : null
  return <details className="group-reassignment mt-3 rounded-xl border p-3 text-sm">
    <summary className="cursor-pointer font-medium">{t('Move student between groups')}</summary>
    <button type="button" className="mt-2 text-blue-700" onClick={() => void refresh()}>{t('Refresh roster and history')}</button>
    <div className="group-reassignment-controls mt-2">
      <select aria-label={t('Choose student')} value={studentId} onChange={(event) => setStudentId(Number(event.target.value))} className="rounded border p-2"><option value={0}>{t('Choose student')}</option>{students.map((item) => <option key={item.id} value={item.id}>{item.email} ({item.group_name})</option>)}</select>
      <select aria-label={t('Target group')} value={groupId} onChange={(event) => setGroupId(Number(event.target.value))} className="rounded border p-2"><option value={0}>{t('Target group')}</option>{groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <button type="button" disabled={!studentId || !groupId || students.find((item) => item.id === studentId)?.group_id === groupId} onClick={() => setConfirmMove(true)} className="rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50">{t('Move')}</button>
    </div>
    {confirmMove && <div className="confirm-panel" role="group" aria-label={t('Move student between groups')}>
      <p>{t('Move this student and update affected pair assignments?')}<br /><strong>{students.find((item) => item.id === studentId)?.email} → {groups.find((item) => item.id === groupId)?.name}</strong></p>
      <div><button type="button" onClick={() => void move()}>{language === 'th' ? 'ยืนยันการย้าย' : 'Confirm move'}</button><button type="button" onClick={() => setConfirmMove(false)}>{language === 'th' ? 'ยกเลิก' : 'Cancel'}</button></div>
    </div>}
    {history.length > 0 && <div className="mt-3"><h4 className="font-medium">{t('Recent moves')}</h4>{history.slice(0, 10).map((item) => <p key={item.id}>{t('Student')} #{item.student_id}: {t('Group')} #{item.old_group_id} → #{item.new_group_id} ({date(item.changed_at)})</p>)}</div>}
    {message && <p role="status" className="mt-2">{message}</p>}
  </details>
}
