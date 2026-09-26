import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { createClassroom, deleteClassroom, renameClassroom, getClassrooms, getHealth, getMe, importRoster, inviteInstructor, removeInstructor, setCredential, type Classroom, type CurrentUser } from './api'
import { cancelGoogleSignIn, GoogleSignIn } from './GoogleSignIn'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'

const AssignmentWorkspace = lazy(() => import('./AssignmentWorkspace').then((module) => ({ default: module.AssignmentWorkspace })))
const GroupReassignment = lazy(() => import('./GroupReassignment').then((module) => ({ default: module.GroupReassignment })))
const AddStudent = lazy(() => import('./AddStudent').then((module) => ({ default: module.AddStudent })))
const AdminDashboard = lazy(() => import('./AdminDashboard').then((module) => ({ default: module.AdminDashboard })))
const ClassroomSettings = lazy(() => import('./ClassroomSettings').then(module => ({ default: module.ClassroomSettings })))

function WorkspaceLoading() {
  const { language } = useLanguage()
  return <p role="status" data-testid="workspace-loading">{language === 'th' ? 'กำลังโหลดพื้นที่ทำงาน...' : 'Loading workspace...'}</p>
}

const demo = import.meta.env.VITE_AUTH_MODE === 'mock'
const demoInstructor = import.meta.env.VITE_DEMO_INSTRUCTOR_EMAIL || 'manasak.mako@gmail.com'
const demoStudent = import.meta.env.VITE_DEMO_STUDENT_EMAIL || 'totomove55@gmail.com'
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
  const renewalTimer = useRef<number | null>(null)
  const sessionVersion = useRef(0)
  const currentLanguage = useRef(language)
  currentLanguage.current = language
  const signInAction = useAsyncLock()
  const classroomAction = useAsyncLock()
  const instructorAction = useAsyncLock()
  const rosterAction = useAsyncLock()
  const [needsRenewal, setNeedsRenewal] = useState(false)
  const restoreStarted = useRef(false)
  const [restoring, setRestoring] = useState(true)
  const healthResource = useResource('health', getHealth)
  const health = healthResource.data?.status ?? (healthResource.error ? 'offline' : 'loading')
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [newClassroom, setNewClassroom] = useState('')
  const [error, setError] = useState('')
  const [rosterStatus, setRosterStatus] = useState<Record<number, string>>({})
  const [instructorInput, setInstructorInput] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [showClassroomForm, setShowClassroomForm] = useState(false)

  useEffect(() => {
    if (!restoreStarted.current) {
      restoreStarted.current = true
      const token = savedCredential()
      if (token) void handleSignIn(token).finally(() => setRestoring(false))
      else setRestoring(false)
    }
    return () => {
      if (sessionTimer.current != null) window.clearTimeout(sessionTimer.current)
      if (renewalTimer.current != null) window.clearTimeout(renewalTimer.current)
    }
  }, [])

  function signOut(message = '') {
    sessionVersion.current += 1
    cancelGoogleSignIn()
    if (sessionTimer.current != null) window.clearTimeout(sessionTimer.current)
    sessionTimer.current = null
    if (renewalTimer.current != null) window.clearTimeout(renewalTimer.current)
    renewalTimer.current = null
    setNeedsRenewal(false)
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
    if (renewalTimer.current != null) window.clearTimeout(renewalTimer.current)
    setNeedsRenewal(false)
    const delay = Math.max(0, (tokenExpiry(token) ?? Date.now() + 55 * 60 * 1000) - Date.now() - 30_000)
    renewalTimer.current = window.setTimeout(() => setNeedsRenewal(true), Math.max(0, delay - 5 * 60_000))
    sessionTimer.current = window.setTimeout(() => signOut(currentLanguage.current === 'th' ? 'เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง' : 'Session expired. Sign in again.'), delay)
  }

  async function handleSignIn(token: string, renewing = false) {
    if (!signInAction.begin()) return
    const version = renewing ? sessionVersion.current : ++sessionVersion.current
    setCredential(token)
    try {
      const [user, availableClassrooms] = await Promise.all([getMe(), getClassrooms()])
      if (version !== sessionVersion.current) return
      if (renewing && user.email !== currentUser?.email) throw new Error('Use the same Google account to continue the session.')
      setCurrentUser(user)
      setClassrooms(availableClassrooms)
      setSelectedId((current) => renewing && availableClassrooms.some((item) => item.id === current) ? current : availableClassrooms.find((item) => item.name === 'PairEval Demo')?.id ?? availableClassrooms[0]?.id ?? null)
      setError('')
      if (demo || (tokenExpiry(token) ?? 0) > Date.now() + 30_000) window.sessionStorage.setItem(sessionKey, token)
      scheduleSessionEnd(token)
    } catch {
      if (version === sessionVersion.current) signOut(language === 'th' ? 'เข้าสู่ระบบไม่สำเร็จ กรุณาลองอีกครั้ง' : 'Sign-in could not be verified. Please try again.')
    } finally {
      signInAction.finish()
    }
  }

  async function handleCreateClassroom() {
    if (!currentUser?.is_instructor || !newClassroom.trim() || !classroomAction.begin()) return
    const version = sessionVersion.current
    try {
      const classroom = await createClassroom(newClassroom.trim())
      if (version !== sessionVersion.current) return
      setClassrooms((items) => [...items, classroom])
      setSelectedId(classroom.id)
      setNewClassroom('')
      setShowClassroomForm(false)
      setError('')
    } catch { if (version === sessionVersion.current) setError(language === 'th' ? 'สร้างห้องเรียนไม่สำเร็จ' : 'Could not create the classroom.') }
    finally { classroomAction.finish() }
  }

  async function renameSelectedClassroom(classroomId: number, name: string) {
    const version = sessionVersion.current
    const updated = await renameClassroom(classroomId, name)
    if (version === sessionVersion.current) setClassrooms(items => items.map(item => item.id === classroomId ? updated : item))
  }

  async function deleteSelectedClassroom(classroomId: number, name: string) {
    const version = sessionVersion.current
    await deleteClassroom(classroomId, name)
    if (version !== sessionVersion.current) return
    setClassrooms(items => items.filter(item => item.id !== classroomId))
    const remaining = classrooms.filter(item => item.id !== classroomId)
    setSelectedId(current => current === classroomId ? remaining.find(item => item.name === 'PairEval Demo')?.id ?? remaining[0]?.id ?? null : current)
    setShowSettings(false)
  }

  async function handleRosterFile(classroomId: number, file: File) {
    if (!rosterAction.begin()) return
    const version = sessionVersion.current
    try {
      const result = await importRoster(classroomId, await file.text())
      if (version !== sessionVersion.current) return
      setRosterStatus((items) => ({ ...items, [classroomId]: result.errors.length ? result.errors.join('; ') : language === 'th' ? 'นำเข้านักศึกษา ' + result.imported + ' คนแล้ว' : 'Imported ' + result.imported + ' students.' }))
    } catch { if (version === sessionVersion.current) setRosterStatus((items) => ({ ...items, [classroomId]: language === 'th' ? 'นำเข้า CSV ไม่สำเร็จ' : 'Roster import failed.' })) }
    finally { rosterAction.finish() }
  }

  async function changeInstructor(classroomId: number, email: string, remove: boolean) {
    if (!instructorAction.begin()) return
    const version = sessionVersion.current
    try {
      const updated = remove ? await removeInstructor(classroomId, email) : await inviteInstructor(classroomId, email)
      if (version !== sessionVersion.current) return
      setClassrooms((items) => items.map((item) => item.id === classroomId ? updated : item))
      setInstructorInput('')
      setError('')
    } catch (problem) { if (version === sessionVersion.current) setError(problem instanceof Error ? problem.message : language === 'th' ? 'แก้ไขรายชื่ออาจารย์ไม่สำเร็จ' : 'Could not update instructors.') }
    finally { instructorAction.finish() }
  }

  const selected = classrooms.find((item) => item.id === selectedId)
  const canManage = Boolean(currentUser?.is_instructor && selected?.instructor_emails.split(',').includes(currentUser.email))

  return <div className="app-shell"><a className="skip-link" href="#main-content">{language === 'th' ? 'ข้ามไปเนื้อหาหลัก' : 'Skip to main content'}</a>
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">P<span>●</span></span><span>PairEval</span><small>{language === 'th' ? 'ระบบประเมินแบบเปรียบเทียบคู่' : 'Pairwise evaluation'}</small></div>
      <div className="sidebar-label">{t('Classrooms')} <span>{classrooms.length.toString().padStart(2, '0')}</span></div>
      <nav aria-label={t('Classrooms')} className="classroom-list">
        {classrooms.map((item, index) => <button key={item.id} type="button" aria-current={selectedId === item.id ? 'page' : undefined} className={'classroom-link ' + (selectedId === item.id ? 'active' : '')} onClick={() => { setSelectedId(item.id); setShowSettings(false) }}>
          <span className="classroom-index">{String(index + 1).padStart(2, '0')}</span><span>{item.name}</span><span className="nav-arrow">↗</span>
        </button>)}
        {!currentUser && <p className="sidebar-hint">{language === 'th' ? 'เข้าสู่ระบบเพื่อดูห้องเรียน' : 'Sign in to view classrooms'}</p>}
        {currentUser && classrooms.length === 0 && <p className="sidebar-hint">{language === 'th' ? 'ยังไม่มีห้องเรียน' : 'No classrooms yet'}</p>}
      </nav>
      {currentUser?.is_instructor && <Button type="button" className="classroom-create-toggle" aria-expanded={showClassroomForm} aria-controls="create-classroom-form" onClick={() => setShowClassroomForm(value => !value)}>{showClassroomForm ? (language === 'th' ? 'ปิด' : 'Close') : (language === 'th' ? '+ สร้างห้อง' : '+ New room')}</Button>}
      {currentUser?.is_instructor && <form id="create-classroom-form" className={'create-classroom' + (showClassroomForm ? ' is-open' : '')} onSubmit={(event) => { event.preventDefault(); void handleCreateClassroom() }}>
        <label htmlFor="new-classroom">{language === 'th' ? 'เพิ่มห้องเรียน' : 'Add classroom'}</label>
        <div><Input id="new-classroom" value={newClassroom} onChange={(event) => setNewClassroom(event.target.value)} required placeholder={language === 'th' ? 'ชื่อห้องเรียน' : 'Classroom name'} /><Button type="submit" aria-label={language === 'th' ? 'สร้างห้องเรียน' : 'Create classroom'} disabled={classroomAction.busy || !newClassroom.trim()} aria-busy={classroomAction.busy}>{language === 'th' ? 'สร้างห้อง' : 'Create'}</Button></div>
      </form>}
      <div className="sidebar-bottom"><span className={'status-dot ' + (health === 'ok' ? 'online' : '')} />{language === 'th' ? 'สถานะระบบ' : 'System status'}: {health}</div>
    </aside>

    <div className="content-shell">
      <header className="topbar"><div className="topbar-crumb">PAIR<span> / </span>{selected?.name || (language === 'th' ? 'ภาพรวม' : 'Overview')}</div><div className="topbar-actions">
        <div className="language-switch" role="group" aria-label="Language"><button type="button" aria-pressed={language === 'th'} className={language === 'th' ? 'selected' : ''} onClick={() => setLanguage('th')}>TH</button><button type="button" aria-pressed={language === 'en'} className={language === 'en' ? 'selected' : ''} onClick={() => setLanguage('en')}>EN</button></div>
        {currentUser && <button type="button" className="signout" onClick={() => signOut()}>{language === 'th' ? 'ออกจากระบบ' : 'Sign out'} ↗</button>}
      </div></header>

      <main id="main-content" tabIndex={-1} className="main-content">
        {needsRenewal && currentUser && <section className="session-renewal" aria-label={language === 'th' ? 'ต่ออายุการเข้าสู่ระบบ' : 'Continue your session'}>
          <p>{language === 'th' ? 'การเข้าสู่ระบบใกล้หมดอายุ ยืนยันด้วยบัญชี Google เดิมเพื่อใช้งานต่อ งานที่บันทึกแล้วยังคงอยู่' : 'Your session expires soon. Confirm with the same Google account to continue. Your saved work is preserved.'}</p>
          <GoogleSignIn autoPrompt onSignIn={(token) => void handleSignIn(token, true)} />
        </section>}
        {signInAction.busy && <p role="status">{t('Signing in...')}</p>}
        {error && <p role="status" className="notice error">{error}</p>}
        {restoring ? <p role="status">{language === 'th' ? 'กำลังกู้คืนการเข้าสู่ระบบ...' : 'Restoring sign-in...'}</p> : !currentUser ? <section className="welcome-layout">
          <div className="welcome-copy"><span className="eyebrow">{language === 'th' ? 'พื้นที่ประเมินแบบเปรียบเทียบคู่' : 'Pairwise evaluation workspace'}</span><h1>{language === 'th' ? <>มองทุกผลงาน<br /><em>อย่างเป็นธรรม</em></> : <>A fairer view<br />of every <em>contribution.</em></>}</h1><p>{language === 'th' ? 'เปรียบเทียบผลงานเป็นคู่ ติดตามความคืบหน้า และดูคะแนนในพื้นที่เดียว' : 'Compare work in pairs, track progress, and review scores in one place.'}</p></div>
          <div className="login-panel"><div className="panel-number">01 / ACCESS</div><h2>{language === 'th' ? 'เข้าสู่พื้นที่การเรียนรู้' : 'Enter your workspace'}</h2><p>{language === 'th' ? 'เลือกบทบาทเพื่อทดลองระบบด้วยข้อมูลตัวอย่าง' : 'Choose a role to explore the sample workspace.'}</p>
            {demo ? <div className="demo-options"><button type="button" disabled={signInAction.busy} className="demo-option" onClick={() => void handleSignIn('mock:' + demoInstructor)}><span className="role-icon">T</span><span><strong>{language === 'th' ? 'ทดลองเป็นอาจารย์' : 'Explore as instructor'}</strong><small>{demoInstructor}</small></span><span>↗</span></button><button type="button" disabled={signInAction.busy} className="demo-option" onClick={() => void handleSignIn('mock:' + demoStudent)}><span className="role-icon student">S</span><span><strong>{language === 'th' ? 'ทดลองเป็นนักศึกษา' : 'Explore as student'}</strong><small>{demoStudent}</small></span><span>↗</span></button><button type="button" disabled={signInAction.busy} className="demo-option" onClick={() => void handleSignIn('mock:67015114@kmitl.ac.th')}><span className="role-icon">A</span><span><strong>{language === 'th' ? 'ทดลองเป็นผู้ดูแลระบบ' : 'Explore as administrator'}</strong><small>67015114@kmitl.ac.th</small></span><span>→</span></button></div> : <GoogleSignIn onSignIn={handleSignIn} />}
            {demo && <p className="demo-note">{language === 'th' ? 'โหมดสาธิต · เลือกบทบาทด้านบนเพื่อเริ่มใช้งาน' : 'Demo mode · Choose a role above to get started'}</p>}
          </div>
        </section> : <>
          <div className="page-heading"><div><div className="eyebrow">{language === 'th' ? 'พื้นที่การเรียนรู้' : 'YOUR WORKSPACE'} / {currentUser.is_admin ? t('Administrator') : currentUser.is_instructor ? (language === 'th' ? 'อาจารย์' : 'INSTRUCTOR') : (language === 'th' ? 'นักศึกษา' : 'STUDENT')}</div><h1>{selected?.name || t('Classrooms')}</h1><p>{language === 'th' ? 'จัดการงานประเมิน ตอบแบบประเมิน และติดตามคะแนน' : 'Manage assignments, complete evaluations, and track scores.'}</p></div><div className="user-badge">{currentUser.picture_url?.startsWith('https://') ? <img src={currentUser.picture_url} alt="" referrerPolicy="no-referrer" /> : <span>{currentUser.email.slice(0, 1).toUpperCase()}</span>}<div><strong>{currentUser.is_admin ? t('Administrator') : currentUser.is_instructor ? (language === 'th' ? 'อาจารย์' : 'Instructor') : t('Student')}</strong><small>{currentUser.email}</small></div></div></div>
          {currentUser.is_admin && <Suspense fallback={<WorkspaceLoading />}><AdminDashboard health={health} classroomRevision={JSON.stringify(classrooms.map(item => [item.id, item.name]))} /></Suspense>}
          {selected ? <div className="workspace-grid"><div className="workspace-main"><div className="section-heading"><span className="section-count">01</span><h2>{t('Assignments')}</h2><span className="heading-rule" /></div><Suspense fallback={<WorkspaceLoading />}><AssignmentWorkspace key={selected.id} classroomId={selected.id} isInstructor={canManage} email={currentUser.email} /></Suspense></div>
            <aside className="workspace-side" data-testid="workspace-side"><div className="info-panel"><span className="panel-number">CLASSROOM / {String(selected.id).padStart(2, '0')}</span><h3>{language === 'th' ? 'รายละเอียดห้องเรียน' : 'Classroom details'}</h3><div className="info-row"><span>{language === 'th' ? 'รหัสห้อง' : 'Class ID'}</span><strong>#{selected.id}</strong></div><div className="info-row"><span>{language === 'th' ? 'อาจารย์' : 'Instructors'}</span><strong>{selected.instructor_emails.split(',').filter(Boolean).length}</strong></div></div>
              {canManage && <div className="side-tools"><Button type="button" variant="outline" className="tools-toggle" onClick={() => setShowSettings((value) => !value)} aria-expanded={showSettings} aria-controls="classroom-tools">{language === 'th' ? 'จัดการห้องเรียน' : 'Manage classroom'} <span>{showSettings ? '−' : '＋'}</span></Button>{showSettings && <div id="classroom-tools" className="tools-content"><Suspense fallback={<WorkspaceLoading />}><ClassroomSettings key={selected.id} classroom={selected} onRename={name => renameSelectedClassroom(selected.id, name)} onDelete={() => deleteSelectedClassroom(selected.id, selected.name)} /></Suspense><label>{language === 'th' ? 'นำเข้ารายชื่อนักศึกษา (CSV)' : 'Import student roster (CSV)'}<Input disabled={rosterAction.busy} aria-busy={rosterAction.busy} type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void handleRosterFile(selected.id, file) }} /></label>{rosterStatus[selected.id] && <p role="status">{rosterStatus[selected.id]}</p>}<Suspense fallback={<WorkspaceLoading />}><AddStudent key={selected.id} classroomId={selected.id} /></Suspense><div className="instructor-list"><strong>{language === 'th' ? 'อาจารย์ในห้อง' : 'Classroom instructors'}</strong>{selected.instructor_emails.split(',').filter(Boolean).map((email) => <div key={email}><span>{email}</span><Button type="button" variant="outline" disabled={instructorAction.busy} onClick={() => void changeInstructor(selected.id, email, true)}>{t('Remove')}</Button></div>)}</div><form onSubmit={(event) => { event.preventDefault(); void changeInstructor(selected.id, instructorInput, false) }}><Input type="email" aria-label={language === 'th' ? 'อีเมลอาจารย์' : 'Instructor email'} placeholder={language === 'th' ? 'อีเมลอาจารย์ที่อนุมัติ' : 'Approved instructor email'} value={instructorInput} onChange={(event) => setInstructorInput(event.target.value)} /><Button type="submit" disabled={instructorAction.busy} aria-busy={instructorAction.busy}>{instructorAction.busy ? t('Working...') : language === 'th' ? 'เชิญ' : 'Invite'}</Button></form><Suspense fallback={<WorkspaceLoading />}><GroupReassignment classroomId={selected.id} isInstructor /></Suspense></div>}</div>}
              {!canManage && <Suspense fallback={<WorkspaceLoading />}><GroupReassignment classroomId={selected.id} isInstructor={false} /></Suspense>}
              <div className="side-quote"><span>“</span><p>{language === 'th' ? 'ทุกความคิดเห็นช่วยให้เห็นภาพที่ครบขึ้น' : 'Every perspective makes the picture clearer.'}</p><small>PAIREVAL / 2026</small></div>
            </aside></div> : currentUser.is_admin ? null : <div className="empty-state">{language === 'th' ? 'เลือกห้องเรียนจากแถบด้านซ้าย' : 'Select a classroom from the sidebar.'}</div>}
        </>}
      </main>
      <footer className="app-footer"><span>PAIR / EVAL © {new Date().getFullYear()}</span><span>{language === 'th' ? 'การประเมินที่เห็นทุกมุมมอง' : 'A clearer view of every contribution'}</span></footer>
    </div>
  </div>
}
