import { Button } from './components/ui/button'
import { getInstructorApprovals } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'

export function InstructorAdminWorkspace() {
  const { language, t } = useLanguage()
  const resource = useResource('instructor-allowlist', getInstructorApprovals)
  const instructors = resource.data ?? []

  return <section className="instructor-admin" data-testid="instructor-admin">
    <div>
      <p className="eyebrow">{language === 'th' ? 'การเข้าถึงระบบ' : 'SYSTEM ACCESS'}</p>
      <h2>{language === 'th' ? 'รายชื่ออาจารย์ที่ได้รับสิทธิ์' : 'Instructor allowlist'}</h2>
      <p>{language === 'th'
        ? 'รายชื่อนี้กำหนดด้วย INSTRUCTOR_EMAILS ในการตั้งค่าเซิร์ฟเวอร์'
        : 'This list is configured through INSTRUCTOR_EMAILS on the server.'}</p>
    </div>
    {resource.loading && <p role="status">{t('Loading...')}</p>}
    {resource.error && <div role="alert">{resource.error} <Button type="button" variant="outline" onClick={() => void resource.refresh()}>{t('Retry')}</Button></div>}
    {!resource.loading && !resource.error && instructors.length === 0 && <p>{language === 'th' ? 'ยังไม่มีอาจารย์ใน allowlist' : 'No instructors are configured.'}</p>}
    <ul className="instructor-admin-list">
      {instructors.map((instructor) => <li key={instructor.email}><strong>{instructor.email}</strong></li>)}
    </ul>
  </section>
}
