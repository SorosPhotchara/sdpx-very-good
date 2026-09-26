import { useState } from 'react'
import { getEvaluation, submitEvaluation, type EvaluationPage } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { Button } from './components/ui/button'
import { Alert, AlertDescription } from './components/ui/alert'
import { useEvaluationDraft } from './useEvaluationDraft'
import { ToastNotice, useNotice } from './components/ui/toast'

const choices = ['Strongly left', 'Slightly left', 'Equal', 'Slightly right', 'Strongly right']

export function EvaluationWorkspace({ assignmentId, section }: { assignmentId: number; section: 'group' | 'individual' }) {
  const { t, language, date } = useLanguage()
  const [opened, setOpened] = useState(section === 'group')
  const [activated, setActivated] = useState(section === 'group')
  const resource = useResource<EvaluationPage>(`${assignmentId}:${section}`, () => getEvaluation(assignmentId, section), activated)
  const page = resource.data
  const setPage = resource.setData
  const [message, setMessage] = useNotice()
  const action = useAsyncLock()
  const busy = action.busy
  const [confirmSubmit, setConfirmSubmit] = useState(false)
  const draft = useEvaluationDraft(assignmentId, section, setPage,
    () => setMessage(t('Draft saved.')), error => setMessage(error, 'error'))
  const saveLabel = draft.saving ? (language === 'th' ? 'กำลังบันทึก...' : 'Saving...')
    : draft.failed ? (language === 'th' ? 'ยังบันทึกไม่ครบ' : 'Unsaved changes') : t('saved')

  async function submit() {
    if (draft.saving || draft.failed || !action.begin()) return
    setConfirmSubmit(false)
    try {
      const result = await submitEvaluation(assignmentId, section)
      await resource.refresh()
      setMessage(language === 'th' ? 'ส่งแล้ว ' + result.answered + ' จาก ' + result.assigned + ' คู่' : 'Submitted ' + result.answered + ' of ' + result.assigned + ' pairs.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submission failed.', 'error')
    } finally {
      action.finish()
    }
  }

  return <details open={opened} onToggle={(event) => { setOpened(event.currentTarget.open); if (event.currentTarget.open) setActivated(true) }} className="evaluation-section mt-3 rounded-xl border border-slate-200 text-sm">
    <summary className="evaluation-section-summary">{t(section === 'group' ? 'Group evaluation' : 'Individual evaluation')}<span>{page ? `${page.pairs.filter((pair) => pair.draft_choice != null).length}/${page.pairs.length} ${saveLabel}` : ''}</span></summary>
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
      <p className="text-slate-600">{t('Progress')}: {page.pairs.filter((pair) => pair.draft_choice != null).length}/{page.pairs.length} {saveLabel}</p>
      {draft.failed && <div role="alert" className="mt-2">{language === 'th' ? 'คำตอบที่เลือกยังบันทึกไม่สำเร็จ กรุณาลองอีกครั้งก่อนส่ง' : 'Your choices have not been saved. Retry before submitting.'} <Button type="button" variant="outline" onClick={draft.retry}>{t('Retry')}</Button></div>}
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
              onChange={() => draft.choose(pair.id, index + 1)} /><span>{t(label)}</span>
            </label>)}
          </div>
          {pair.submitted_choice != null && <p className="submitted-choice">{t('Last submitted')}: {t(choices[pair.submitted_choice - 1])}</p>}
        </fieldset>)}
      </div>
      {page.is_open && page.pairs.length > 0 && <button type="button" disabled={busy || draft.saving || draft.failed || !page.pairs.some((pair) => pair.draft_choice != null)}
        onClick={() => setConfirmSubmit(true)} className="mt-3 rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">{t('Submit saved answers')}</button>}
      {confirmSubmit && <Alert className="mt-3" role="group" aria-label={t('Submit saved answers')}>
        <AlertDescription>{t('Submit all currently saved answers for this section?')}</AlertDescription>
        <div className="mt-4 flex flex-wrap gap-3"><Button type="button" disabled={busy || draft.saving || draft.failed} onClick={() => void submit()}>{language === 'th' ? 'ยืนยันการส่ง' : 'Confirm submission'}</Button><Button type="button" variant="outline" disabled={busy} onClick={() => setConfirmSubmit(false)}>{language === 'th' ? 'ยกเลิก' : 'Cancel'}</Button></div>
      </Alert>}
    </>}
    <ToastNotice notice={message} />
    </div>
  </details>
}
