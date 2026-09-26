import { useState } from 'react'
import { downloadReportCsv, downloadReportXlsx, getAssignmentReport, getMyScores, type AssignmentReport, type StudentScore } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'

function ScoreCells({ row }: { row: StudentScore }) {
  const { t } = useLanguage()
  const score = (value: number | null) => value == null ? t('No data') : value.toFixed(2)
  return <><td className="p-2">{score(row.group_work_score)}</td><td className="p-2">{score(row.individual_work_score)}</td><td className="p-2">{score(row.group_participation_score)}</td><td className="p-2">{score(row.individual_participation_score)}</td></>
}

export function ScoreWorkspace({ assignmentId, isInstructor }: { assignmentId: number; isInstructor: boolean }) {
  const { t, language } = useLanguage()
  const [opened, setOpened] = useState(false)
  const resource = useResource<AssignmentReport | StudentScore>(`${assignmentId}:${isInstructor}`, () => isInstructor ? getAssignmentReport(assignmentId) : getMyScores(assignmentId), opened)
  const report = isInstructor ? resource.data as AssignmentReport | null : null
  const mine = !isInstructor ? resource.data as StudentScore | null : null
  const [error, setError] = useState('')

  return <details onToggle={(event) => { if (event.currentTarget.open) setOpened(true) }} className="mt-3 rounded-xl border p-3 text-sm">
    <summary className="cursor-pointer font-medium">{t('Scores and coverage')}</summary>
    <button type="button" disabled={resource.loading} onClick={() => { setError(''); void resource.refresh() }} className="my-2 text-blue-700">{t('Refresh scores')}</button>
    {resource.loading && <p role="status">{language === 'th' ? 'กำลังโหลดคะแนน...' : 'Loading scores...'}</p>}
    {resource.error && <p role="alert">{resource.error}</p>}
    {error && <p role="status">{error}</p>}
    {(mine || report) && <div className="overflow-x-auto"><table className="w-full text-left">
      <thead><tr><th className="p-2">{t('Student')}</th><th className="p-2">{t('Group work')}</th><th className="p-2">{t('Individual work')}</th><th className="p-2">{t('Group participation')}</th><th className="p-2">{t('Individual participation')}</th></tr></thead>
      <tbody>{(report?.students ?? (mine ? [mine] : [])).map((row) => <tr key={row.student_id} className="border-t"><td className="p-2">{row.email}</td><ScoreCells row={row} /></tr>)}</tbody>
    </table></div>}
    {report && <p className="mt-2 text-slate-500">{t('Group')}: {t(report.group_final ? 'Final' : 'Interim — may change')} · {t('Individual')}: {t(report.individual_final ? 'Final' : 'Interim — may change')}</p>}
    {report && <div className="mt-2 flex flex-wrap gap-3">{(['groups', 'students', 'pairs'] as const).map((sheet) =>
      <button key={sheet} type="button" className="text-blue-700" onClick={() => void downloadReportCsv(assignmentId, sheet).catch(() => setError(t('Export failed.')))}>{language === 'th' ? 'ส่งออก' : 'Export'} {t(sheet)} CSV</button>
    )}<button type="button" className="text-blue-700" onClick={() => void downloadReportXlsx(assignmentId).catch(() => setError(t('Export failed.')))}>{language === 'th' ? 'ส่งออก Excel' : 'Export Excel'}</button></div>}
    {report && <p className="mt-2">{t('Pairs missing target coverage')}: {report.coverage.filter((pair) => pair.missing_to_five > 0).length}/{report.coverage.length}</p>}
    {report && <details className="mt-2"><summary className="cursor-pointer">{t('Criterion details and effective votes')}</summary>
      <div className="report-details-scroll max-h-72 overflow-auto"><table className="w-full text-left"><thead><tr><th>{t('Section')}</th><th>{t('Criterion')}</th><th>{t('Item ID')}</th><th>{t('Weighted score')}</th><th>{t('Effective votes')}</th></tr></thead>
        <tbody>{report.criterion_scores.map((item) => <tr key={item.criterion_id + '-' + item.item_id} className="border-t"><td>{t(item.section === 'group' ? 'Group' : 'Individual')}</td><td>{item.criterion}</td><td>{item.item_id}</td><td>{item.weighted_score == null ? t('No data') : item.weighted_score.toFixed(2)}</td><td>{item.effective_votes}</td></tr>)}</tbody></table></div>
    </details>}
  </details>
}
