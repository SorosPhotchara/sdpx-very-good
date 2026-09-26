import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { LanguageProvider } from './i18n'
import '@fontsource-variable/noto-sans-thai/wght.css'
import './index.css'

const root = document.getElementById('root')!
createRoot(root).render(
  <React.StrictMode>
    <LanguageProvider><App /></LanguageProvider>
  </React.StrictMode>
)
