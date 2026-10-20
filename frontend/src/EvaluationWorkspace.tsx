import { useRef, useState } from 'react'
import { getEvaluation, submitEvaluation, type EvaluationPage, type EvaluationPair } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'
import { Button } from './components/ui/button'
import { Alert, AlertDescription } from './components/ui/alert'
import { useEvaluationDraft } from './useEvaluationDraft'
import { formatCountdown, useCountdown } from './useCountdown'
import { ToastNotice, useNotice } from './components/ui/toast'
import { DisclosureSummary } from './components/ui/disclosure-summary'
import { choices } from './choices'

const sections = ['group', 'individual'] as const
const sectionTitle = (section: 'group' | 'individual') => section === 'group' ? 'Group evaluation' : 'Individual evaluation'

// The PRD keeps Group and Individual evaluation on separate pages, so only the chosen
// one is mounted. The surrounding disclosure stays per assignment to preserve lazy loading.
export function StudentEvaluationPages({ assignmentId, initiallyOpen = false }: { assignmentId: number; initiallyOpen?: boolean }) {
  const { t, language } = useLanguage()
  const [opened, setOpened] = useState(initiallyOpen)
  const [activated, setActivated] = useState(initiallyOpen)
  const [section, setSection] = useState<'group' | 'individual'>('group')

  return <details open={opened} onToggle={(event) => { setOpened(event.currentTarget.open); if (event.currentTarget.open) setActivated(true) }} className="evaluation-section mt-3 rounded-xl border border-slate-200 text-sm">
    <DisclosureSummary className="evaluation-section-summary">{language === 'th' ? 'ประเมินผล' : 'Evaluation'}<span>{t(sectionTitle(section))}</span></DisclosureSummary>
    <div className="evaluation-section-content">
      <nav className="evaluation-page-nav" data-testid="evaluation-page-nav" role="group" aria-label={language === 'th' ? 'เลือกหน้าประเมิน' : 'Choose evaluation page'}>
        {sections.map((value) => <Button key={value} type="button" size="sm" variant={section === value ? 'default' : 'outline'}
          aria-pressed={section === value} data-testid={`evaluation-page-${value}`} onClick={() => setSection(value)}>{t(sectionTitle(value))}</Button>)}
      </nav>
      {activated && <EvaluationWorkspace key={section} assignmentId={assignmentId} section={section} />}
    </div>
  </details>
}

