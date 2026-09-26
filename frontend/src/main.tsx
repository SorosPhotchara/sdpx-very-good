import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { LanguageProvider } from './i18n'
import '@fontsource-variable/noto-sans-thai/wght.css'
import './index.css'
import { ToastProvider } from './components/ui/toast'

const root = document.getElementById('root')!
createRoot(root).render(
  <React.StrictMode>
    <LanguageProvider><ToastProvider><App /></ToastProvider></LanguageProvider>
  </React.StrictMode>
)
