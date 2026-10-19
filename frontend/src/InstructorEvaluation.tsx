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
  return <details onToggle={(event) => { if (event.currentTarget.open) setActivated(true) }} className="mt-4 border-t border-slate-200 pt-4 text-sm">
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
  const selectedLeft = candidates.find((item) => item.id === leftId)
  const selectedRight = candidates.find((item) => item.id === rightId)
  const itemLabel = (item: typeof selectedLeft) => item ? ('email' in item ? item.display_name || item.email : item.name) : ''
  const selectedLeftLabel = itemLabel(selectedLeft)
  const selectedRightLabel = itemLabel(selectedRight)
  const currentInstructorPair = pairs.find((pair) =>
    pair.section === (criterion?.is_group ? 'group' : 'individual')
    && pair.criterion === criterion?.name
    && ((pair.left === selectedLeftLabel && pair.right === selectedRightLabel)
      || (pair.left === selectedRightLabel && pair.right === selectedLeftLabel)),
  )
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
  const groupedPairs = Object.values(pairs.reduce<Record<string, { section: string; criterion: string; pairs: typeof pairs }>>((groups, pair) => {
    const key = `${pair.section}:${pair.criterion}`
    groups[key] ??= { section: pair.section, criterion: pair.criterion, pairs: [] }
    groups[key].pairs.push(pair)
    return groups
  }, {}))

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
    <div className="instructor-pair-controls mt-2 flex flex-wrap items-center gap-2">
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
      <button type="button" data-testid="assign-instructor-pair" disabled={action.busy || resource.loading || !criterionId || !leftId || !rightId || leftId === rightId || Boolean(currentInstructorPair)} aria-busy={action.busy} onClick={() => void assign('instructor')}
        className={currentInstructorPair ? 'min-h-11 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 font-semibold text-primary disabled:opacity-100' : 'min-h-11 rounded-md bg-primary px-3 py-2 font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50'}>
        {action.busy ? t('Working...') : currentInstructorPair ? (language === 'th' ? 'มอบหมายให้ฉันแล้ว' : 'Already assigned to me') : t('Assign to me')}
      </button>
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
    {criterion && leftId && rightId && leftId !== rightId && <div className={currentInstructorPair ? 'mt-3 rounded-lg border border-primary/25 bg-primary/10 p-3 text-sm text-foreground' : 'mt-3 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-foreground'} role="status" aria-live="polite" data-testid="instructor-pair-selection-status">
      <strong>{currentInstructorPair ? (language === 'th' ? 'คู่นี้มอบหมายให้คุณแล้ว' : 'This pair is assigned to you') : (language === 'th' ? 'คู่ที่เลือก' : 'Selected pair')}</strong>
      <span className="ml-2">{criterion.name}: {selectedLeftLabel} vs {selectedRightLabel}</span>
      {!currentInstructorPair && <p className="mt-1 text-xs text-muted-foreground">{language === 'th' ? 'กด “กำหนดให้ฉัน” เพื่อเพิ่มคู่นี้ในรายการงานของคุณ' : 'Select “Assign to me” to add this pair to your assigned work.'}</p>}
    </div>}
    {coverageGaps.length > 0 && <div className="mt-3 rounded border p-2 text-sm">
      <strong>{language === 'th' ? `คู่ที่ยังขาดคำตอบตามเป้าหมาย ${belowTarget} คู่ · คู่ที่ผู้มีสิทธิ์ไม่ครบ 5 คน ${eligibilityShortage} คู่` : `${belowTarget} pairs below feasible submitted target · ${eligibilityShortage} pairs have fewer than five eligible evaluators`}</strong>
      <div className="mt-2 max-h-64 space-y-2 overflow-y-auto pr-1">
        {coverageGaps.map((row) => {
          const leftStudent = row.section === 'group' ? undefined : students.find((item) => item.id === row.left_id)
          const rightStudent = row.section === 'group' ? undefined : students.find((item) => item.id === row.right_id)
          const left = row.section === 'group' ? groups.find((item) => item.id === row.left_id)?.name : leftStudent?.display_name || leftStudent?.email
          const right = row.section === 'group' ? groups.find((item) => item.id === row.right_id)?.name : rightStudent?.display_name || rightStudent?.email
          const assignedPair = pairs.find((pair) => pair.section === row.section && pair.criterion === row.criterion
            && ((pair.left === left && pair.right === right) || (pair.left === right && pair.right === left)))
          const selected = criterionId === row.criterion_id
            && ((leftId === row.left_id && rightId === row.right_id) || (leftId === row.right_id && rightId === row.left_id))
          const unassigned = Math.max(0, row.target_evaluations - row.assigned_evaluators)
          const awaitingSubmission = Math.max(0, row.assigned_evaluators - row.votes)
          return <div key={`${row.criterion_id}:${row.left_id}:${row.right_id}`} className={selected ? 'rounded-md border border-primary/40 bg-primary/5 p-2.5' : 'rounded-md border border-border bg-background p-2.5'}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong className="min-w-0 break-words">{row.criterion}: {left} / {right}</strong>
              {assignedPair && <span className="shrink-0 rounded-full bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">{language === 'th' ? 'มอบหมายให้ฉันแล้ว' : 'Assigned to me'}</span>}
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{language === 'th' ? `ส่งแล้ว ${row.votes}/${row.target_evaluations} · ยังไม่มอบหมาย ${unassigned} · มอบหมายแล้วแต่ยังไม่ส่ง ${awaitingSubmission} · ผู้มีสิทธิ์ขาดจาก 5 อีก ${row.shortage_to_five}` : `submitted ${row.votes}/${row.target_evaluations} · not assigned ${unassigned} · assigned but not submitted ${awaitingSubmission} · eligible shortage to five ${row.shortage_to_five}`}</p>
            <button type="button" aria-pressed={selected} className={selected ? 'mt-2 min-h-10 rounded-md border border-primary bg-primary/10 px-3 py-1.5 font-semibold text-primary' : 'mt-2 min-h-10 rounded-md border border-border bg-background px-3 py-1.5 text-foreground hover:bg-muted'} onClick={() => {
              setCriterionId(row.criterion_id); setLeftId(row.left_id); setRightId(row.right_id); setStudentId(0)
              if (assignedPair) document.getElementById('instructor-assigned-pairs')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}>{assignedPair ? (language === 'th' ? 'ดูงานของฉัน' : 'View my task') : selected ? (language === 'th' ? 'เลือกคู่นี้แล้ว' : 'Selected') : (language === 'th' ? 'เลือกคู่นี้' : 'Select pair')}</button>
          </div>
        })}
      </div>
    </div>}
    <section id="instructor-assigned-pairs" tabIndex={-1} aria-labelledby="instructor-assigned-heading" data-testid="instructor-assigned-pairs" className="mt-6 scroll-mt-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div><h3 id="instructor-assigned-heading" className="font-semibold text-slate-900">{language === 'th' ? 'คู่ประเมินที่มอบหมายให้ฉัน' : 'Pairs assigned to me'}</h3><p className="mt-1 text-xs text-slate-500">{language === 'th' ? 'รายการนี้เป็นงานของบัญชีอาจารย์ที่กำลังใช้งาน' : 'These pairs belong to the instructor account you are using.'}</p></div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-sm font-semibold text-slate-700" aria-label={language === 'th' ? `${pairs.length} คู่ที่มอบหมายให้ฉัน` : `${pairs.length} pairs assigned to me`}>{pairs.length}</span>
      </div>
      {pairs.length === 0
        ? <p className="border-t border-slate-200 py-4 text-sm text-muted-foreground">{t('No instructor pairs assigned')}</p>
        : <div className="space-y-5">{groupedPairs.map((group) => <section key={`${group.section}:${group.criterion}`} aria-label={`${group.section} ${group.criterion}`} className="border-t border-slate-200 pt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-semibold text-slate-800">{t(group.section === 'group' ? 'Group evaluation' : 'Individual evaluation')} · {group.criterion}</h4>
            <span className="text-xs text-slate-500">{group.pairs.length} {t(group.pairs.length === 1 ? 'pair' : 'pairs')}</span>
          </div>
          <div className="divide-y divide-slate-100">{group.pairs.map((pair) => <div key={pair.pair_id} data-testid={`instructor-assigned-pair-${pair.pair_id}`} className="py-3 first:pt-1 last:pb-0">
            <div className="mb-2 flex justify-end">
              <span className={pair.choice !== null ? 'rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700' : pair.is_open ? 'rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-950' : 'rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700'}>
                {t(pair.choice !== null ? 'Answer saved' : pair.is_open ? 'Needs evaluation' : 'Closed')}
              </span>
            </div>
            <fieldset disabled={!pair.is_open || savingPairIds.has(pair.pair_id)} className="evaluation-pair !mt-0 !border-0 !bg-transparent !p-0">
              <legend className="sr-only">{group.criterion}: {pair.left} vs {pair.right}</legend>
              <div className="pair-candidates">
                <span className="pair-side">{pair.left}</span>
                <div className="choice-scale">{choices.map((label, index) => <label key={label} className="choice-option" title={t(label)}>
                  <input type="radio" name={`instructor-pair-${pair.pair_id}`} checked={pair.choice === index + 1}
                    onChange={() => void vote(pair.pair_id, index + 1)} /><span>{t(label)}</span>
                </label>)}</div>
                <span className="pair-side pair-side-right">{pair.right}</span>
              </div>
            </fieldset>
          </div>)}</div>
        </section>)}</div>}
    </section>
    <ToastNotice notice={message} />
  </div>
}
