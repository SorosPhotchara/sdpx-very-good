import { useEffect, useRef, useState } from 'react'
import {
  addInstructorPair, addStudentPair, getAssignmentReport, getCriteria, getGroups, getRawPairResponses,
  getInstructorPairs, getStudents, saveInstructorVote,
} from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { ToastNotice, useNotice } from './components/ui/toast'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { DisclosureSummary } from './components/ui/disclosure-summary'

const choices = ['Strongly left', 'Slightly left', 'Equal', 'Slightly right', 'Strongly right']
const pageSize = 8
const pairKey = (criterionId: number, leftId: number, rightId: number) => `${criterionId}:${Math.min(leftId, rightId)}:${Math.max(leftId, rightId)}`

export function InstructorEvaluation(props: { assignmentId: number; classroomId: number; email: string }) {
  const { t } = useLanguage()
  const [activated, setActivated] = useState(false)
  return <details onToggle={(event) => { if (event.currentTarget.open) setActivated(true) }} className="mt-4 border-t border-slate-200 pt-4 text-sm">
    <DisclosureSummary className="font-medium">{t('Instructor pairwise evaluation')}</DisclosureSummary>
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
  const [section, setSection] = useState<'group' | 'individual'>('group')
  const [groupId, setGroupId] = useState(0)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(0)
  const [evaluationPage, setEvaluationPage] = useState(0)
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(() => new Set())
  const [batchProgress, setBatchProgress] = useState(0)
  const [leftId, setLeftId] = useState(0)
  const [rightId, setRightId] = useState(0)
  const [studentId, setStudentId] = useState(0)
  const [message, setMessage] = useNotice()
  const [savingPairIds, setSavingPairIds] = useState<Set<number>>(() => new Set())
  const assignedSection = useRef<HTMLElement>(null)
  const pendingVotes = useRef(new Set<number>())
  const action = useAsyncLock()
  useEffect(() => {
    if (!resource.data) return
    const firstGroup = resource.data.criteria.find((item) => item.is_group)
    if (!firstGroup) setSection('individual')
    setCriterionId((current) => current || firstGroup?.id || resource.data?.criteria[0]?.id || 0)
  }, [resource.data])
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
  const assignedKeys = new Set(rawPairs.filter((pair) => pair.evaluator_student_id === null && pair.evaluator.toLowerCase() === email.toLowerCase())
    .map((pair) => pairKey(pair.criterion_id, pair.left_id, pair.right_id)))
  const rawById = new Map(rawPairs.map((pair) => [pair.pair_id, pair]))
  const activeCriteria = criteria.filter((item) => item.is_group === (section === 'group'))
  const visibleRows = (report?.coverage ?? []).filter((row) => {
    if (row.section !== section || row.criterion_id !== criterionId) return false
    const leftStudent = students.find((item) => item.id === row.left_id)
    if (section === 'individual' && groupId && leftStudent?.group_id !== groupId) return false
    const left = section === 'group' ? groups.find((item) => item.id === row.left_id)?.name : leftStudent?.email
    const right = section === 'group' ? groups.find((item) => item.id === row.right_id)?.name : students.find((item) => item.id === row.right_id)?.email
    return `${left} ${right}`.toLocaleLowerCase().includes(query.toLocaleLowerCase().trim())
  })
  const availableRows = visibleRows.filter((row) => !assignedKeys.has(pairKey(row.criterion_id, row.left_id, row.right_id)))
  const selectedRows = availableRows.filter((row) => selectedKeys.has(pairKey(row.criterion_id, row.left_id, row.right_id)))
  const pageCount = Math.max(1, Math.ceil(visibleRows.length / pageSize))
  const pageRows = visibleRows.slice(page * pageSize, (page + 1) * pageSize)
  const sectionClosed = section === 'group' ? report?.group_final : report?.individual_final
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
  const assignedInView = pairs.filter((pair) => {
    const raw = rawById.get(pair.pair_id)
    return pair.section === section && raw?.criterion_id === criterionId
      && (section === 'group' || !groupId || students.some((student) => student.id === raw.left_id && student.group_id === groupId))
  })
  const evaluationPageCount = Math.max(1, Math.ceil(assignedInView.length / pageSize))
  const groupedPairs = Object.values(assignedInView.slice(evaluationPage * pageSize, (evaluationPage + 1) * pageSize)
    .reduce<Record<string, { section: string; criterion: string; pairs: typeof pairs }>>((groups, pair) => {
    const key = `${pair.section}:${pair.criterion}`
    groups[key] ??= { section: pair.section, criterion: pair.criterion, pairs: [] }
    groups[key].pairs.push(pair)
    return groups
  }, {}))

  async function assignSelected() {
    if (!selectedRows.length || !action.begin()) return
    let completed = 0
    const failed: typeof selectedRows = []
    try {
      for (let index = 0; index < selectedRows.length; index += 4) {
        const chunk = selectedRows.slice(index, index + 4)
        const results = await Promise.allSettled(chunk.map((row) => addInstructorPair(assignmentId, {
          criteria_id: row.criterion_id, left_id: row.left_id, right_id: row.right_id, instructor_email: email,
        })))
        results.forEach((result, offset) => { if (result.status === 'fulfilled') completed += 1; else failed.push(chunk[offset]) })
        setBatchProgress(Math.min(index + chunk.length, selectedRows.length))
      }
      await resource.refresh()
      setSelectedKeys(new Set(failed.map((row) => pairKey(row.criterion_id, row.left_id, row.right_id))))
      setMessage(language === 'th' ? `มอบหมายสำเร็จ ${completed} คู่${failed.length ? ` · ไม่สำเร็จ ${failed.length} คู่` : ''}` : `Assigned ${completed} pairs${failed.length ? ` · ${failed.length} failed` : ''}`, failed.length ? 'error' : 'success')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not refresh assigned pairs.', 'error')
    } finally {
      setBatchProgress(0)
      action.finish()
    }
  }

  async function assignStudent() {
    if (!action.begin()) return
    try {
      await addStudentPair(assignmentId, { criteria_id: criterionId, left_id: leftId, right_id: rightId, student_id: studentId })
      setStudentId(0)
      await resource.refresh()
      setMessage(language === 'th' ? 'ส่งคู่ประเมินเพิ่มให้นักศึกษาแล้ว' : 'Extra pair assigned to student.')
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

  function changeEvaluationPage(nextPage: number) {
    setEvaluationPage(nextPage)
    requestAnimationFrame(() => {
      assignedSection.current?.focus({ preventScroll: true })
      assignedSection.current?.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'start',
      })
    })
  }

  return <div>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดการประเมินของอาจารย์...' : 'Loading instructor evaluation...'}</p>}
    {resource.error && <div role="alert">{resource.error} <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button></div>}
    <div className="mt-4 space-y-4" data-testid="instructor-pair-planner">
      <div className="flex flex-wrap gap-2" role="group" aria-label={language === 'th' ? 'ประเภทการประเมิน' : 'Evaluation type'}>
        {(['group', 'individual'] as const).map((mode) => <Button key={mode} type="button" variant={section === mode ? 'default' : 'outline'} aria-pressed={section === mode}
          onClick={() => { setSection(mode); setCriterionId(criteria.find((item) => item.is_group === (mode === 'group'))?.id || 0); setLeftId(0); setRightId(0); setGroupId(0); setQuery(''); setPage(0); setEvaluationPage(0); setSelectedKeys(new Set()) }}>
          {t(mode === 'group' ? 'Group evaluation' : 'Individual evaluation')} <span className="opacity-70">{report?.coverage.filter((row) => row.section === mode).length ?? 0}</span>
        </Button>)}
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.4fr)]">
        <select aria-label={t('Criterion')} value={criterionId} onChange={(event) => { setCriterionId(Number(event.target.value)); setLeftId(0); setRightId(0); setPage(0); setEvaluationPage(0); setSelectedKeys(new Set()) }} className="min-h-10 min-w-0 rounded-lg border border-input bg-background px-3 text-sm">
          {activeCriteria.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        {section === 'individual' && <select aria-label={language === 'th' ? 'กรองตามกลุ่ม' : 'Filter by group'} value={groupId} onChange={(event) => { setGroupId(Number(event.target.value)); setPage(0); setSelectedKeys(new Set()) }} className="min-h-10 min-w-0 rounded-lg border border-input bg-background px-3 text-sm">
          <option value={0}>{language === 'th' ? 'ทุกกลุ่ม' : 'All groups'}</option>
          {groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>}
        <Input type="search" aria-label={language === 'th' ? 'ค้นหาคู่ประเมิน' : 'Search pairs'} placeholder={language === 'th' ? 'ค้นหาชื่อกลุ่มหรืออีเมล' : 'Search groups or email'} value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); setSelectedKeys(new Set()) }} className={section === 'group' ? 'sm:col-span-1 lg:col-start-3' : ''} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <p className="text-sm text-muted-foreground">{language === 'th' ? `${visibleRows.length} คู่ในรายการ · มอบหมายให้ฉันแล้ว ${visibleRows.length - availableRows.length} คู่` : `${visibleRows.length} pairs · ${visibleRows.length - availableRows.length} assigned to me`}</p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" disabled={action.busy || sectionClosed || !availableRows.length} onClick={() => setSelectedKeys(new Set(availableRows.map((row) => pairKey(row.criterion_id, row.left_id, row.right_id))))}>{language === 'th' ? 'เลือกคู่ที่ยังไม่ได้ทั้งหมด' : 'Select all unassigned'}</Button>
          {selectedRows.length > 0 && <Button type="button" variant="ghost" size="sm" disabled={action.busy} onClick={() => setSelectedKeys(new Set())}>{language === 'th' ? 'ล้างที่เลือก' : 'Clear'}</Button>}
          <Button type="button" size="sm" data-testid="assign-instructor-pair" disabled={action.busy || sectionClosed || !selectedRows.length} aria-busy={action.busy} onClick={() => void assignSelected()}>{action.busy ? `${batchProgress}/${selectedRows.length}` : language === 'th' ? `มอบหมายให้ฉัน ${selectedRows.length} คู่` : `Assign ${selectedRows.length} to me`}</Button>
        </div>
      </div>
      {sectionClosed && <p className="text-sm text-amber-800" role="status">{language === 'th' ? 'หมดกำหนดประเมินแล้ว จึงมอบหมายคู่เพิ่มไม่ได้' : 'The deadline has passed; no more pairs can be assigned.'}</p>}
      <div className="divide-y divide-border rounded-xl border border-border bg-background">
        {pageRows.length === 0 && <p className="p-4 text-muted-foreground">{language === 'th' ? 'ไม่พบคู่ประเมินในตัวกรองนี้' : 'No pairs match these filters.'}</p>}
        {pageRows.map((row) => {
          const key = pairKey(row.criterion_id, row.left_id, row.right_id)
          const assigned = assignedKeys.has(key)
          const left = row.section === 'group' ? groups.find((item) => item.id === row.left_id)?.name : students.find((item) => item.id === row.left_id)?.email
          const right = row.section === 'group' ? groups.find((item) => item.id === row.right_id)?.name : students.find((item) => item.id === row.right_id)?.email
          return <label key={key} className={`flex cursor-pointer items-start gap-3 p-3 sm:items-center ${assigned ? 'bg-slate-50/70' : 'hover:bg-indigo-50/50'}`}>
            <input type="checkbox" checked={assigned || selectedKeys.has(key)} disabled={assigned || action.busy || sectionClosed} onChange={(event) => setSelectedKeys((current) => { const next = new Set(current); if (event.target.checked) next.add(key); else next.delete(key); return next })} className="mt-1 size-4 shrink-0 accent-primary sm:mt-0" aria-label={`${left} / ${right}`} />
            <span className="min-w-0 flex-1"><span className="block break-words font-medium text-foreground">{left} <span className="px-1 text-muted-foreground">vs</span> {right}</span><span className="block text-xs text-muted-foreground">{language === 'th' ? `นักศึกษาส่งแล้ว ${row.votes}/${row.target_evaluations}` : `Student responses ${row.votes}/${row.target_evaluations}`}{row.shortage_to_five > 0 ? (language === 'th' ? ` · ผู้มีสิทธิ์ไม่ครบ 5 คน` : ` · fewer than 5 eligible`) : ''}</span></span>
            {assigned && <span className="shrink-0 rounded-full bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">{language === 'th' ? 'มอบหมายแล้ว' : 'Assigned'}</span>}
          </label>
        })}
      </div>
      {pageCount > 1 && <div className="flex items-center justify-end gap-2"><Button type="button" variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>{language === 'th' ? 'ก่อนหน้า' : 'Previous'}</Button><span className="text-xs text-muted-foreground">{page + 1}/{pageCount}</span><Button type="button" variant="outline" size="sm" disabled={page + 1 >= pageCount} onClick={() => setPage(page + 1)}>{language === 'th' ? 'ถัดไป' : 'Next'}</Button></div>}
    </div>
    <details className="mt-4 rounded-xl border border-border p-3 text-sm">
      <DisclosureSummary className="font-medium text-foreground">{language === 'th' ? 'ส่งคู่เพิ่มให้นักศึกษา' : 'Assign an extra pair to a student'}</DisclosureSummary>
      <p className="mt-2 text-muted-foreground">{language === 'th' ? 'นักศึกษาหนึ่งคนประเมินคู่เดียวกันได้หนึ่งครั้ง' : 'Each student can evaluate a pair once.'}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {(['left', 'right'] as const).map((side) => <select key={side} aria-label={t(side + ' item')} value={side === 'left' ? leftId : rightId} onChange={(event) => { if (side === 'left') setLeftId(Number(event.target.value)); else setRightId(Number(event.target.value)); setStudentId(0) }} className="min-h-10 min-w-0 flex-1 rounded-lg border border-input bg-background px-3 text-sm"><option value={0}>{t(side + ' item')}</option>{candidates.map((item) => <option key={item.id} value={item.id}>{'email' in item ? item.email : item.name}</option>)}</select>)}
        <select aria-label={language === 'th' ? 'นักศึกษาผู้ประเมิน' : 'Student evaluator'} value={studentId} onChange={(event) => setStudentId(Number(event.target.value))} className="min-h-10 min-w-0 flex-1 rounded-lg border border-input bg-background px-3 text-sm"><option value={0}>{language === 'th' ? 'เลือกนักศึกษาผู้ประเมิน' : 'Choose student evaluator'}</option>{eligibleStudents.map((student) => <option key={student.id} value={student.id}>{student.email}</option>)}</select>
        <Button type="button" data-testid="assign-student-pair" disabled={action.busy || !studentId || !eligibleStudents.some((student) => student.id === studentId)} onClick={() => void assignStudent()}>{language === 'th' ? 'ส่งคู่ให้นักศึกษา' : 'Assign to student'}</Button>
      </div>
      {criterion && leftId && rightId && leftId !== rightId && <p className="mt-2 text-muted-foreground" data-testid="instructor-pair-selection-status">{criterion.name}: {selectedLeftLabel} vs {selectedRightLabel}</p>}
    </details>
    <section ref={assignedSection} id="instructor-assigned-pairs" tabIndex={-1} aria-labelledby="instructor-assigned-heading" data-testid="instructor-assigned-pairs" className="mt-6 scroll-mt-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div><h3 id="instructor-assigned-heading" className="font-semibold text-slate-900">{language === 'th' ? 'คู่ประเมินที่มอบหมายให้ฉัน' : 'Pairs assigned to me'}</h3><p className="mt-1 text-xs text-slate-500">{language === 'th' ? `เกณฑ์ ${criterion?.name || '—'} · รอประเมิน ${assignedInView.filter((pair) => pair.choice === null).length} คู่` : `${criterion?.name || '—'} · ${assignedInView.filter((pair) => pair.choice === null).length} awaiting evaluation`}</p></div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-sm font-semibold text-slate-700" aria-label={language === 'th' ? `${assignedInView.length} คู่ที่มอบหมายให้ฉันในรายการนี้` : `${assignedInView.length} pairs assigned to me in this view`}>{assignedInView.length}</span>
      </div>
      {assignedInView.length === 0
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
                <span>{pair.left}</span><span className="pair-versus" aria-hidden="true">VS</span><span>{pair.right}</span>
              </div>
              <div className="choice-scale">{choices.map((label, index) => <label key={label} className="choice-option">
                <input type="radio" name={`instructor-pair-${pair.pair_id}`} checked={pair.choice === index + 1}
                  onChange={() => void vote(pair.pair_id, index + 1)} /><span>{t(label)}</span>
              </label>)}</div>
            </fieldset>
          </div>)}</div>
        </section>)}</div>}
      {evaluationPageCount > 1 && <div className="mt-4 flex items-center justify-end gap-2"><Button type="button" variant="outline" size="sm" disabled={evaluationPage === 0} onClick={() => changeEvaluationPage(evaluationPage - 1)}>{language === 'th' ? 'ก่อนหน้า' : 'Previous'}</Button><span className="text-xs text-muted-foreground">{evaluationPage + 1}/{evaluationPageCount}</span><Button type="button" variant="outline" size="sm" disabled={evaluationPage + 1 >= evaluationPageCount} onClick={() => changeEvaluationPage(evaluationPage + 1)}>{language === 'th' ? 'ถัดไป' : 'Next'}</Button></div>}
    </section>
    <ToastNotice notice={message} />
  </div>
}
