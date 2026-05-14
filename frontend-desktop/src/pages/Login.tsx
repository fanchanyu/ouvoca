/**
 * Login 頁 — i18n + 漸層美術 + 動效
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { apiLogin, apiHealth, ApiError } from '../lib/api'
import { Button, useToast } from '../components/ui'
import { useTranslation, type Lang } from '../i18n'

export default function Login() {
  const navigate = useNavigate()
  const toast = useToast()
  const setAuth = useAuthStore(s => s.setAuth)
  const loginAsDemo = useAuthStore(s => s.loginAsDemo)
  const { t, lang, setLang } = useTranslation()

  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoBypass, setDemoBypass] = useState(false)
  const [version, setVersion] = useState<string>('')
  const [llmProvider, setLlmProvider] = useState<string>('')

  useEffect(() => {
    apiHealth().then(h => {
      setDemoBypass(h.demo_bypass)
      setVersion(h.version)
      setLlmProvider(h.llm_provider)
    }).catch(() => {/* ignore */})
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null); setLoading(true)
    try {
      const res = await apiLogin(username, password)
      setAuth(res.access_token, {
        id: res.user.id, username: res.user.username,
        employee_id: res.user.employee_id, is_superuser: res.user.is_superuser,
      })
      toast.success(`${t('common.success')}: ${res.user.username}`)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('login.backendOffline'))
    } finally { setLoading(false) }
  }

  function useDemoToken() {
    loginAsDemo()
    toast.info('Demo mode')
    navigate('/')
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-ink-900">
      {/* 動態漸層背景 */}
      <div className="absolute inset-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-600 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse-slow" />
        <div className="absolute top-1/2 -right-40 w-96 h-96 bg-brand-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse-slow" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse-slow" />
      </div>

      {/* 語言切換器 — 右上角 */}
      <div className="absolute top-6 right-6 z-10 flex gap-1 bg-white/10 backdrop-blur-md rounded-lg p-1 border border-white/20">
        <LangBtn flag="🇹🇼" label="繁中" value="zh-TW" current={lang} onClick={setLang} />
        <LangBtn flag="🇺🇸" label="EN" value="en" current={lang} onClick={setLang} />
      </div>

      {/* 登入卡 */}
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-8 sm:p-10 w-full max-w-md relative z-10 animate-slide-up border border-white/20">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white text-3xl font-bold shadow-lg shadow-brand-500/30 mb-4">
            L
          </div>
          <h1 className="text-h1 text-ink-900 tracking-tight">{t('login.title')}</h1>
          <p className="text-body-sm text-ink-500 mt-2">
            {t('login.subtitle')}
            {version && <span className="text-ink-400"> · v{version}</span>}
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-body-sm text-ink-700 mb-1.5 font-medium">
              {t('login.username')}
            </label>
            <input
              type="text" value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-4 py-3 border border-ink-200 rounded-input bg-white focus-ring focus:border-brand-400 transition-colors"
              autoComplete="username" required
            />
          </div>
          <div>
            <label className="block text-body-sm text-ink-700 mb-1.5 font-medium">
              {t('login.password')}
            </label>
            <input
              type="password" value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-ink-200 rounded-input bg-white focus-ring focus:border-brand-400 transition-colors"
              autoComplete="current-password" required
            />
          </div>
          {error && (
            <div className="bg-danger-50 border border-danger-200 text-danger-700 px-3 py-2 rounded-input text-body-sm flex items-start gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}
          <Button type="submit" variant="primary" size="lg"
            loading={loading} className="w-full mt-2">
            {loading ? t('login.signingIn') : t('login.signIn')}
          </Button>
        </form>

        {demoBypass && (
          <>
            <div className="my-6 flex items-center gap-3">
              <div className="flex-1 border-t border-ink-200" />
              <span className="text-caption text-ink-400">{t('login.or')}</span>
              <div className="flex-1 border-t border-ink-200" />
            </div>
            <Button onClick={useDemoToken} variant="secondary" size="md" className="w-full bg-warning-50 hover:bg-warning-100 border-warning-200 text-warning-800">
              ✨ {t('login.demoMode')}
            </Button>
            <p className="mt-3 text-caption text-ink-400 text-center leading-relaxed">
              {t('login.demoHint')}
            </p>
          </>
        )}

        {/* LLM provider 提示 */}
        {llmProvider && (
          <div className="mt-6 pt-4 border-t border-ink-100 flex items-center justify-center gap-2 text-caption text-ink-400">
            <span className="w-2 h-2 rounded-full bg-success-500 animate-pulse" />
            <span>{llmProvider}</span>
          </div>
        )}
      </div>
    </div>
  )
}

function LangBtn({ flag, label, value, current, onClick }: {
  flag: string; label: string; value: Lang; current: Lang
  onClick: (v: Lang) => void
}) {
  const active = current === value
  return (
    <button
      onClick={() => onClick(value)}
      className={[
        'px-3 py-1.5 rounded-md text-body-sm font-medium transition-all flex items-center gap-1.5',
        active ? 'bg-white text-ink-900 shadow' : 'text-white/80 hover:text-white',
      ].join(' ')}
    >
      <span>{flag}</span><span>{label}</span>
    </button>
  )
}
