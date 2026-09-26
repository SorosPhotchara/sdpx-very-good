import { useState } from 'react'
import { getEvaluation, saveEvaluationDraft, submitEvaluation, type EvaluationPage } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'

const choices = ['Strongly left', 'Slightly left', 'Equal', 'Slightly right', 'Strongly right']

export function EvaluationWorkspace({ assignmentId, section }: { assignmentId: number; section: 'group' | 'individual' }) {
  const { t, language, date } = useLanguage()
  const [opened, setOpened] = useState(section === 'group')
  const [activated, setActivated] = useState(section === 'group')
  const resource = useResource<EvaluationPage>(`${assignmentId}:${section}`, () => getEvaluation(assignmentId, section), activated)
  const page = resource.data
  const setPage = resource.setData
  const [message, setMessage] = useState('')
  const action = useAsyncLock()
  const busy = action.busy
  const [confirmSubmit, setConfirmSubmit] = useState(false)

  async function choose(pairId: number, choice: number) {
    if (!page || !action.begin()) return
    const previous = page
    setPage({ ...page, pairs: page.pairs.map((pair) => pair.id === pairId ? { ...pair, draft_choice: choice } : pair) })
    try {
      const updated = await saveEvaluationDraft(assignmentId, section, [{ pair_id: pairId, choice }])
      setPage(updated)
      setMessage(t('Draft saved.'))
    } catch (error) {
      setPage(previous)
      setMessage(error instanceof Error ? error.message : 'Draft could not be saved.')
    } finally {
      action.finish()
    }
  }

  async function submit() {
    if (!action.begin()) return
    setConfirmSubmit(false)
    try {
      const result = await submitEvaluation(assignmentId, section)
      await resource.refresh()
      setMessage(language === 'th' ? 'ส่งแล้ว ' + result.answered + ' จาก ' + result.assigned + ' คู่' : 'Submitted ' + result.answered + ' of ' + result.assigned + ' pairs.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submission failed.')
    } finally {
      action.finish()
    }
  }

  return <details open={opened} onToggle={(event) => { setOpened(event.currentTarget.open); if (event.currentTarget.open) setActivated(true) }} className="evaluation-section mt-3 rounded-xl border border-slate-200 text-sm">
    <summary className="evaluation-section-summary">{t(section === 'group' ? 'Group evaluation' : 'Individual evaluation')}<span>{page ? `${page.pairs.filter((pair) => pair.draft_choice != null).length}/${page.pairs.length} ${t('saved')}` : ''}</span></summary>
    <div className="evaluation-section-content">
    <h3 className="sr-only">{t(section === 'group' ? 'Group evaluation' : 'Individual evaluation')}</h3>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดแบบประเมิน...' : 'Loading evaluation...'}</p>}
    {resource.error && <div role="alert">{resource.error} <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button></div>}
    {section === 'individual' && <p className="evaluation-context">{page
      ? language === 'th'
        ? `กลุ่มของคุณ: ${page.group_name || 'ยังไม่ระบุกลุ่ม'} · ประเมินเฉพาะสมาชิกในกลุ่มนี้ ไม่ประเมินข้ามกลุ่ม คู่เดิมอาจแสดงซ้ำในกลุ่มขนาดเล็กเพราะระบบตั้งเป้า 5 ผลประเมินต่อคู่และเกณฑ์`
        : `Your group: ${page.group_name || 'Not assigned'} · Evaluate members of this group only, not across groups. Pairs may repeat in smaller groups to reach five evaluations per pair and criterion.`
      : language === 'th' ? 'กำลังโหลดข้อมูลกลุ่มของคุณ…' : 'Loading your group…'}</p>}
    {page && <>
      {page.is_open && page.pairs.length > 0 && <p className="evaluation-help">{language === 'th'
        ? 'เลือกคำตอบในแต่ละคู่ ระบบบันทึกให้อัตโนมัติ เมื่อพร้อมแล้วกด “ส่งคำตอบที่บันทึกแล้ว” เพื่อยืนยันการส่ง'
        : 'Choose an answer for each pair. Your choices save automatically. When ready, select “Submit saved answers” to confirm your submission.'}</p>}
      <p className="text-slate-600">{t('Deadline')}: {page.deadline ? date(page.deadline) : t('Not set')}</p>
      <p className="text-slate-600">{t('Progress')}: {page.pairs.filter((pair) => pair.draft_choice != null).length}/{page.pairs.length} {t('saved')}</p>
      {page.submitted_at && <p className="text-slate-600">{t('Last submitted')}: {date(page.submitted_at)}</p>}
      {page.pairs.length === 0 && <p className="text-slate-500">{t('No pairs assigned for this section.')}</p>}
      <div className="mt-3 space-y-3">
        {page.pairs.map((pair) => <fieldset key={pair.id} className="evaluation-pair" disabled={!page.is_open || busy}>
          <legend>{pair.criterion}</legend>
          <div className="pair-candidates" data-testid="pair-candidates">
            <span>{pair.left}</span><span className="pair-versus" aria-hidden="true">VS</span><span>{pair.right}</span>
          </div>
          <div className="choice-scale">
            {choices.map((label, index) => <label key={label} className="choice-option">
              <input type="radio" name={`pair-${pair.id}`} checked={pair.draft_choice === index + 1}
              onChange={() => void choose(pair.id, index + 1)} /><span>{t(label)}</span>
            </label>)}
          </div>
          {pair.submitted_choice != null && <p className="submitted-choice">{t('Last submitted')}: {t(choices[pair.submitted_choice - 1])}</p>}
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
  </details>
}
