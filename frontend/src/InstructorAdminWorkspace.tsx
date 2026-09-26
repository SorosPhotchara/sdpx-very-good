import { useState, type FormEvent } from 'react'
import { approveInstructor, getInstructorApprovals, revokeInstructor } from './api'
import { useLanguage } from './i18n'
import { useResource } from './useResource'
import { useAsyncLock } from './useAsyncLock'

export function InstructorAdminWorkspace() {
  const { language, t } = useLanguage()
  const resource = useResource('instructor-approvals', getInstructorApprovals)
  const instructors = resource.data ?? []
  const action = useAsyncLock()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!action.begin()) return
    try {
      await approveInstructor(email.trim())
      setEmail('')
      await resource.refresh()
      setMessage(t('Instructor approved.'))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t('Could not approve instructor.'))
    } finally {
      action.finish()
    }
  }

  async function revoke(emailToRevoke: string) {
    if (!action.begin()) return
    try {
      await revokeInstructor(emailToRevoke)
      await resource.refresh()
      setMessage(t('Instructor access revoked.'))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t('Could not revoke instructor.'))
    } finally {
      action.finish()
    }
  }

  return <section className="instructor-admin" data-testid="instructor-admin">
    <div>
      <p className="eyebrow">{language === 'th' ? 'การเข้าถึงระบบ' : 'SYSTEM ACCESS'}</p>
      <h2>{t('Manage approved instructors')}</h2>
      <p>{t('Approved instructors can be invited into classrooms by a classroom instructor.')}</p>
    </div>
    <form className="instructor-admin-form" onSubmit={(event) => void submit(event)}>
      <label htmlFor="approved-instructor-email">{t('Instructor Google email')}</label>
      <div><input id="approved-instructor-email" data-testid="approved-instructor-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.edu" />
        <button type="submit" disabled={action.busy || resource.loading} aria-busy={action.busy}>{t(action.busy ? 'Working...' : 'Approve instructor')}</button></div>
    </form>
    {resource.loading && <p role="status">{t('Loading...')}</p>}
    {resource.error && <div role="alert">{resource.error} <button type="button" onClick={() => void resource.refresh()}>{t('Retry')}</button></div>}
    <ul className="instructor-admin-list">
      {instructors.map((instructor) => <li key={instructor.email}>
        <div><strong>{instructor.email}</strong><small>{instructor.source === 'environment' ? t('Configured by administrator') : t('Approved by') + ` ${instructor.approved_by ?? ''}`}</small></div>
        {instructor.source === 'database' && <button type="button" disabled={action.busy || resource.loading} aria-label={`${t('Revoke')} ${instructor.email}`} onClick={() => void revoke(instructor.email)}>{t('Revoke')}</button>}
      </li>)}
    </ul>
    {message && <p role="status" className="instructor-admin-status">{message}</p>}
  </section>
}
