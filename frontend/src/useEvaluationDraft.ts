import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { saveEvaluationDraft, type EvaluationPage } from './api'

// Serialize writes, coalesce pending choices and preserve newer optimistic edits.
export function useEvaluationDraft(assignmentId: number, section: string,
  setPage: Dispatch<SetStateAction<EvaluationPage | null>>, onSaved: () => void, onError: (error: string) => void) {
  const pending = useRef(new Map<number, number>())
  const running = useRef(false)
  const generation = useRef(0)
  const callbacks = useRef({ onSaved, onError })
  callbacks.current = { onSaved, onError }
  const [saving, setSaving] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    pending.current = new Map()
    running.current = false
    setSaving(false)
    setFailed(false)
    return () => { generation.current++ }
  }, [assignmentId, section])

  async function flush() {
    if (running.current || !pending.current.size) return
    const requestGeneration = generation.current
    running.current = true
    setSaving(true)
    setFailed(false)
    try {
      while (pending.current.size) {
        const batch = new Map(pending.current)
        const updated = await saveEvaluationDraft(assignmentId, section,
          [...batch].map(([pair_id, choice]) => ({ pair_id, choice })))
        if (requestGeneration !== generation.current) return
        for (const [id, choice] of batch) {
          if (pending.current.get(id) === choice) pending.current.delete(id)
        }
        setPage({ ...updated, pairs: updated.pairs.map(pair => pending.current.has(pair.id)
          ? { ...pair, draft_choice: pending.current.get(pair.id)! } : pair) })
      }
      callbacks.current.onSaved()
    } catch (error) {
      if (requestGeneration !== generation.current) return
      // Retain unsaved edits for an explicit retry; never claim they were saved.
      setFailed(true)
      callbacks.current.onError(error instanceof Error ? error.message : 'Draft could not be saved.')
    } finally {
      if (requestGeneration === generation.current) {
        running.current = false
        setSaving(false)
      }
    }
  }

  function choose(pairId: number, choice: number) {
    pending.current.set(pairId, choice)
    setPage(current => current ? { ...current, pairs: current.pairs.map(pair => pair.id === pairId
      ? { ...pair, draft_choice: choice } : pair) } : current)
    void flush()
  }

  return { choose, saving, failed, retry: () => void flush() }
}
