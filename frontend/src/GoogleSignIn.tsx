import { useEffect, useRef, useState } from 'react'
import { useLanguage } from './i18n'

type GoogleClient = {
  accounts: {
    id: {
      initialize(options: { client_id: string; callback: (response: { credential: string }) => void }): void
      renderButton(element: HTMLElement, options: { theme: string; size: string }): void
    }
  }
}

let initialized = false
let credentialHandler: ((credential: string) => void) | null = null

export function GoogleSignIn({ onSignIn }: { onSignIn: (credential: string) => void }) {
  const { t } = useLanguage()
  const buttonRef = useRef<HTMLDivElement>(null)
  const handlerRef = useRef(onSignIn)
  const [error, setError] = useState('')
  handlerRef.current = onSignIn

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) {
      setError('Google sign-in is not configured.')
      return
    }

    let active = true
    let rendered = false
    const start = () => {
      const google = (window as typeof window & { google?: GoogleClient }).google
      if (!active || rendered || !google || !buttonRef.current) return
      credentialHandler = (credential) => handlerRef.current(credential)
      if (!initialized) {
        google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => credentialHandler?.(response.credential),
        })
        initialized = true
      }
      google.accounts.id.renderButton(buttonRef.current, { theme: 'outline', size: 'large' })
      rendered = true
    }
    const onError = () => active && setError('Google sign-in could not load.')

    let script = document.querySelector<HTMLScriptElement>('script[data-google-signin]')
    if (!script) {
      script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.dataset.googleSignin = 'true'
      document.head.appendChild(script)
    }
    script.addEventListener('load', start)
    script.addEventListener('error', onError)
    start()

    return () => {
      active = false
      script?.removeEventListener('load', start)
      script?.removeEventListener('error', onError)
      credentialHandler = null
    }
  }, [])

  return error ? <p role="status">{t(error)}</p> : <div ref={buttonRef} data-testid="google-sign-in" />
}
