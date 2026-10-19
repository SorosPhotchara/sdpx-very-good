import { useState } from 'react'
import { downloadReportCsv, downloadReportXlsx, getAssignmentReport, getMyScores, getRawPairResponses, type AssignmentReport, type MyScores, type RawPairResponse, type StudentScore } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { ToastNotice, useNotice } from './components/ui/toast'
import { DisclosureSummary } from './components/ui/disclosure-summary'

function ScoreCells({ row }: { row: StudentScore }) {
  const { t } = useLanguage()
  const score = (value: number | null) => value == null ? t('No data') : value.toFixed(2)
  return <><td className="p-2">{score(row.group_work_score)}</td><td className="p-2">{score(row.individual_work_score)}</td><td className="p-2">{score(row.group_participation_score)}</td><td className="p-2">{score(row.individual_participation_score)}</td></>
}

const choiceValues = ['1/0', '.75/.25', '.5/.5', '.25/.75', '0/1']

function RawPairReport({ assignmentId, coverage }: { assignmentId: number; coverage: AssignmentReport['coverage'] }) {
  const { t, language } = useLanguage()
  const [opened, setOpened] = useState(false)
  const [visibleCount, setVisibleCount] = useState(100)
  const resource = useResource<RawPairResponse[]>(`${assignmentId}:raw-pairs`, () => getRawPairResponses(assignmentId), opened)
  const rows = resource.data ?? []
  return <details className="mt-2" onToggle={(event) => { if (event.currentTarget.open) setOpened(true) }}>
    <DisclosureSummary>{language === 'th' ? 'ความครอบคลุมและคำตอบรายคู่' : 'Pair coverage and raw responses'}</DisclosureSummary>
    <div className="report-details-scroll mt-2 max-h-72 overflow-auto" role="region" aria-label={language === 'th' ? 'ความครอบคลุมรายคู่' : 'Pair coverage'} tabIndex={0}>
      <table className="w-full text-left"><thead><tr><th>{t('Section')}</th><th>{t('Criterion')}</th><th>{language === 'th' ? 'รายการซ้าย' : 'Left'}</th><th>{language === 'th' ? 'รายการขวา' : 'Right'}</th><th>{language === 'th' ? 'ผู้มีสิทธิ์' : 'Eligible'}</th><th>{language === 'th' ? 'เป้าหมาย' : 'Target'}</th><th>{language === 'th' ? 'มอบหมายแล้ว' : 'Assigned'}</th><th>{language === 'th' ? 'ส่งแล้ว' : 'Submitted'}</th><th>{language === 'th' ? 'โหวตอาจารย์' : 'Instructor votes'}</th><th>{language === 'th' ? 'โหวตถ่วงน้ำหนัก' : 'Effective votes'}</th><th>{language === 'th' ? 'แต้มซ้าย' : 'Left points'}</th><th>{language === 'th' ? 'แต้มขวา' : 'Right points'}</th><th>{language === 'th' ? 'ขาดจากเป้าหมาย' : 'Missing to target'}</th><th>{language === 'th' ? 'ขาดผู้มีสิทธิ์ให้ครบ 5' : 'Eligible shortage to five'}</th></tr></thead>
        <tbody>{coverage.map((item) => <tr key={`${item.criterion_id}:${item.left_id}:${item.right_id}`} className="border-t"><td>{t(item.section === 'group' ? 'Group' : 'Individual')}</td><td>{item.criterion}</td><td>{item.left ?? `#${item.left_id}`}</td><td>{item.right ?? `#${item.right_id}`}</td><td>{item.eligible_evaluators}</td><td>{item.target_evaluations}</td><td>{item.assigned_evaluators}</td><td>{item.votes}</td><td>{item.instructor_votes}</td><td>{item.effective_votes.toFixed(2)}</td><td>{item.left_points.toFixed(2)}</td><td>{item.right_points.toFixed(2)}</td><td>{item.missing_to_target}</td><td>{item.shortage_to_five}</td></tr>)}</tbody>
      </table>
    </div>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดคำตอบรายคู่...' : 'Loading raw pair responses...'}</p>}
    {resource.error && <p role="alert">{resource.error} <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button></p>}
    {resource.data && <><p className="mt-2 font-medium">{language === 'th' ? 'คำตอบรายคู่และผู้ประเมิน' : 'Raw pair responses and evaluators'} ({rows.length}) <button type="button" disabled={resource.loading} className="ml-2 text-blue-700" onClick={() => void resource.refresh()}>{language === 'th' ? 'อัปเดตคำตอบ' : 'Refresh responses'}</button></p>
      {rows.length === 0 ? <p>{t('No data')}</p> : <>
        <div className="report-details-scroll max-h-72 overflow-auto" role="region" aria-label={language === 'th' ? 'คำตอบรายคู่' : 'Raw pair responses'} tabIndex={0}>
          <table className="w-full text-left"><thead><tr><th>{language === 'th' ? 'รหัสคู่' : 'Pair ID'}</th><th>{t('Section')}</th><th>{t('Criterion')}</th><th>{language === 'th' ? 'คู่' : 'Pair'}</th><th>{language === 'th' ? 'ผู้ประเมิน' : 'Evaluator'}</th><th>{language === 'th' ? 'ผล' : 'Choice'}</th><th>{language === 'th' ? 'เวลาส่ง' : 'Submitted at'}</th></tr></thead>
            <tbody>{rows.slice(0, visibleCount).map((row) => <tr key={row.pair_id} className="border-t"><td>{row.pair_id}</td><td>{t(row.section === 'group' ? 'Group' : 'Individual')}</td><td>{row.criterion}</td><td>{row.left} / {row.right}</td><td>{row.evaluator}</td><td>{row.choice == null ? t('No data') : choiceValues[row.choice - 1]}</td><td>{row.submitted_at ? new Date(row.submitted_at).toLocaleString(language === 'th' ? 'th-TH' : 'en-US') : '—'}</td></tr>)}</tbody>
          </table>
        </div>
        {visibleCount < rows.length && <button type="button" className="mt-2 text-blue-700" onClick={() => setVisibleCount((count) => count + 100)}>{language === 'th' ? 'แสดงเพิ่มอีก 100 รายการ' : 'Show 100 more'}</button>}
      </>}
    </>}
  </details>
}

