import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { useResource } from '../src/useResource'
import { GoogleSignIn, cancelGoogleSignIn } from '../src/GoogleSignIn'
import { LanguageProvider } from '../src/i18n'

function Harness() {
  const [key, setKey] = useState('first')
  const resource = useResource(key, async () => {
    const response = await fetch(`/resource/${key}`)
    if (!response.ok) throw new Error('Temporary failure')
    return response.text()
  })
  return <><button onClick={() => setKey('second')}>Switch</button><button onClick={() => void resource.refresh()}>Retry</button><output>{resource.loading ? 'Loading' : resource.error || resource.data}</output></>
}
function GoogleHarness() {
  const [credential, setCredential] = useState('')
  const [renewing, setRenewing] = useState(false)
  const [visible, setVisible] = useState(true)
  return <LanguageProvider>
    <button onClick={() => setRenewing(true)}>Renew</button>
    <button onClick={() => { cancelGoogleSignIn(); setVisible(false); setCredential('') }}>Sign out</button>
    {visible && <GoogleSignIn autoPrompt={renewing} onSignIn={setCredential} />}
    <output>{credential || 'Signed out'}</output>
  </LanguageProvider>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode>{location.search === '?google' ? <GoogleHarness /> : <Harness />}</React.StrictMode>)
