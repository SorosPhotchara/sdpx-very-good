import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useLanguage } from '../../i18n'
import { Button } from './button'

type Notice = { id: number; message: string; kind: 'success' | 'error' | 'info' }
type ToastActions = { publish: (message: string, kind: Notice['kind']) => Notice; dismiss: (id: number) => void }
const Actions = createContext<ToastActions | null>(null)
const Active = createContext<number | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const nextId = useRef(0)
  const [active, setActive] = useState<number | null>(null)
  const actions = useMemo<ToastActions>(() => ({
    publish(message, kind) {
      const notice = { id: ++nextId.current, message, kind }
      setActive(notice.id)
      return notice
    },
    dismiss(id) { setActive(current => current === id ? null : current) },
  }), [])
  return <Actions.Provider value={actions}><Active.Provider value={active}>{children}</Active.Provider></Actions.Provider>
}

export function useNotice() {
  const actions = useContext(Actions)
  if (!actions) throw new Error('ToastProvider is required')
  const current = useRef<Notice | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const show = useCallback((message: string, kind: Notice['kind'] = 'success') => {
    if (current.current) actions.dismiss(current.current.id)
    current.current = message ? actions.publish(message, kind) : null
    setNotice(current.current)
  }, [actions])
  return [notice, show] as const
}

// Keep the notice with its action's accessible context; CSS places it in the viewport.
export function ToastNotice({ notice, assertive = false }: { notice: Notice | null; assertive?: boolean }) {
  const active = useContext(Active)
  const actions = useContext(Actions)!
  const { language } = useLanguage()
  const element = useRef<HTMLDivElement>(null)
  const [pause, setPause] = useState({ id: 0, value: false })
  const paused = pause.id === notice?.id && pause.value
  const visible = notice != null && notice.id === active
  useLayoutEffect(() => {
    // The top layer avoids clipping and containing blocks in responsive panels.
    if (visible && !element.current?.matches(':popover-open')) element.current?.showPopover?.()
  }, [visible, notice?.id])
  useEffect(() => {
    if (!visible || paused || notice.kind === 'error') return
    const timer = window.setTimeout(() => actions.dismiss(notice.id), 7000)
    return () => window.clearTimeout(timer)
  }, [visible, paused, notice, actions])
  if (!visible) return null
  return <div ref={element} popover="manual" className={'action-toast action-toast--' + notice.kind} data-testid="action-toast"
    onMouseEnter={() => setPause({ id: notice.id, value: true })} onMouseLeave={() => setPause({ id: notice.id, value: false })}
    onFocus={() => setPause({ id: notice.id, value: true })} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setPause({ id: notice.id, value: false }) }}
    onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); actions.dismiss(notice.id) } }}>
    <span className="action-toast-symbol" aria-hidden="true">{notice.kind === 'error' ? '!' : notice.kind === 'info' ? 'i' : '✓'}</span>
    <p role={assertive ? 'alert' : 'status'} aria-live={assertive ? 'assertive' : 'polite'} aria-atomic="true">{notice.message}</p>
    <Button type="button" variant="ghost" size="icon" className="action-toast-close"
      aria-label={language === 'th' ? 'ปิดแจ้งเตือน' : 'Dismiss notification'} onClick={() => actions.dismiss(notice.id)}>×</Button>
  </div>
}
