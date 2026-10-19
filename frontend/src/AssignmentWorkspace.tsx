import { Button } from './components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog'
import { Input } from './components/ui/input'
import { useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { Plus, X } from 'lucide-react'
import {
  createAssignment, getAssignments, getAssignmentSetup, previewAssignment, publishAssignment, updateAssignmentSetup,
  type Assignment, type AssignmentSetup, type PairPreview, type PairPreviewItem,
} from './api'
import { EvaluationWorkspace } from './EvaluationWorkspace'
import { ScoreWorkspace } from './ScoreWorkspace'
import { InstructorEvaluation } from './InstructorEvaluation'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { ToastNotice, useDismissActiveNotice, useNotice } from './components/ui/toast'

type CriterionDraft = { name: string; weight: string }
type SectionDraft = {
  score: string
  participation: string
  deadline: string
  criteria: CriterionDraft[]
}

function SectionEditor({
  title, value, onChange,
}: {
  title: string
  value: SectionDraft
  onChange: (value: SectionDraft) => void
}) {
  const { t, language } = useLanguage()
  const update = (changes: Partial<SectionDraft>) => onChange({ ...value, ...changes })
  const updateCriterion = (index: number, changes: Partial<CriterionDraft>) => {
    update({ criteria: value.criteria.map((item, current) => current === index ? { ...item, ...changes } : item) })
  }
  const active = Number(value.score) > 0 || Number(value.participation) > 0
  const totalWeight = value.criteria.reduce((total, item) => total + Number(item.weight || 0), 0)

  return <fieldset className="assignment-section grid gap-3 rounded-xl border border-slate-200 p-4">
    <legend className="font-medium">{title}</legend>
    <label className="block text-sm">{t('Work score maximum')}
      <Input type="number" min="0" value={value.score} onChange={(event) => update({ score: event.target.value })} className="mt-1" />
    </label>
    <label className="block text-sm">{t('Participation maximum')}
      <Input type="number" min="0" value={value.participation} onChange={(event) => update({ participation: event.target.value })} className="mt-1" />
    </label>
    <label className="block text-sm">{t('Deadline')}
      <Input type="datetime-local" required={active} value={value.deadline} onChange={(event) => update({ deadline: event.target.value })} className="mt-1" />
    </label>
    {value.criteria.map((criterion, index) => <div key={index} className="criterion-row flex flex-wrap gap-2 items-end">
      <label className="text-sm flex-1">{t('Criterion')}
        <Input value={criterion.name} onChange={(event) => updateCriterion(index, { name: event.target.value })} className="mt-1" />
      </label>
      <label className="text-sm w-24">{t('Weight %')}
        <Input type="number" min="1" max="100" value={criterion.weight} onChange={(event) => updateCriterion(index, { weight: event.target.value })} className="mt-1" />
      </label>
      <Button type="button" onClick={() => update({ criteria: value.criteria.filter((_, current) => current !== index) })} variant="ghost" className="text-destructive">{t('Remove')}</Button>
    </div>)}
    {active && <p role="status" className={Math.abs(totalWeight - 100) < 0.001 ? 'text-sm text-primary' : 'text-sm text-destructive'}>
      {language === 'th' ? `น้ำหนักเกณฑ์รวม ${totalWeight}% / 100%` : `Criterion weights: ${totalWeight}% / 100%`}
    </p>}
    <Button type="button" onClick={() => update({ criteria: [...value.criteria, { name: '', weight: '' }] })} variant="outline" size="sm">{t('Add criterion')}</Button>
  </fieldset>
}

function toDeadline(value: string): string | null {
  return value ? new Date(value).toISOString() : null
}

function toLocalInput(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

function PairPreviewPanel({ preview }: { preview: PairPreview }) {
  const { language } = useLanguage()
  const grouped = new Map<string, { pair: PairPreviewItem; count: number }>()
  for (const pair of preview.pairs) {
    const key = JSON.stringify([pair.section, pair.criterion, pair.left, pair.right, pair.evaluator])
    const existing = grouped.get(key)
    if (existing) existing.count += 1
    else grouped.set(key, { pair, count: 1 })
  }

  return <section className="pair-plan-preview" aria-label={language === 'th' ? 'ตัวอย่างคู่ประเมิน' : 'Pair assignment preview'}>
    <div className="pair-plan-heading">
      <div><strong>{language === 'th' ? 'ตัวอย่างแผนประเมิน' : 'Evaluation plan preview'}</strong>
        <p>{language === 'th' ? 'ยังไม่เผยแพร่ นักศึกษายังไม่เห็นแบบประเมิน' : 'Not published; students cannot see this evaluation yet.'}</p></div>
      <span>{preview.pair_assignments} {language === 'th' ? 'งานประเมิน' : 'pair assignments'}</span>
    </div>
    <div className="pair-plan-list">
      {[...grouped.values()].map(({ pair, count }, index) => <article key={`${pair.section}-${pair.criterion}-${pair.left}-${pair.right}-${pair.evaluator}-${index}`}>
        <div><strong>{pair.section === 'group' ? (language === 'th' ? 'ประเมินกลุ่ม' : 'Group') : (language === 'th' ? 'ประเมินรายบุคคล' : 'Individual')} · {pair.criterion}</strong>
          <span>{pair.left} <b>VS</b> {pair.right}</span></div>
        <div className="pair-plan-reviewer"><small>{language === 'th' ? 'ผู้ประเมิน' : 'Evaluator'}</small><span>{pair.evaluator}</span>
          {count > 1 && <em>×{count} {language === 'th' ? 'ครั้ง' : 'assignments'}</em>}</div>
      </article>)}
    </div>
  </section>
}

export function AssignmentWorkspace({ classroomId, isInstructor, email, actionTarget }: { classroomId: number; isInstructor: boolean; email: string; actionTarget: HTMLElement | null }) {
  const { t, language } = useLanguage()
  const resource = useResource(`${classroomId}`, () => getAssignments(classroomId))
  const assignments = resource.data ?? []
  const [title, setTitle] = useState('')
  const [group, setGroup] = useState<SectionDraft>({ score: '10', participation: '0', deadline: '', criteria: [{ name: 'Quality', weight: '100' }] })
  const [individual, setIndividual] = useState<SectionDraft>({ score: '0', participation: '0', deadline: '', criteria: [] })
  const [instructorWeight, setInstructorWeight] = useState('1')
  const [status, setStatus] = useNotice()
  const dismissActiveNotice = useDismissActiveNotice()
  const action = useAsyncLock()
  const busy = action.busy
  const [editId, setEditId] = useState<number | null>(null)
  const [editorOpen, setEditorOpen] = useState(false)
  const [pairPreviews, setPairPreviews] = useState<Record<number, PairPreview>>({})
  const [pairAction, setPairAction] = useState<{ id: number; publish: boolean } | null>(null)
  const totalScore = Number(group.score || 0) + Number(individual.score || 0)
    + Number(group.participation || 0) + Number(individual.participation || 0)

  function openCreateEditor() {
    dismissActiveNotice()
    setEditId(null)
    setTitle('')
    setGroup({ score: '10', participation: '0', deadline: '', criteria: [{ name: 'Quality', weight: '100' }] })
    setIndividual({ score: '0', participation: '0', deadline: '', criteria: [] })
    setInstructorWeight('1')
    setStatus('')
    setEditorOpen(true)
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    for (const [section, label] of [[group, t('Group evaluation')], [individual, t('Individual evaluation')]] as const) {
      const active = Number(section.score) > 0 || Number(section.participation) > 0
      const total = section.criteria.reduce((sum, item) => sum + Number(item.weight || 0), 0)
      if (active && Math.abs(total - 100) >= 0.001) {
        setStatus(language === 'th'
          ? `น้ำหนักเกณฑ์${label}รวม ${total}% ต้องรวม 100%`
          : `${label} weights total ${total}%; they must total 100%.`, 'error')
        return
      }
    }
    if (!action.begin()) return
    try {
    const setup: AssignmentSetup & { total_score: number } = {
      title,
      group_score: Number(group.score),
      individual_score: Number(individual.score),
      group_participation_max: Number(group.participation),
      individual_participation_max: Number(individual.participation),
      total_score: totalScore,
      instructor_weight: Number(instructorWeight),
      group_deadline: toDeadline(group.deadline),
      individual_deadline: toDeadline(individual.deadline),
      group_criteria: group.criteria.map((item) => ({ name: item.name, weight: Number(item.weight) })),
      individual_criteria: individual.criteria.map((item) => ({ name: item.name, weight: Number(item.weight) })),
    }
      const created = editId == null ? await createAssignment(classroomId, setup) : await updateAssignmentSetup(editId, setup)
      resource.setData((current) => editId == null ? [...(current ?? []), created] : (current ?? []).map((item) => item.id === editId ? created : item))
      setTitle('')
      setEditId(null)
      setEditorOpen(false)
      setStatus(t(editId == null ? 'Assignment created.' : 'Assignment updated.'))
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not create assignment.', 'error')
    } finally {
      action.finish()
    }
  }

  async function beginEdit(assignmentId: number) {
    if (!action.begin()) return
    try {
      const setup = await getAssignmentSetup(assignmentId)
      setEditId(assignmentId)
      setTitle(setup.title)
      const section = (prefix: 'group' | 'individual'): SectionDraft => ({
        score: String(setup[`${prefix}_score`]),
        participation: String(setup[`${prefix}_participation_max`]),
        deadline: toLocalInput(setup[`${prefix}_deadline`]),
        criteria: setup[`${prefix}_criteria`].map((item) => ({ name: item.name, weight: String(item.weight) })),
      })
      setGroup(section('group'))
      setIndividual(section('individual'))
      setInstructorWeight(String(setup.instructor_weight))
      setStatus('')
      setEditorOpen(true)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not load assignment setup.', 'error')
    } finally {
      action.finish()
    }
  }

  async function handlePairs(assignmentId: number, shouldPublish: boolean) {
    if (busy) return
    if (!shouldPublish && pairPreviews[assignmentId]) {
      setPairPreviews((current) => { const next = { ...current }; delete next[assignmentId]; return next })
      setStatus('')
      return
    }
    if (!action.begin()) return
    setPairAction({ id: assignmentId, publish: shouldPublish })
    try {
      if (!shouldPublish) {
        const result = await previewAssignment(assignmentId)
        setPairPreviews((current) => ({ ...current, [assignmentId]: result }))
        setStatus(language === 'th' ? `ตัวอย่างแผนมี ${result.pair_assignments} งานประเมิน` : `Preview contains ${result.pair_assignments} pair assignments.`, 'info')
        return
      }
        const result = await publishAssignment(assignmentId)
        resource.setData((current) => current?.map((item) => item.id === assignmentId ? { ...item, published_at: new Date().toISOString() } : item) ?? [])
      setPairPreviews((current) => { const next = { ...current }; delete next[assignmentId]; return next })
      await resource.refresh()
      setStatus(language === 'th' ? (shouldPublish ? 'เผยแพร่' : 'ตัวอย่าง') + 'คู่ประเมิน ' + result.pair_assignments + ' รายการ' : result.pair_assignments + ' pair assignments ' + (shouldPublish ? 'published' : 'in preview') + '.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Pair operation failed.', 'error')
    } finally {
      action.finish()
      setPairAction(null)
    }
  }

  return <div className="mt-4 space-y-3">
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดงานประเมิน...' : 'Loading assignments...'}</p>}
    {resource.error && <div role="alert">{resource.error} <Button type="button" variant="outline" onClick={() => void resource.refresh()}>{t('Retry')}</Button></div>}
    {!resource.loading && !resource.error && assignments.length === 0 && <div className="assignment-empty">
      <strong>{t('No assignments yet.')}</strong>
      <p>{isInstructor
        ? language === 'th' ? 'กด “สร้างแบบประเมิน” เพื่อกำหนดเกณฑ์และวันครบกำหนด จากนั้นดูตัวอย่างคู่ก่อนเผยแพร่ให้นักศึกษา' : 'Select “Create assignment” to set criteria and deadlines, then preview the pairs before publishing to students.'
        : language === 'th' ? 'งานประเมินจะแสดงที่นี่เมื่ออาจารย์เพิ่มงาน หากยังไม่พบงาน ให้สอบถามอาจารย์ประจำห้องเรียน' : 'Evaluations will appear here when your instructor adds an assignment. If you are expecting one, ask your classroom instructor.'}</p>
    </div>}
    {assignments.map((assignment, index) => <div key={assignment.id} className="assignment-card border rounded-xl p-3 text-sm">
      <span>{assignment.title}</span>
      {isInstructor && <span className="ml-3 inline-flex gap-2">
        {!assignment.published_at && <>
          <Button type="button" disabled={busy || resource.loading} aria-expanded={Boolean(pairPreviews[assignment.id])} aria-controls={`pair-preview-${assignment.id}`} aria-busy={pairAction?.id === assignment.id && !pairAction.publish} variant="outline" onClick={() => void handlePairs(assignment.id, false)}>{pairAction?.id === assignment.id && !pairAction.publish ? (language === 'th' ? 'กำลังสร้างตัวอย่าง...' : 'Preparing preview...') : t(pairPreviews[assignment.id] ? 'Hide preview' : 'Preview pairs')}</Button>
          <Button type="button" disabled={busy || resource.loading} variant="outline" onClick={() => void beginEdit(assignment.id)}>{t('Edit')}</Button>
          <Button type="button" disabled={busy || resource.loading} aria-busy={pairAction?.id === assignment.id && pairAction.publish} className="publish-action" onClick={() => void handlePairs(assignment.id, true)}>{pairAction?.id === assignment.id && pairAction.publish ? (language === 'th' ? 'กำลังเผยแพร่...' : 'Publishing...') : t('Publish')}</Button>
        </>}
        {assignment.published_at && <span className="text-primary">{t('Published')}</span>}
      </span>}
      {isInstructor && pairPreviews[assignment.id] && <div id={`pair-preview-${assignment.id}`}><PairPreviewPanel preview={pairPreviews[assignment.id]} /></div>}
      {!isInstructor && <>
        <EvaluationWorkspace assignmentId={assignment.id} section="group" initiallyOpen={index === 0} />
        <EvaluationWorkspace assignmentId={assignment.id} section="individual" />
      </>}
      <ScoreWorkspace assignmentId={assignment.id} isInstructor={isInstructor} />
      {isInstructor && assignment.published_at && <InstructorEvaluation assignmentId={assignment.id} classroomId={classroomId} email={email} />}
    </div>)}
    {isInstructor && <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
      {actionTarget && createPortal(<DialogTrigger asChild>
        <Button type="button" className="w-full justify-start gap-2" disabled={busy} data-testid="create-assignment" onClick={openCreateEditor}><Plus size={16} aria-hidden="true" />{language === 'th' ? 'สร้างแบบประเมิน' : 'Create assignment'}</Button>
      </DialogTrigger>, actionTarget)}
      <DialogContent data-testid="assignment-editor-dialog" className="flex max-h-[min(90dvh,52rem)] max-w-3xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="relative shrink-0 border-b px-4 py-4 pr-16 sm:px-5">
          <DialogTitle>{editId == null ? (language === 'th' ? 'สร้างแบบประเมิน' : 'Create assignment') : (language === 'th' ? 'แก้ไขแบบประเมิน' : 'Edit assignment')}</DialogTitle>
          <DialogDescription>{language === 'th' ? 'กำหนดคะแนน เกณฑ์ และวันครบกำหนดของแบบประเมิน' : 'Set scores, criteria, and deadlines for this assignment.'}</DialogDescription>
          <DialogClose asChild><Button type="button" variant="ghost" size="icon" className="absolute right-2 top-2 h-11 w-11" aria-label={language === 'th' ? 'ปิดหน้าต่าง' : 'Close dialog'}><X size={20} aria-hidden="true" /></Button></DialogClose>
        </DialogHeader>
        <form onSubmit={(event) => void handleCreate(event)} className="flex min-h-0 flex-1 flex-col">
          <div className="assignment-editor-scroll min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5" role="region" aria-label={language === 'th' ? 'รายละเอียดแบบประเมิน' : 'Assignment details'} tabIndex={0}>
            <fieldset disabled={busy} className="grid gap-4">
              <label className="block text-sm">{t('Title')}<Input required value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1" /></label>
              <SectionEditor title={t('Group evaluation')} value={group} onChange={setGroup} />
              <SectionEditor title={t('Individual evaluation')} value={individual} onChange={setIndividual} />
              <p className="text-sm font-medium" data-testid="assignment-total-score">{language === 'th' ? 'คะแนนเต็มรวม' : 'Assignment total maximum'}: {totalScore.toFixed(2)}</p>
              <label className="block text-sm">{t('Instructor vote weight')}<Input type="number" min="0.1" step="0.1" value={instructorWeight} onChange={(event) => setInstructorWeight(event.target.value)} className="mt-1" /></label>
            </fieldset>
          </div>
          <div className="flex shrink-0 items-center justify-end border-t px-4 py-3 sm:px-5"><Button disabled={busy} aria-busy={busy} type="submit">{busy ? t('Working...') : editId == null ? (language === 'th' ? 'สร้างแบบประเมิน' : 'Create assignment') : t('Save assignment')}</Button></div>
        </form>
      </DialogContent>
    </Dialog>}
    <ToastNotice notice={status} />
  </div>
}
