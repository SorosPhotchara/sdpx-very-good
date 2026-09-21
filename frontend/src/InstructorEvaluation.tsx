import { useEffect, useState } from 'react'
import {
  addInstructorPair, getCriteria, getGroups, getInstructorPairs, getStudents, saveInstructorVote,
  type Criterion, type Group, type InstructorPair, type Student,
} from './api'
import { useLanguage } from './i18n'

const choices = ['Strongly left', 'Slightly left', 'Equal', 'Slightly right', 'Strongly right']

export function InstructorEvaluation({ assignmentId, classroomId, email }: {
  assignmentId: number; classroomId: number; email: string
}) {
  const { t } = useLanguage()
  const [criteria, setCriteria] = useState<Criterion[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [students, setStudents] = useState<Student[]>([])
  const [pairs, setPairs] = useState<InstructorPair[]>([])
  const [criterionId, setCriterionId] = useState(0)
  const [leftId, setLeftId] = useState(0)
  const [rightId, setRightId] = useState(0)
  const [message, setMessage] = useState('')

  async function refresh() {
    try {
      const [items, groupItems, studentItems, assigned] = await Promise.all([
        getCriteria(assignmentId), getGroups(classroomId), getStudents(classroomId), getInstructorPairs(assignmentId),
      ])
      setCriteria(items); setGroups(groupItems); setStudents(studentItems); setPairs(assigned)
      setCriterionId((current) => current || items[0]?.id || 0)
      setMessage('')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not load instructor evaluations.')
    }
  }

  useEffect(() => { void refresh() }, [assignmentId, classroomId])

  const criterion = criteria.find((item) => item.id === criterionId)
  const candidates = criterion?.is_group ? groups : students

  async function assign() {
    try {
      await addInstructorPair(assignmentId, { criteria_id: criterionId, left_id: leftId, right_id: rightId, instructor_email: email })
      setPairs(await getInstructorPairs(assignmentId))
      setMessage(t('Instructor pair assigned.'))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not assign pair.')
    }
  }

  async function vote(pairId: number, choice: number) {
    try {
      await saveInstructorVote(assignmentId, pairId, choice)
      setPairs(await getInstructorPairs(assignmentId))
      setMessage(t('Vote saved.'))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save vote.')
    }
  }

  return <details className="mt-3 rounded-xl border p-3 text-sm">
    <summary className="cursor-pointer font-medium">{t('Instructor pairwise evaluation')}</summary>
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
      <button type="button" disabled={!criterionId || !leftId || !rightId || leftId === rightId} onClick={() => void assign()}
        className="rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-50">{t('Assign to me')}</button>
    </div>
    <div className="mt-3 space-y-2">{pairs.map((pair) => <fieldset key={pair.pair_id} disabled={!pair.is_open} className="rounded border p-2">
      <legend>{pair.criterion}: {pair.left} / {pair.right}</legend>
      <div className="flex flex-wrap gap-2">{choices.map((label, index) => <label key={label} className="inline-flex items-center gap-1">
        <input type="radio" name={`instructor-pair-${pair.pair_id}`} checked={pair.choice === index + 1}
          onChange={() => void vote(pair.pair_id, index + 1)} />{t(label)}
      </label>)}</div>
    </fieldset>)}</div>
    {message && <p role="status" className="mt-2">{message}</p>}
  </details>
}