export function EvaluationWorkspace({ assignmentId, section }: { assignmentId: number; section: 'group' | 'individual' }) {
  const { t, language, date } = useLanguage()
  const resource = useResource<EvaluationPage>(`${assignmentId}:${section}`, () => getEvaluation(assignmentId, section), true)
  const page = resource.data
  const [selectedCriterion, setSelectedCriterion] = useState<string | null>(null)
  const criterionNavigator = useRef<HTMLDivElement>(null)
  const criterionGroups = Array.from((page?.pairs ?? []).reduce((groups, pair) => {
    const items = groups.get(pair.criterion) ?? []
    items.push(pair)
    groups.set(pair.criterion, items)
    return groups
  }, new Map<string, EvaluationPair[]>()))
  const firstUnansweredCriterion = criterionGroups.find(([, pairs]) => pairs.some((pair) => pair.draft_choice == null))?.[0]
  const activeCriterionIndex = criterionGroups.findIndex(([name]) => name === selectedCriterion)
  const visibleCriterionIndex = activeCriterionIndex >= 0 ? activeCriterionIndex
    : criterionGroups.findIndex(([name]) => name === firstUnansweredCriterion)
  const activeCriterionPairs = criterionGroups[visibleCriterionIndex >= 0 ? visibleCriterionIndex : 0]?.[1] ?? []
  const currentRound = visibleCriterionIndex >= 0 ? visibleCriterionIndex : 0

  function goToCriterion(index: number) {
    setSelectedCriterion(criterionGroups[index][0])
    criterionNavigator.current?.scrollIntoView({ block: 'start' })
  }
  const remaining = useCountdown(page?.deadline ?? null)
  // Participation credit counts submitted pairs, so the warning and the bars both track submissions.
  const unanswered = (page?.pairs ?? []).filter((pair) => pair.draft_choice == null).length
  const setPage = resource.setData
  const [message, setMessage] = useNotice()
  const action = useAsyncLock()
  const busy = action.busy
  const [confirmSubmit, setConfirmSubmit] = useState(false)
  const draft = useEvaluationDraft(assignmentId, section, setPage,
    () => setMessage(section === 'group' ? t('Draft saved.') : ''), error => setMessage(error, 'error'))
  const saveLabel = draft.saving ? (language === 'th' ? 'กำลังบันทึก...' : 'Saving...')
    : draft.failed ? (language === 'th' ? 'ยังบันทึกไม่ครบ' : 'Unsaved changes') : t('saved')

  async function saveDraft() {
    if (draft.saving || !action.begin()) return
    try {
      if (await draft.save()) setMessage(t('Draft saved.'))
    } finally {
      action.finish()
    }
  }

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

  return <section className="evaluation-page">
    <h3 className="sr-only">{t(sectionTitle(section))}</h3>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดแบบประเมิน...' : 'Loading evaluation...'}</p>}
    {resource.error && <div role="alert">{resource.error} <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button></div>}
    {section === 'individual' && <p className="evaluation-context">{page
      ? language === 'th'
        ? `กลุ่มของคุณ: ${page.group_name || 'ยังไม่ระบุกลุ่ม'} · เปรียบเทียบเพื่อนร่วมกลุ่มตามเกณฑ์`
        : `Your group: ${page.group_name || 'Not assigned'} · Compare teammates by criterion.`
      : language === 'th' ? 'กำลังโหลดข้อมูลกลุ่มของคุณ…' : 'Loading your group…'}</p>}
    {page && <>
      {page.is_open && page.pairs.length > 0 && <p className="evaluation-help">{language === 'th'
        ? 'เลือกคำตอบ ระบบบันทึกอัตโนมัติ หรือกด “บันทึกร่าง” ได้ตลอด แล้วกด “ส่งคำตอบที่บันทึก” เมื่อพร้อม'
        : 'Choose an answer. Your choice saves automatically, or select “Save draft” at any time. Select “Submit saved answers” when ready.'}</p>}
      <p className="text-slate-600">{t('Deadline')}: {page.deadline ? date(page.deadline) : t('Not set')}</p>
      {remaining != null && <p className="evaluation-countdown" data-testid="evaluation-countdown" role="timer" aria-live="off">
        {remaining > 0
          ? (language === 'th' ? `เหลือเวลา ${formatCountdown(remaining, 'th')}` : `${formatCountdown(remaining, 'en')} left`)
          : t('Deadline has passed.')}
      </p>}
      <p className="text-slate-600">{t('Progress')}: {page.pairs.filter((pair) => pair.draft_choice != null).length}/{page.pairs.length} {saveLabel}</p>
      {criterionGroups.length > 0 && <div className="criterion-progress" data-testid="criterion-progress">
        {criterionGroups.map(([name, pairs]) => {
          const submitted = pairs.filter((pair) => pair.submitted_choice != null).length
          const label = language === 'th' ? `${name}: ส่งแล้ว ${submitted} จาก ${pairs.length} คู่` : `${name}: ${submitted} of ${pairs.length} pairs submitted`
          return <div key={name} className="criterion-progress-row">
            <span className="criterion-progress-name">{name}</span>
            <progress value={submitted} max={pairs.length} aria-label={label} />
            <small>{submitted} / {pairs.length} {language === 'th' ? 'คู่ที่ส่งแล้ว' : 'pairs submitted'}</small>
          </div>
        })}
      </div>}
      {draft.failed && <div role="alert" className="mt-2">{language === 'th' ? 'คำตอบที่เลือกยังบันทึกไม่สำเร็จ กรุณาลองอีกครั้งก่อนส่ง' : 'Your choices have not been saved. Retry before submitting.'} <Button type="button" variant="outline" onClick={draft.retry}>{t('Retry')}</Button></div>}
      {page.submitted_at && <p className="text-slate-600">{t('Last submitted')}: {date(page.submitted_at)}</p>}
      {page.is_open && unanswered > 0 && <p className="evaluation-incomplete" data-testid="unanswered-notice">{language === 'th'
        ? `ยังมี ${unanswered} คู่ที่ยังไม่ได้ประเมิน คู่ที่ไม่ได้ตอบจะไม่ถูกนับ และทำให้ตัวคูณการมีส่วนร่วมของคุณลดลง`
        : `${unanswered} pair${unanswered === 1 ? '' : 's'} still unevaluated. Unanswered pairs are not counted and lower your participation multiplier.`}</p>}
      {page.pairs.length === 0 && <p className="text-slate-500">{t('No pairs assigned for this section.')}</p>}
      {section === 'individual' && activeCriterionPairs.length > 0 && <div ref={criterionNavigator} className="mt-3 border-b border-border pb-3" data-testid="individual-criterion-navigator">
        <div className="flex items-center justify-between gap-3">
          <strong>{language === 'th' ? 'ประเมินตามเกณฑ์' : 'Evaluate by criterion'}</strong>
          <span className="text-xs text-muted-foreground">{language === 'th' ? `รอบ ${currentRound + 1}/${criterionGroups.length}` : `Round ${currentRound + 1}/${criterionGroups.length}`}</span>
        </div>
        <div role="group" aria-label={language === 'th' ? 'เลือกเกณฑ์ประเมิน' : 'Choose evaluation criterion'} className="mt-3 grid gap-2 sm:flex sm:flex-wrap">
          {criterionGroups.map(([name, pairs], index) => <Button key={`${name}:${index}`} type="button" size="sm" variant={currentRound === index ? 'default' : 'outline'} aria-pressed={currentRound === index} className="w-full max-w-full justify-between gap-2 sm:w-auto" onClick={() => goToCriterion(index)}>
            <span className="min-w-0 truncate">{name}</span><span className="shrink-0 text-xs opacity-75">{pairs.filter((pair) => pair.draft_choice != null).length}/{pairs.length}</span>
          </Button>)}
        </div>
      </div>}
      <div className="mt-3 space-y-3">
        {(section === 'individual' ? activeCriterionPairs : page.pairs).map((pair, pairIndex) => <fieldset key={pair.id} className="evaluation-pair" disabled={!page.is_open || busy}>
          <legend className={section === 'individual' ? 'sr-only' : undefined}>{pair.criterion}</legend>
          {section === 'individual' && <div className="mb-3 text-xs font-medium text-muted-foreground">
            {language === 'th' ? `คู่ที่ ${pairIndex + 1}/${activeCriterionPairs.length}` : `Pair ${pairIndex + 1}/${activeCriterionPairs.length}`}
          </div>}
          {/* One row per the PRD mock: left item, the six levels, right item. */}
          <div className="pair-candidates" data-testid="pair-candidates">
            <span className="pair-side">{pair.left}</span>
            <div className="choice-scale">
              {choices.map((label, index) => <label key={label} className="choice-option" title={t(label)}>
                <input type="radio" name={`pair-${pair.id}`} checked={pair.draft_choice === index + 1}
                onChange={() => draft.choose(pair.id, index + 1)} /><span>{t(label)}</span>
              </label>)}
            </div>
            <span className="pair-side pair-side-right">{pair.right}</span>
          </div>
          {pair.submitted_choice != null && <p className="submitted-choice">{t('Last submitted')}: {t(choices[pair.submitted_choice - 1])}</p>}
        </fieldset>)}
      </div>
      {section === 'individual' && criterionGroups.length > 1 && <div className="mt-3 flex items-center justify-between gap-3" role="group" aria-label={language === 'th' ? 'เปลี่ยนเกณฑ์ประเมิน' : 'Navigate evaluation criteria'}>
        <Button type="button" variant="outline" size="sm" disabled={currentRound <= 0} data-testid="previous-individual-criterion" onClick={() => goToCriterion(currentRound - 1)}>{language === 'th' ? 'เกณฑ์ก่อนหน้า' : 'Previous criterion'}</Button>
        <span className="text-xs text-muted-foreground">{currentRound + 1}/{criterionGroups.length}</span>
        <Button type="button" variant="outline" size="sm" disabled={currentRound >= criterionGroups.length - 1} data-testid="next-individual-criterion" onClick={() => goToCriterion(currentRound + 1)}>{language === 'th' ? 'เกณฑ์ถัดไป' : 'Next criterion'}</Button>
      </div>}
      {page.is_open && page.pairs.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button type="button" variant="outline" data-testid="save-draft" disabled={busy || draft.saving}
          onClick={() => void saveDraft()}>{draft.saving ? t('Working...') : t('Save draft')}</Button>
        <button type="button" disabled={busy || draft.saving || draft.failed || !page.pairs.some((pair) => pair.draft_choice != null)}
          onClick={() => setConfirmSubmit(true)} className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">{t('Submit saved answers')}</button>
      </div>}
      {confirmSubmit && <Alert className="mt-3" role="group" aria-label={t('Submit saved answers')}>
        <AlertDescription>{t('Submit all currently saved answers for this section?')}</AlertDescription>
        {unanswered > 0 && <AlertDescription className="mt-2 font-medium" data-testid="unanswered-warning">{language === 'th'
          ? `คำเตือน: ยังมี ${unanswered} จาก ${page.pairs.length} คู่ที่ยังไม่ได้ประเมิน`
          : `Warning: ${unanswered} of ${page.pairs.length} pairs are still unevaluated.`}</AlertDescription>}
        <div className="mt-4 flex flex-wrap gap-3"><Button type="button" disabled={busy || draft.saving || draft.failed} onClick={() => void submit()}>{language === 'th' ? 'ยืนยันการส่ง' : 'Confirm submission'}</Button><Button type="button" variant="outline" disabled={busy} onClick={() => setConfirmSubmit(false)}>{language === 'th' ? 'ยกเลิก' : 'Cancel'}</Button></div>
      </Alert>}
    </>}
    <ToastNotice notice={message} />
  </section>
}
