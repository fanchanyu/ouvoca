import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ToastProvider } from './components/ui'
import { I18nProvider } from './i18n'
import './index.css'
import './styles/galaxy.css'  // v3.64 uiverse-io/galaxy（MIT）精選元件

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <BrowserRouter>
        <ToastProvider>
          <App />
        </ToastProvider>
      </BrowserRouter>
    </I18nProvider>
  </React.StrictMode>,
)
