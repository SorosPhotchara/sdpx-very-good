import { useEffect, useRef, useState } from 'react'
import { createClassroom, getClassrooms, getHealth, getMe, importRoster, inviteInstructor, removeInstructor, setCredential, type Classroom, type CurrentUser } from './api'
import { GoogleSignIn } from './GoogleSignIn'
import { AssignmentWorkspace } from './AssignmentWorkspace'
import { GroupReassignment } from './GroupReassignment'
import { AddStudent } from './AddStudent'
import { useLanguage } from './i18n'

const demo = import.meta.env.VITE_AUTH_MODE === 'mock'
const sessionKey = 'paireval-credential'

function tokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(window.atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: unknown }
    return typeof payload.exp === 'number' && Number.isFinite(payload.exp) ? payload.exp * 1000 : null
  } catch { return null }
}

function savedCredential(): string | null {
  const token = window.sessionStorage.getItem(sessionKey)
  if (token && (demo ? token.startsWith('mock:') : (tokenExpiry(token) ?? 0) > Date.now() + 30_000)) return token
  window.sessionStorage.removeItem(sessionKey)
  return null
}

export default function App() {
  const { language, setLanguage, t } = useLanguage()
  const sessionTimer = useRef<number | null>(null)
  const restoreStarted = useRef(false)
  const [restoring, setRestoring] = useState(true)
  const [health, setHealth] = useState('loading')
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [newClassroom, setNewClassroom] = useState('')
  const [error, setError] = useState('')
  const [rosterStatus, setRosterStatus] = useState<Record<number, string>>({})
  const [instructorInput, setInstructorInput] = useState('')
  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    getHealth().then((data) => setHealth(data.status)).catch(() => setHealth('offline'))
    if (!restoreStarted.current) {
      restoreStarted.current = true
      const token = savedCredential()
      if (token) void handleSignIn(token).finally(() => setRestoring(false))
      else setRestoring(false)
    }
    return () => { if (sessionTimer.current != null) window.clearTimeout(sessionTimer.current) }
  }, [])

  function signOut(message = '') {
    if (sessionTimer.current != null) window.clearTimeout(sessionTimer.current)
    sessionTimer.current = null
    setCredential('')
    window.sessionStorage.removeItem(sessionKey)
    setCurrentUser(null)
    setClassrooms([])
    setSelectedId(null)
    setError(message)
  }

  function scheduleSessionEnd(token: string) {
    if (sessionTimer.current != null) window.clearTimeout(sessionTimer.current)
    if (demo) return
    const delay = Math.max(0, (tokenExpiry(token) ?? Date.now() + 55 * 60 * 1000) - Date.now() - 30_000)
    sessionTimer.current = window.setTimeout(() => signOut(language === 'th' ? 'เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง' : 'Session expired. Sign in again.'), delay)
  }

  async function handleSignIn(token: string) {
    setCredential(token)
    try {
      const [user, availableClassrooms] = await Promise.all([getMe(), getClassrooms()])
      setCurrentUser(user)
      setClassrooms(availableClassrooms)
      setSelectedId(availableClassrooms.find((item) => item.name === 'PairEval Demo')?.id ?? availableClassrooms[0]?.id ?? null)
      setError('')
      if (demo || (tokenExpiry(token) ?? 0) > Date.now() + 30_000) window.sessionStorage.setItem(sessionKey, token)
      scheduleSessionEnd(token)
    } catch {
      signOut(language === 'th' ? 'เข้าสู่ระบบไม่สำเร็จ กรุณาลองอีกครั้ง' : 'Sign-in could not be verified. Please try again.')
    }
  }

  async function handleCreateClassroom() {
    if (!currentUser?.is_instructor || !newClassroom.trim()) return
    try {
      const classroom = await createClassroom(newClassroom.trim())
      setClassrooms((items) => [...items, classroom])
      setSelectedId(classroom.id)
      setNewClassroom('')
      setError('')
    } catch { setError(language === 'th' ? 'สร้างห้องเรียนไม่สำเร็จ' : 'Could not create the classroom.') }
  }

  async function handleRosterFile(classroomId: number, file: File) {
    try {
      const result = await importRoster(classroomId, await file.text())
      setRosterStatus((items) => ({ ...items, [classroomId]: result.errors.length ? result.errors.join('; ') : language === 'th' ? 'นำเข้านักศึกษา ' + result.imported + ' คนแล้ว' : 'Imported ' + result.imported + ' students.' }))
    } catch { setRosterStatus((items) => ({ ...items, [classroomId]: language === 'th' ? 'นำเข้า CSV ไม่สำเร็จ' : 'Roster import failed.' })) }
  }

  async function changeInstructor(classroomId: number, email: string, remove: boolean) {
    try {
      const updated = remove ? await removeInstructor(classroomId, email) : await inviteInstructor(classroomId, email)
      setClassrooms((items) => items.map((item) => item.id === classroomId ? updated : item))
      setInstructorInput('')
      setError('')
    } catch (problem) { setError(problem instanceof Error ? problem.message : language === 'th' ? 'แก้ไขรายชื่ออาจารย์ไม่สำเร็จ' : 'Could not update instructors.') }
  }

  const selected = classrooms.find((item) => item.id === selectedId)
  const canManage = Boolean(currentUser?.is_instructor && selected?.instructor_emails.split(',').includes(currentUser.email))

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">P<span>●</span></span><span>PairEval<small>{language === 'th' ? 'ระบบประเมินแบบเปรียบเทียบคู่' : 'Pairwise evaluation'}</small></span></div>
      <div className="sidebar-label">{t('Classrooms')} <span>{classrooms.length.toString().padStart(2, '0')}</span></div>
      <nav aria-label={t('Classrooms')} className="classroom-list">
        {classrooms.map((item, index) => <button key={item.id} type="button" className={'classroom-link ' + (selectedId === item.id ? 'active' : '')} onClick={() => { setSelectedId(item.id); setShowSettings(false) }}>
          <span className="classroom-index">{String(index + 1).padStart(2, '0')}</span><span>{item.name}</span><span className="nav-arrow">↗</span>
        </button>)}
        {!currentUser && <p className="sidebar-hint">{language === 'th' ? 'เข้าสู่ระบบเพื่อดูห้องเรียน' : 'Sign in to view classrooms'}</p>}
        {currentUser && classrooms.length === 0 && <p className="sidebar-hint">{language === 'th' ? 'ยังไม่มีห้องเรียน' : 'No classrooms yet'}</p>}
      </nav>
      {currentUser?.is_instructor && <form className="create-classroom" onSubmit={(event) => { event.preventDefault(); void handleCreateClassroom() }}>
        <label htmlFor="new-classroom">{language === 'th' ? 'เพิ่มห้องเรียน' : 'Add classroom'}</label>
        <div><input id="new-classroom" value={newClassroom} onChange={(event) => setNewClassroom(event.target.value)} placeholder={language === 'th' ? 'ชื่อห้องเรียน' : 'Classroom name'} /><button type="submit" aria-label={language === 'th' ? 'สร้างห้องเรียน' : 'Create classroom'}>＋</button></div>
      </form>}
      <div className="sidebar-bottom"><span className={'status-dot ' + (health === 'ok' ? 'online' : '')} />{language === 'th' ? 'สถานะระบบ' : 'System status'}: {health}</div>
    </aside>

    <div className="content-shell">
      <header className="topbar"><div className="topbar-crumb">PAIR<span> / </span>{selected?.name || (language === 'th' ? 'ภาพรวม' : 'Overview')}</div><div className="topbar-actions">
        <div className="language-switch" role="group" aria-label="Language"><button type="button" className={language === 'th' ? 'selected' : ''} onClick={() => setLanguage('th')}>TH</button><button type="button" className={language === 'en' ? 'selected' : ''} onClick={() => setLanguage('en')}>EN</button></div>
        {currentUser && <button type="button" className="signout" onClick={() => signOut()}>{language === 'th' ? 'ออกจากระบบ' : 'Sign out'} ↗</button>}
      </div></header>

      <main className="main-content">
        {error && <p role="status" className="notice error">{error}</p>}
        {restoring ? <p role="status">{language === 'th' ? 'กำลังกู้คืนการเข้าสู่ระบบ...' : 'Restoring sign-in...'}</p> : !currentUser ? <section className="welcome-layout">
          <div className="welcome-copy"><span className="eyebrow">THE PAIRWISE REVIEW WORKSPACE</span><h1>{language === 'th' ? <>ประเมินอย่าง<br /><em>เป็นธรรม</em> ด้วย<br />มุมมองที่หลากหลาย</> : <>A fairer view<br />of every <em>contribution.</em></>}</h1><p>{language === 'th' ? 'เปรียบเทียบผลงานเป็นคู่ ติดตามความคืบหน้า และดูคะแนนในพื้นที่เดียว' : 'Compare work in pairs, track progress, and review scores in one place.'}</p></div>
          <div className="login-panel"><div className="panel-number">01 / ACCESS</div><h2>{language === 'th' ? 'เข้าสู่พื้นที่การเรียนรู้' : 'Enter your workspace'}</h2><p>{language === 'th' ? 'เลือกบทบาทเพื่อทดลองระบบด้วยข้อมูลตัวอย่าง' : 'Choose a role to explore the sample workspace.'}</p>
            {demo ? <div className="demo-options"><button type="button" className="demo-option" onClick={() => void handleSignIn('mock:teacher@example.edu')}><span className="role-icon">T</span><span><strong>{language === 'th' ? 'ทดลองเป็นอาจารย์' : 'Explore as instructor'}</strong><small>teacher@example.edu</small></span><span>↗</span></button><button type="button" className="demo-option" onClick={() => void handleSignIn('mock:student1@example.edu')}><span className="role-icon student">S</span><span><strong>{language === 'th' ? 'ทดลองเป็นนักศึกษา' : 'Explore as student'}</strong><small>student1@example.edu</small></span><span>↗</span></button></div> : <GoogleSignIn onSignIn={handleSignIn} />}
            {demo && <p className="demo-note">{language === 'th' ? 'โหมดสาธิต · ข้อมูลอยู่ใน PostgreSQL ภายใน Docker' : 'Demo mode · Data is stored in PostgreSQL inside Docker'}</p>}
          </div>
        </section> : <>
          <div className="page-heading"><div><div className="eyebrow">{language === 'th' ? 'พื้นที่การเรียนรู้' : 'YOUR WORKSPACE'} / {currentUser.is_instructor ? (language === 'th' ? 'อาจารย์' : 'INSTRUCTOR') : (language === 'th' ? 'นักศึกษา' : 'STUDENT')}</div><h1>{selected?.name || t('Classrooms')}</h1><p>{language === 'th' ? 'จัดการงานประเมิน ตอบแบบประเมิน และติดตามคะแนน' : 'Manage assignments, complete evaluations, and track scores.'}</p></div><div className="user-badge"><span>{currentUser.email.slice(0, 1).toUpperCase()}</span><div><strong>{currentUser.is_instructor ? (language === 'th' ? 'อาจารย์' : 'Instructor') : t('Student')}</strong><small>{currentUser.email}</small></div></div></div>
          {selected ? <div className="workspace-grid"><div className="workspace-main"><div className="section-heading"><span className="section-count">01</span><h2>{t('Assignments')}</h2><span className="heading-rule" /></div><AssignmentWorkspace key={selected.id} classroomId={selected.id} isInstructor={canManage} email={currentUser.email} /></div>
            <aside className="workspace-side" data-testid="workspace-side"><div className="info-panel"><span className="panel-number">CLASSROOM / {String(selected.id).padStart(2, '0')}</span><h3>{language === 'th' ? 'รายละเอียดห้องเรียน' : 'Classroom details'}</h3><div className="info-row"><span>{language === 'th' ? 'รหัสห้อง' : 'Class ID'}</span><strong>#{selected.id}</strong></div><div className="info-row"><span>{language === 'th' ? 'อาจารย์' : 'Instructors'}</span><strong>{selected.instructor_emails.split(',').filter(Boolean).length}</strong></div></div>
              {canManage && <div className="side-tools"><button type="button" className="tools-toggle" onClick={() => setShowSettings((value) => !value)} aria-expanded={showSettings}>{language === 'th' ? 'จัดการห้องเรียน' : 'Manage classroom'} <span>{showSettings ? '−' : '＋'}</span></button>{showSettings && <div className="tools-content"><label>{language === 'th' ? 'นำเข้ารายชื่อนักศึกษา (CSV)' : 'Import student roster (CSV)'}<input type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void handleRosterFile(selected.id, file) }} /></label>{rosterStatus[selected.id] && <p role="status">{rosterStatus[selected.id]}</p>}<AddStudent key={selected.id} classroomId={selected.id} /><div className="instructor-list"><strong>{language === 'th' ? 'อาจารย์ในห้อง' : 'Classroom instructors'}</strong>{selected.instructor_emails.split(',').filter(Boolean).map((email) => <div key={email}><span>{email}</span><button type="button" onClick={() => void changeInstructor(selected.id, email, true)}>{t('Remove')}</button></div>)}</div><form onSubmit={(event) => { event.preventDefault(); void changeInstructor(selected.id, instructorInput, false) }}><input type="email" aria-label={language === 'th' ? 'อีเมลอาจารย์' : 'Instructor email'} placeholder={language === 'th' ? 'อีเมลอาจารย์ที่อนุมัติ' : 'Approved instructor email'} value={instructorInput} onChange={(event) => setInstructorInput(event.target.value)} /><button type="submit">{language === 'th' ? 'เชิญ' : 'Invite'}</button></form><GroupReassignment classroomId={selected.id} isInstructor /></div>}</div>}
              {!canManage && <GroupReassignment classroomId={selected.id} isInstructor={false} />}
              <div className="side-quote"><span>“</span><p>{language === 'th' ? 'ทุกความคิดเห็นช่วยให้เห็นภาพที่ครบขึ้น' : 'Every perspective makes the picture clearer.'}</p><small>PAIREVAL / 2026</small></div>
            </aside></div> : <div className="empty-state">{language === 'th' ? 'เลือกห้องเรียนจากแถบด้านซ้าย' : 'Select a classroom from the sidebar.'}</div>}
        </>}
      </main>
      <footer className="app-footer"><span>PAIR / EVAL © {new Date().getFullYear()}</span><span>{language === 'th' ? 'การประเมินที่เห็นทุกมุมมอง' : 'A clearer view of every contribution'}</span></footer>
    </div>
  </div>
}
