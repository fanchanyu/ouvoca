/**
 * i18n 系統 — 輕量、無外部依賴。
 *
 * 用法：
 *   const { t, lang, setLang } = useTranslation()
 *   t('dashboard.title')
 *   t('dashboard.soCount', { count: 5 })
 *
 * 切換語言會：
 *   1. 寫入 localStorage（持久化）
 *   2. 更新 <html lang> 屬性
 *   3. 觸發所有訂閱元件重新渲染
 */
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { zhTW } from './locales/zh-TW'
import { en } from './locales/en'

export type Lang = 'zh-TW' | 'en'

const dictionaries: Record<Lang, typeof zhTW> = {
  'zh-TW': zhTW,
  'en': en as typeof zhTW,
}

interface I18nContextValue {
  lang: Lang
  setLang: (l: Lang) => void
  t: (path: string, vars?: Record<string, string | number>) => string
  /** 取得陣列（如 suggestions） */
  ta: (path: string) => string[]
}

const I18nContext = createContext<I18nContextValue | null>(null)

function getNested(obj: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((acc, k) => {
    if (acc && typeof acc === 'object' && k in (acc as object)) {
      return (acc as Record<string, unknown>)[k]
    }
    return undefined
  }, obj)
}

function interpolate(s: string, vars?: Record<string, string | number>) {
  if (!vars) return s
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`))
}

function getInitialLang(): Lang {
  if (typeof window === 'undefined') return 'zh-TW'
  const stored = localStorage.getItem('llm-erp-lang') as Lang | null
  if (stored && (stored === 'zh-TW' || stored === 'en')) return stored
  // 從瀏覽器偏好猜
  const browser = navigator.language.toLowerCase()
  if (browser.startsWith('zh')) return 'zh-TW'
  return 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => getInitialLang())

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    localStorage.setItem('llm-erp-lang', l)
  }, [])

  const t = useCallback((path: string, vars?: Record<string, string | number>) => {
    const dict = dictionaries[lang]
    const val = getNested(dict, path)
    if (typeof val === 'string') return interpolate(val, vars)
    // fallback：找不到回 path 本身
    return path
  }, [lang])

  const ta = useCallback((path: string): string[] => {
    const dict = dictionaries[lang]
    const val = getNested(dict, path)
    return Array.isArray(val) ? val as string[] : []
  }, [lang])

  return (
    <I18nContext.Provider value={{ lang, setLang, t, ta }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useTranslation must be used within I18nProvider')
  return ctx
}
