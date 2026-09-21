import { useEffect, useState } from 'react'
import { getEvaluation, saveEvaluationDraft, submitEvaluation, type EvaluationPage } from './api'
import { useLanguage } from './i18n'

const choices = ['Strongly left', 'Slightly left', 'Equal', 'Slightly right', 'Strongly right']

export function EvaluationWorkspace({ assignmentId, section }: { assignmentId: number; section: 'group' | 'individual' }) {
  const { t, language, date } = useLanguage()
  const [page, setPage] = useState<EvaluationPage | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmSubmit, setConfirmSubmit] = useState(false)

  useEffect(() => {
    getEvaluation(assignmentId, section).then(setPage).catch((error: unknown) => {
      setMessage(error instanceof Error ? error.message : 'Could not load evaluation.')
    })
  }, [assignmentId, section])

  async function choose(pairId: number, choice: number) {
    setBusy(true)
    try {
      const updated = await saveEvaluationDraft(assignmentId, section, [{ pair_id: pairId, choice }])
      setPage(updated)
      setMessage(t('Draft saved.'))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Draft could not be saved.')
    } finally {
      setBusy(false)
    }
  }

  async function submit() {
    setConfirmSubmit(false)
    setBusy(true)
    try {
      const result = await submitEvaluation(assignmentId, section)
      setPage(await getEvaluation(assignmentId, section))
      setMessage(language === 'th' ? 'ส่งแล้ว ' + result.answered + ' จาก ' + result.assigned + ' คู่' : 'Submitted ' + result.answered + ' of ' + result.assigned + ' pairs.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submission failed.')
    } finally {
      setBusy(false)
    }
  }

  return <div className="mt-3 rounded-xl border border-slate-200 p-3 text-sm">
    <h4 className="font-medium capitalize">{t(section === 'group' ? 'Group evaluation' : 'Individual evaluation')}</h4>
    {page && <>
      <p className="text-slate-600">{t('Deadline')}: {page.deadline ? date(page.deadline) : t('Not set')}</p>
      <p className="text-slate-600">{t('Progress')}: {page.pairs.filter((pair) => pair.draft_choice != null).length}/{page.pairs.length} {t('saved')}</p>
      {page.submitted_at && <p className="text-slate-600">{t('Last submitted')}: {date(page.submitted_at)}</p>}
      {page.pairs.length === 0 && <p className="text-slate-500">{t('No pairs assigned for this section.')}</p>}
      <div className="mt-3 space-y-3">
        {page.pairs.map((pair) => <fieldset key={pair.id} className="rounded-lg border p-3" disabled={!page.is_open || busy}>
          <legend className="font-medium">{pair.criterion}: {pair.left} / {pair.right}</legend>
          <div className="flex flex-wrap gap-3">
            {choices.map((label, index) => <label key={label} className="inline-flex items-center gap-1">
              <input type="radio" name={`pair-${pair.id}`} checked={pair.draft_choice === index + 1}
              onChange={() => void choose(pair.id, index + 1)} />{t(label)}
            </label>)}
          </div>
          {pair.submitted_choice != null && <p className="text-slate-500">{t('Last submitted')}: {t(choices[pair.submitted_choice - 1])}</p>}
        </fieldset>)}
      </div>
      {page.is_open && page.pairs.length > 0 && <button type="button" disabled={busy || !page.pairs.some((pair) => pair.draft_choice != null)}
        onClick={() => setConfirmSubmit(true)} className="mt-3 rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">{t('Submit saved answers')}</button>}
      {confirmSubmit && <div className="confirm-panel" role="group" aria-label={t('Submit saved answers')}>
        <p>{t('Submit all currently saved answers for this section?')}</p>
        <div><button type="button" disabled={busy} onClick={() => void submit()}>{language === 'th' ? 'ยืนยันการส่ง' : 'Confirm submission'}</button><button type="button" disabled={busy} onClick={() => setConfirmSubmit(false)}>{language === 'th' ? 'ยกเลิก' : 'Cancel'}</button></div>
      </div>}
    </>}
    {message && <p role="status" className="mt-2">{message}</p>}
  </div>
}
