import { useEffect, useRef, useState } from 'react'
import {
  addInstructorPair, getCriteria, getGroups, getInstructorPairs, getStudents, saveInstructorVote,
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
    const [criteria, groups, students, pairs] = await Promise.all([getCriteria(assignmentId), getGroups(classroomId), getStudents(classroomId), getInstructorPairs(assignmentId)])
    return { criteria, groups, students, pairs }
  })
  const { criteria = [], groups = [], students = [], pairs = [] } = resource.data ?? {}
  const [criterionId, setCriterionId] = useState(0)
  const [leftId, setLeftId] = useState(0)
  const [rightId, setRightId] = useState(0)
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

  async function assign() {
    if (!action.begin()) return
    try {
      await addInstructorPair(assignmentId, { criteria_id: criterionId, left_id: leftId, right_id: rightId, instructor_email: email })
      const assigned = await getInstructorPairs(assignmentId)
      resource.setData((current) => current ? { ...current, pairs: assigned } : current)
      setMessage(t('Instructor pair assigned.'))
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
      <select aria-label={t('Criterion')} value={criterionId} onChange={(event) => { setCriterionId(Number(event.target.value)); setLeftId(0); setRightId(0) }} className="rounded border p-2">
        <option value={0}>{t('Choose criterion')}</option>
        {criteria.map((item) => <option key={item.id} value={item.id}>{t(item.is_group ? 'Group' : 'Individual')}: {item.name}</option>)}
      </select>
      {(['left', 'right'] as const).map((side) => <select key={side} aria-label={t(side + ' item')} value={side === 'left' ? leftId : rightId}
        onChange={(event) => side === 'left' ? setLeftId(Number(event.target.value)) : setRightId(Number(event.target.value))}
        className="rounded border p-2">
        <option value={0}>{t(side + ' item')}</option>
        {candidates.map((item) => <option key={item.id} value={item.id}>{'email' in item ? item.email : item.name}</option>)}
      </select>)}
      <button type="button" disabled={action.busy || resource.loading || !criterionId || !leftId || !rightId || leftId === rightId} aria-busy={action.busy} onClick={() => void assign()}
        className="rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50">{t(action.busy ? 'Working...' : 'Assign to me')}</button>
    </div>
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
