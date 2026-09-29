import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useLanguage } from '../../i18n'
import { Toaster, toast } from 'sonner'

type Notice = { id: number; message: string; kind: 'success' | 'error' | 'info' }
type ToastActions = { publish: (message: string, kind: Notice['kind']) => Notice; dismiss: (id: number) => void }
const Actions = createContext<ToastActions | null>(null)
const Active = createContext<number | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const nextId = useRef(0)
  const [active, setActive] = useState<number | null>(null)
  const actions = useMemo<ToastActions>(() => ({
    publish(message, kind) {
      toast.dismiss(`notice-${nextId.current}`)
      const notice = { id: ++nextId.current, message, kind }
      setActive(notice.id)
      return notice
    },
    dismiss(id) { toast.dismiss(`notice-${id}`); setActive(current => current === id ? null : current) },
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
  const { language } = useLanguage()
  const element = useRef<HTMLDivElement>(null)
  const visible = notice != null && notice.id === active
  useLayoutEffect(() => {
    // The top layer avoids clipping and containing blocks in responsive panels.
    if (visible && !element.current?.matches(':popover-open')) element.current?.showPopover?.()
  }, [visible, notice?.id])
  useEffect(() => {
    if (!visible) return
    toast[notice.kind](<span role={assertive ? 'alert' : 'status'} aria-atomic="true">{notice.message}</span>, {
      id: `notice-${notice.id}`, testId: 'action-toast', duration: notice.kind === 'error' ? Infinity : 7000,
    })
  }, [visible, notice, assertive])
  if (!visible) return null
  return <div ref={element} popover="manual" className="toast-layer"
    onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); toast.dismiss(`notice-${notice.id}`) } }}>
    <Toaster key={notice.id} theme="light" position="bottom-right" richColors closeButton visibleToasts={1}
      className="app-toaster" offset={16} mobileOffset={16}
      containerAriaLabel={language === 'th' ? 'แจ้งเตือน' : 'Notifications'}
      toastOptions={{
        closeButtonAriaLabel: language === 'th' ? 'ปิดแจ้งเตือน' : 'Dismiss notification',
        style: { position: 'fixed', left: 'auto', bottom: 'max(16px, env(safe-area-inset-bottom))', right: 'max(16px, env(safe-area-inset-right))', width: 'min(400px, calc(100% - 32px))' },
      }} />
  </div>
}
