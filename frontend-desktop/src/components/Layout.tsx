/**
 * 主框架 — i18n + 響應式 sidebar + 使用者下拉 + 通知 + 語言切換
 *
 * 美術重點：
 * - 漸層 brand logo
 * - 柔和陰影
 * - 平滑過渡
 * - 觸控 44px+
 * - 中英文切換器（國旗 icon）
 */
import { useCallback, useEffect, useState, useRef } from 'react'
import { Outlet, Link, useLocation, Navigate, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { useToast } from './ui'
import { useTranslation, type Lang } from '../i18n'
import DesktopNotifications, { type ToastEntry } from './DesktopNotifications'

const navConfig = [
  { path: '/',                key: 'dashboard',      icon: '📊', group: 'overview' },
  { path: '/chat',            key: 'aiAssistant',    icon: '💬', group: 'overview' },
  { path: '/events',          key: 'eventStream',    icon: '📡', group: 'overview' },
  { path: '/inventory',       key: 'inventory',      icon: '📦', group: 'operations' },
  { path: '/purchase',        key: 'purchase',       icon: '🛒', group: 'operations' },
  { path: '/production',      key: 'production',     icon: '🏭', group: 'operations' },
  { path: '/sales',           key: 'sales',          icon: '💰', group: 'operations' },
  { path: '/quality',         key: 'quality',        icon: '🔬', group: 'operations' },
  { path: '/permissions',     key: 'permissions',    icon: '🛡️', group: 'system' },
  { path: '/me/permissions',  key: 'myPermissions',  icon: '🔑', group: 'system' },
] as const

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { token, user, logout } = useAuthStore()
  const toast = useToast()
  const { t, lang, setLang } = useTranslation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [langMenuOpen, setLangMenuOpen] = useState(false)
  const [notifCount, setNotifCount] = useState(0)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const langMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => { setDrawerOpen(false) }, [location.pathname])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
      if (langMenuRef.current && !langMenuRef.current.contains(e.target as Node)) {
        setLangMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // v3.3：把 SSE 訂閱委派給 <DesktopNotifications />（同時負責桌面 Notification）。
  // 這裡只保留 in-app toast banner（最近 5 則）+ badge 計數。
  const [recentToasts, setRecentToasts] = useState<ToastEntry[]>([])
  const handleToast = useCallback((entry: ToastEntry) => {
    setNotifCount((c) => c + 1)
    setRecentToasts((prev) => [entry, ...prev].slice(0, 5))
    // 5 秒後自動移除這條 banner
    setTimeout(() => {
      setRecentToasts((prev) => prev.filter((t) => t.id !== entry.id))
    }, 5000)
  }, [])

  if (!token) return <Navigate to="/login" replace />

  function handleLogout() {
    logout()
    toast.success(t('userMenu.logout'))
    navigate('/login')
  }

  const groups = ['overview', 'operations', 'system'] as const

  return (
    <div className="min-h-screen bg-gradient-to-br from-ink-50 to-brand-50/30 flex">
      {drawerOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-ink-900/60 backdrop-blur-sm z-30"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* ─── Sidebar ─── */}
      <aside className={[
        'fixed lg:sticky top-0 left-0 z-40 h-screen w-64 flex flex-col',
        'bg-gradient-to-b from-ink-900 to-ink-800 text-white',
        'transition-transform duration-300 shadow-2xl lg:shadow-none',
        drawerOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      ].join(' ')}>
        {/* Brand */}
        <div className="p-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-xl font-bold shadow-lg shadow-brand-500/30">
              L
            </div>
            <div>
              <p className="font-bold text-h3 leading-tight tracking-wide">LLM-ERP</p>
              <p className="text-caption text-white/50">AI-Native ERP</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          {groups.map(group => (
            <div key={group} className="mb-5">
              <p className="px-3 mb-2 text-caption uppercase tracking-wider text-white/40 font-semibold">
                {t(`nav.group.${group}`)}
              </p>
              <div className="space-y-0.5">
                {navConfig.filter(i => i.group === group).map(item => {
                  const active = location.pathname === item.path
                  return (
                    <Link
                      key={item.path} to={item.path}
                      className={[
                        'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-body-sm',
                        active
                          ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white font-medium shadow-md shadow-brand-500/20'
                          : 'text-white/70 hover:bg-white/5 hover:text-white',
                      ].join(' ')}
                    >
                      <span className="text-lg">{item.icon}</span>
                      <span>{t(`nav.${item.key}`)}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-4 border-t border-white/10 text-caption text-white/40 space-y-1">
          <p>{t('footer.version')} · {new Date().getFullYear()}</p>
          <p className="text-white/30">
            <a
              href="https://github.com/fanchanyu/erpilot"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-brand-300 transition-colors"
            >
              {t('footer.madeBy')}
            </a>
          </p>
        </div>
      </aside>

      {/* ─── Main area ─── */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white/80 backdrop-blur-lg border-b border-ink-100 flex items-center justify-between px-4 sm:px-6 sticky top-0 z-20">
          <button
            className="lg:hidden p-2 -ml-2 text-ink-700 focus-ring rounded"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>

          <div className="hidden sm:block">
            <p className="text-body-sm text-ink-500 font-medium">
              {t(`nav.${navConfig.find(i => i.path === location.pathname)?.key || 'dashboard'}`)}
            </p>
          </div>

          <div className="flex items-center gap-1 ml-auto">
            {/* Language switcher */}
            <div className="relative" ref={langMenuRef}>
              <button
                onClick={() => setLangMenuOpen(o => !o)}
                className="flex items-center gap-1.5 px-2.5 h-9 rounded-lg hover:bg-ink-100 focus-ring transition-colors text-body-sm font-medium text-ink-700"
                aria-label="Language"
              >
                <span>{lang === 'zh-TW' ? '🇹🇼' : '🇺🇸'}</span>
                <span className="hidden sm:inline">{lang === 'zh-TW' ? '繁中' : 'EN'}</span>
              </button>
              {langMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-44 bg-white rounded-card shadow-pop border border-ink-100 py-2 animate-slide-up z-30">
                  <LangItem flag="🇹🇼" label={t('footer.languageZh')} value="zh-TW"
                    current={lang} onClick={(l) => { setLang(l); setLangMenuOpen(false) }} />
                  <LangItem flag="🇺🇸" label={t('footer.languageEn')} value="en"
                    current={lang} onClick={(l) => { setLang(l); setLangMenuOpen(false) }} />
                </div>
              )}
            </div>

            {/* Notification */}
            <button
              onClick={() => { navigate('/events'); setNotifCount(0) }}
              className="relative p-2 rounded-lg hover:bg-ink-100 focus-ring transition-colors"
              aria-label="Notifications"
            >
              <span className="text-xl">🔔</span>
              {notifCount > 0 && (
                <span className="absolute top-1 right-1 min-w-[18px] h-[18px] bg-gradient-to-br from-danger-500 to-danger-600 text-white text-caption font-bold rounded-full flex items-center justify-center px-1 shadow">
                  {notifCount > 99 ? '99+' : notifCount}
                </span>
              )}
            </button>

            {/* User menu */}
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(o => !o)}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-ink-100 focus-ring transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center font-semibold shadow">
                  {(user?.username || '?').slice(0, 1).toUpperCase()}
                </div>
                <span className="hidden sm:block text-body-sm text-ink-700 font-medium">
                  {user?.username || 'Guest'}
                </span>
              </button>
              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-card shadow-pop border border-ink-100 py-2 animate-slide-up z-30">
                  <div className="px-4 py-2 border-b border-ink-100">
                    <p className="font-semibold text-ink-900">{user?.username}</p>
                    <p className="text-caption text-ink-500">{user?.employee_id}</p>
                  </div>
                  <button
                    className="w-full text-left px-4 py-2.5 hover:bg-ink-50 text-body-sm transition-colors"
                    onClick={() => { setUserMenuOpen(false); toast.info(t('userMenu.profile')) }}
                  >👤 {t('userMenu.profile')}</button>
                  <button
                    className="w-full text-left px-4 py-2.5 hover:bg-ink-50 text-body-sm transition-colors"
                    onClick={() => { setUserMenuOpen(false); navigate('/me/permissions') }}
                  >🛡️ {t('userMenu.myPerms')}</button>
                  <div className="border-t border-ink-100 mt-1 pt-1">
                    <button
                      className="w-full text-left px-4 py-2.5 hover:bg-danger-50 text-body-sm text-danger-700 transition-colors"
                      onClick={handleLogout}
                    >↩ {t('userMenu.logout')}</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 overflow-x-hidden">
          <Outlet />
        </main>

        {/* v3.3 桌機通知（背景 SSE + Browser Notification） */}
        {token && <DesktopNotifications onToast={handleToast} />}

        {/* v3.3 in-app toast banner（最近 5 則，5 秒後自動消失） */}
        {recentToasts.length > 0 && (
          <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 pointer-events-none">
            {recentToasts.map((t) => (
              <div
                key={t.id}
                className="bg-white border border-brand-200 shadow-pop rounded-card px-4 py-3 max-w-sm pointer-events-auto animate-slide-up"
              >
                <div className="font-semibold text-ink-900 text-body-sm">{t.title}</div>
                <div className="text-caption text-ink-600 mt-0.5">{t.body}</div>
                <div className="text-caption text-ink-400 mt-1 font-mono">
                  {new Date(t.ts).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function LangItem({ flag, label, value, current, onClick }: {
  flag: string; label: string; value: Lang; current: Lang
  onClick: (v: Lang) => void
}) {
  const active = current === value
  return (
    <button
      className={`w-full text-left px-4 py-2.5 hover:bg-ink-50 text-body-sm transition-colors flex items-center gap-2 ${active ? 'bg-brand-50 text-brand-700 font-medium' : ''}`}
      onClick={() => onClick(value)}
    >
      <span>{flag}</span><span className="flex-1">{label}</span>
      {active && <span className="text-brand-500">✓</span>}
    </button>
  )
}
