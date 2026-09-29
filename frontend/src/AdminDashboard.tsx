import { getAdminOverview } from './api'
import { useLanguage } from './i18n'
import { InstructorAdminWorkspace } from './InstructorAdminWorkspace'
import { useResource } from './useResource'

export function AdminDashboard({ health, classroomRevision = '' }: { health: string; classroomRevision?: string }) {
  const { language, t } = useLanguage()
  const resource = useResource(`admin-overview:${classroomRevision}`, getAdminOverview)
  const overview = resource.data
  const error = resource.error

  return <section className="admin-dashboard">
    <div className="admin-dashboard-heading">
      <div><p className="eyebrow">{language === 'th' ? 'ภาพรวมผู้ดูแลระบบ' : 'ADMINISTRATION'}</p>
        <h2>{language === 'th' ? 'สถานะระบบและห้องเรียน' : 'System and classroom overview'}</h2>
        <p>{language === 'th' ? 'ตรวจดูภาพรวมบัญชีและการใช้งานห้องเรียน พร้อมจัดการสิทธิ์อาจารย์' : 'Review account and classroom activity, and manage instructor access.'}</p></div>
      <span className={'admin-health ' + (health === 'ok' ? 'online' : 'offline')}><i />{language === 'th' ? `สถานะ API: ${health}` : `API status: ${health}`}</span>
    </div>
    {error && <p role="status" className="notice error">{error}</p>}
    {resource.loading && <p role="status">{t('Loading...')}</p>}
    {error && <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button>}
    <div className="admin-metrics">
      <article><small>{language === 'th' ? 'ห้องเรียน' : 'Classrooms'}</small><strong>{overview?.classroom_count ?? '—'}</strong></article>
      <article><small>{language === 'th' ? 'บัญชีนักศึกษา' : 'Student accounts'}</small><strong>{overview?.student_count ?? '—'}</strong></article>
      <article><small>{language === 'th' ? 'อาจารย์ที่อนุมัติ' : 'Approved instructors'}</small><strong>{overview?.instructor_count ?? '—'}</strong></article>
    </div>
    <section className="admin-classrooms"><h3>{language === 'th' ? 'การใช้งานห้องเรียน' : 'Classroom activity'}</h3>
      {overview && overview.classrooms.length === 0 && <p>{language === 'th' ? 'ยังไม่มีห้องเรียน' : 'No classrooms yet.'}</p>}
      {overview?.classrooms.map((room) => <article key={room.id}>
        <div><strong>{room.name}</strong><small>#{room.id} · {room.instructors.join(', ') || (language === 'th' ? 'ยังไม่มีอาจารย์' : 'No instructors')}</small></div>
        <div className="admin-classroom-counts"><span>{room.student_count} {t('students')}</span><span>{room.assignment_count} {language === 'th' ? 'งานประเมิน' : 'assignments'}</span></div>
      </article>)}
    </section>
    <InstructorAdminWorkspace />
  </section>
}