export function ScoreWorkspace({ assignmentId, isInstructor }: { assignmentId: number; isInstructor: boolean }) {
  const { t, language } = useLanguage()
  const [opened, setOpened] = useState(false)
  const resource = useResource<AssignmentReport | MyScores>(`${assignmentId}:${isInstructor}`, () => isInstructor ? getAssignmentReport(assignmentId) : getMyScores(assignmentId), opened)
  const report = isInstructor ? resource.data as AssignmentReport | null : null
  const mine = !isInstructor ? resource.data as MyScores | null : null
  // Students and instructors read the same interim/final state, so both views carry the label.
  const finality = report ?? mine
  const [error, setError] = useNotice()

  return <details onToggle={(event) => { if (event.currentTarget.open) setOpened(true) }} className="mt-3 rounded-xl border p-3 text-sm">
    <DisclosureSummary className="font-medium">{t('Scores and coverage')}</DisclosureSummary>
    <button type="button" disabled={resource.loading} onClick={() => { setError(''); void resource.refresh() }} className="my-2 text-blue-700">{t('Refresh scores')}</button>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดคะแนน...' : 'Loading scores...'}</p>}
    {resource.error && <p role="alert">{resource.error}</p>}
    <ToastNotice notice={error} />
    {(mine || report) && <div className="score-table-scroll overflow-x-auto" role="region" aria-label={t('Scores and coverage')} tabIndex={0}><table className="w-full text-left">
      <thead><tr><th className="p-2">{t('Student')}</th><th className="p-2">{t('Group work')}</th><th className="p-2">{t('Individual work')}</th><th className="p-2">{t('Group participation')}</th><th className="p-2">{t('Individual participation')}</th></tr></thead>
      <tbody>{(report?.students ?? (mine ? [mine] : [])).map((row) => <tr key={row.student_id} className="border-t"><td className="p-2">{row.email}</td><ScoreCells row={row} /></tr>)}</tbody>
    </table></div>}
    {finality && <p className="mt-2 text-slate-500" data-testid="score-finality">{t('Group')}: {t(finality.group_final ? 'Final' : 'Interim — may change')} · {t('Individual')}: {t(finality.individual_final ? 'Final' : 'Interim — may change')}</p>}
    {report && <div className="mt-2 flex flex-wrap gap-3">{(['groups', 'students', 'pairs'] as const).map((sheet) =>
      <button key={sheet} type="button" className="text-blue-700" onClick={() => void downloadReportCsv(assignmentId, sheet).catch(() => setError(t('Export failed.'), 'error'))}>{language === 'th' ? 'ส่งออก' : 'Export'} {t(sheet)} CSV</button>
    )}<button type="button" className="text-blue-700" onClick={() => void downloadReportXlsx(assignmentId).catch(() => setError(t('Export failed.'), 'error'))}>{language === 'th' ? 'ส่งออก Excel' : 'Export Excel'}</button></div>}
    {report && <p className="mt-2">{language === 'th' ? 'คู่ที่ยังขาดคำตอบจากเป้าหมายที่ทำได้' : 'Pairs missing submitted votes to feasible target'}: {report.coverage.filter((pair) => pair.missing_to_target > 0).length}/{report.coverage.length}. {language === 'th' ? 'คู่ที่มีผู้ประเมินเข้าเกณฑ์ไม่ครบ 5 คน' : 'Pairs with fewer than five eligible evaluators'}: {report.coverage.filter((pair) => pair.shortage_to_five > 0).length}/{report.coverage.length}.</p>}
    {report && <details className="mt-2"><DisclosureSummary>{t('Criterion details and effective votes')}</DisclosureSummary>
      <div className="report-details-scroll max-h-72 overflow-auto" role="region" aria-label={t('Criterion details and effective votes')} tabIndex={0}><table className="w-full text-left"><thead><tr><th>{t('Section')}</th><th>{t('Criterion')}</th><th>{t('Item ID')}</th><th>{t('Weighted score')}</th><th>{t('Effective votes')}</th></tr></thead>
        <tbody>{report.criterion_scores.map((item) => <tr key={item.criterion_id + '-' + item.item_id} className="border-t"><td>{t(item.section === 'group' ? 'Group' : 'Individual')}</td><td>{item.criterion}</td><td>{item.item_id}</td><td>{item.weighted_score == null ? t('No data') : item.weighted_score.toFixed(2)}</td><td>{item.effective_votes}</td></tr>)}</tbody></table></div>
    </details>}
    {report && <RawPairReport assignmentId={assignmentId} coverage={report.coverage} />}
  </details>
}
