import { useEffect, useRef, useState } from 'react'
import {
  addInstructorPair, addStudentPair, getAssignmentReport, getCriteria, getGroups, getRawPairResponses,
  getInstructorPairs, getStudents, saveInstructorVote,
} from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { ToastNotice, useNotice } from './components/ui/toast'

const choices = ['Strongly left', 'Slightly left', 'Equal', 'Slightly right', 'Strongly right']

export function InstructorEvaluation(props: { assignmentId: number; classroomId: number; email: string }) {
  const { t } = useLanguage()
  const [activated, setActivated] = useState(false)
  return <details onToggle={(event) => { if (event.currentTarget.open) setActivated(true) }} className="mt-3 rounded-xl border p-3 text-sm">
    <summary className="cursor-pointer font-medium">{t('Instructor pairwise evaluation')}</summary>
    {activated && <InstructorEvaluationContent key={`${props.assignmentId}:${props.classroomId}`} {...props} />}
  </details>
}

function InstructorEvaluationContent({ assignmentId, classroomId, email }: {
  assignmentId: number; classroomId: number; email: string
}) {
  const { t, language } = useLanguage()
  const resource = useResource(`${assignmentId}:${classroomId}`, async () => {
    const [criteria, groups, students, pairs, report, rawPairs] = await Promise.all([
      getCriteria(assignmentId), getGroups(classroomId), getStudents(classroomId),
      getInstructorPairs(assignmentId), getAssignmentReport(assignmentId), getRawPairResponses(assignmentId),
    ])
    return { criteria, groups, students, pairs, report, rawPairs }
  })
  const { criteria = [], groups = [], students = [], pairs = [], report, rawPairs = [] } = resource.data ?? {}
  const [criterionId, setCriterionId] = useState(0)
  const [leftId, setLeftId] = useState(0)
  const [rightId, setRightId] = useState(0)
  const [studentId, setStudentId] = useState(0)
  const [message, setMessage] = useNotice()
  const [savingPairIds, setSavingPairIds] = useState<Set<number>>(() => new Set())
  const pendingVotes = useRef(new Set<number>())
  const action = useAsyncLock()
  useEffect(() => { if (resource.data) setCriterionId((current) => current || resource.data?.criteria[0]?.id || 0) }, [resource.data])
  function updateChoice(pairId: number, choice: number | null) {
    resource.setData((current) => current ? { ...current, pairs: current.pairs.map((pair) => pair.pair_id === pairId ? { ...pair, choice } : pair) } : current)
  }

  const criterion = criteria.find((item) => item.id === criterionId)
  const candidates = criterion?.is_group ? groups : students
  const assignedStudentIds = new Set(rawPairs.filter((pair) =>
    pair.criterion_id === criterionId
    && ((pair.left_id === leftId && pair.right_id === rightId)
      || (pair.left_id === rightId && pair.right_id === leftId))
    && pair.evaluator_student_id !== null,
  ).map((pair) => pair.evaluator_student_id))
  const eligibleStudents = students.filter((student) => {
    if (student.group_id === null || !criterion || !leftId || !rightId || leftId === rightId) return false
    if (assignedStudentIds.has(student.id)) return false
    if (criterion.is_group) return student.group_id !== leftId && student.group_id !== rightId
    const left = students.find((item) => item.id === leftId)
    const right = students.find((item) => item.id === rightId)
    return left?.group_id !== null && left?.group_id === right?.group_id
      && student.group_id === left?.group_id && student.id !== leftId && student.id !== rightId
  })
  const coverageGaps = report?.coverage.filter((row) => row.missing_to_target > 0 || row.shortage_to_five > 0) ?? []
  const belowTarget = coverageGaps.filter((row) => row.missing_to_target > 0).length
  const eligibilityShortage = coverageGaps.filter((row) => row.shortage_to_five > 0).length

  async function assign(target: 'instructor' | 'student') {
    if (!action.begin()) return
    try {
      if (target === 'instructor') {
        await addInstructorPair(assignmentId, { criteria_id: criterionId, left_id: leftId, right_id: rightId, instructor_email: email })
        const assigned = await getInstructorPairs(assignmentId)
        resource.setData((current) => current ? { ...current, pairs: assigned } : current)
        setMessage(t('Instructor pair assigned.'))
      } else {
        await addStudentPair(assignmentId, { criteria_id: criterionId, left_id: leftId, right_id: rightId, student_id: studentId })
        setStudentId(0)
        await resource.refresh()
        setMessage(language === 'th' ? 'ส่งคู่ประเมินเพิ่มให้นักศึกษาแล้ว' : 'Extra pair assigned to student.')
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not assign pair.', 'error')
    } finally {
      action.finish()
    }
  }

  async function vote(pairId: number, choice: number) {
    if (pendingVotes.current.has(pairId)) return
    pendingVotes.current.add(pairId)
    const previousChoice = pairs.find((pair) => pair.pair_id === pairId)?.choice ?? null
    updateChoice(pairId, choice)
    setSavingPairIds((current) => new Set(current).add(pairId))
    try {
      await saveInstructorVote(assignmentId, pairId, choice)
      setMessage(t('Vote saved.'))
    } catch (error) {
      updateChoice(pairId, previousChoice)
      setMessage(error instanceof Error ? error.message : 'Could not save vote.', 'error')
    } finally {
      pendingVotes.current.delete(pairId)
      setSavingPairIds((current) => { const next = new Set(current); next.delete(pairId); return next })
    }
  }

  return <div>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดการประเมินของอาจารย์...' : 'Loading instructor evaluation...'}</p>}
    {resource.error && <div role="alert">{resource.error} <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button></div>}
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <select aria-label={t('Criterion')} value={criterionId} onChange={(event) => { setCriterionId(Number(event.target.value)); setLeftId(0); setRightId(0); setStudentId(0) }} className="rounded border p-2">
        <option value={0}>{t('Choose criterion')}</option>
        {criteria.map((item) => <option key={item.id} value={item.id}>{t(item.is_group ? 'Group' : 'Individual')}: {item.name}</option>)}
      </select>
      {(['left', 'right'] as const).map((side) => <select key={side} aria-label={t(side + ' item')} value={side === 'left' ? leftId : rightId}
        onChange={(event) => { if (side === 'left') setLeftId(Number(event.target.value)); else setRightId(Number(event.target.value)); setStudentId(0) }}
        className="rounded border p-2">
        <option value={0}>{t(side + ' item')}</option>
        {candidates.map((item) => <option key={item.id} value={item.id}>{'email' in item ? item.email : item.name}</option>)}
      </select>)}
      <button type="button" disabled={action.busy || resource.loading || !criterionId || !leftId || !rightId || leftId === rightId} aria-busy={action.busy} onClick={() => void assign('instructor')}
        className="rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50">{t(action.busy ? 'Working...' : 'Assign to me')}</button>
      <select aria-label={language === 'th' ? 'นักศึกษาผู้ประเมิน' : 'Student evaluator'} value={studentId}
        onChange={(event) => setStudentId(Number(event.target.value))} className="rounded border p-2">
        <option value={0}>{eligibleStudents.length === 0 && leftId && rightId && leftId !== rightId
          ? (language === 'th' ? 'ไม่มีนักศึกษาผู้ประเมินที่ยังไม่เคยได้คู่นี้' : 'No unused eligible student evaluators')
          : (language === 'th' ? 'เลือกนักศึกษาผู้ประเมิน' : 'Choose student evaluator')}</option>
        {eligibleStudents.map((student) => <option key={student.id} value={student.id}>{student.email}</option>)}
      </select>
      <button type="button" data-testid="assign-student-pair" disabled={action.busy || resource.loading || !studentId || !eligibleStudents.some((student) => student.id === studentId)}
        aria-busy={action.busy} onClick={() => void assign('student')}
        className="rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50">{language === 'th' ? 'ส่งคู่เพิ่มให้นักศึกษา' : 'Assign extra pair to student'}</button>
    </div>
    <p className="mt-2 text-slate-600">{language === 'th' ? 'นักศึกษาหนึ่งคนประเมินคู่เดียวกันได้หนึ่งครั้ง หากมอบหมายแล้วให้เลือกคนอื่น' : 'Each student counts once per pair. Choose another evaluator if this pair is already assigned to them.'}</p>
    {coverageGaps.length > 0 && <div className="mt-3 rounded border p-2 text-sm">
      <strong>{language === 'th' ? `คู่ที่ยังขาดคำตอบตามเป้าหมาย ${belowTarget} คู่ · คู่ที่ผู้มีสิทธิ์ไม่ครบ 5 คน ${eligibilityShortage} คู่` : `${belowTarget} pairs below feasible submitted target · ${eligibilityShortage} pairs have fewer than five eligible evaluators`}</strong>
      <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
        {coverageGaps.map((row) => {
          const left = row.section === 'group' ? groups.find((item) => item.id === row.left_id)?.name : students.find((item) => item.id === row.left_id)?.email
          const right = row.section === 'group' ? groups.find((item) => item.id === row.right_id)?.name : students.find((item) => item.id === row.right_id)?.email
          const unassigned = Math.max(0, row.target_evaluations - row.assigned_evaluators)
          const awaitingSubmission = Math.max(0, row.assigned_evaluators - row.votes)
          return <div key={`${row.criterion_id}:${row.left_id}:${row.right_id}`} className="flex flex-wrap items-center justify-between gap-2">
            <span>{row.criterion}: {left} / {right} · {language === 'th' ? `ส่งแล้ว ${row.votes}/${row.target_evaluations} · ยังไม่มอบหมาย ${unassigned} · มอบหมายแล้วแต่ยังไม่ส่ง ${awaitingSubmission} · ผู้มีสิทธิ์ขาดจาก 5 อีก ${row.shortage_to_five}` : `submitted ${row.votes}/${row.target_evaluations} · not assigned ${unassigned} · assigned but not submitted ${awaitingSubmission} · eligible shortage to five ${row.shortage_to_five}`}</span>
            <button type="button" className="rounded border px-2 py-1" onClick={() => {
              setCriterionId(row.criterion_id); setLeftId(row.left_id); setRightId(row.right_id); setStudentId(0)
            }}>{language === 'th' ? 'เลือกคู่นี้' : 'Select pair'}</button>
          </div>
        })}
      </div>
    </div>}
    <div className="mt-4 space-y-4">{pairs.map((pair) => <fieldset key={pair.pair_id} disabled={!pair.is_open || savingPairIds.has(pair.pair_id)} className="evaluation-pair">
      <legend>{pair.criterion}</legend>
      <div className="pair-candidates">
        <span>{pair.left}</span><span className="pair-versus" aria-hidden="true">VS</span><span>{pair.right}</span>
      </div>
      <div className="choice-scale">{choices.map((label, index) => <label key={label} className="choice-option">
        <input type="radio" name={`instructor-pair-${pair.pair_id}`} checked={pair.choice === index + 1}
          onChange={() => void vote(pair.pair_id, index + 1)} /><span>{t(label)}</span>
      </label>)}</div>
    </fieldset>)}</div>
    <ToastNotice notice={message} />
  </div>
}
