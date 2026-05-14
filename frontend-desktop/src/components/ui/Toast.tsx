// 全域 Toast 通知系統 — 用法：
//   const toast = useToast()
//   toast.success('採購單已建立')
//   toast.error('庫存不足', { description: '需要 100，可用 50' })

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

type Tone = 'success' | 'error' | 'warning' | 'info'

interface ToastItem {
  id: number
  tone: Tone
  title: string
  description?: string
  duration?: number
}

interface ToastContextValue {
  show: (item: Omit<ToastItem, 'id'>) => void
  success: (title: string, opts?: { description?: string; duration?: number }) => void
  error:   (title: string, opts?: { description?: string; duration?: number }) => void
  warning: (title: string, opts?: { description?: string; duration?: number }) => void
  info:    (title: string, opts?: { description?: string; duration?: number }) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const toneStyle: Record<Tone, { bg: string; ring: string; icon: string }> = {
  success: { bg: 'bg-white border-l-4 border-success-500', ring: 'ring-success-200', icon: '✓' },
  error:   { bg: 'bg-white border-l-4 border-danger-500',  ring: 'ring-danger-200',  icon: '✕' },
  warning: { bg: 'bg-white border-l-4 border-warning-500', ring: 'ring-warning-200', icon: '!' },
  info:    { bg: 'bg-white border-l-4 border-brand-500',   ring: 'ring-brand-200',   icon: 'i' },
}

const iconBg: Record<Tone, string> = {
  success: 'bg-success-500',
  error:   'bg-danger-500',
  warning: 'bg-warning-500',
  info:    'bg-brand-500',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const remove = useCallback((id: number) => {
    setItems(prev => prev.filter(t => t.id !== id))
  }, [])

  const show = useCallback((item: Omit<ToastItem, 'id'>) => {
    const id = Date.now() + Math.random()
    const it: ToastItem = { id, duration: 4000, ...item }
    setItems(prev => [...prev, it])
    if (it.duration && it.duration > 0) {
      setTimeout(() => remove(id), it.duration)
    }
  }, [remove])

  const value: ToastContextValue = {
    show,
    success: (title, opts) => show({ tone: 'success', title, ...opts }),
    error:   (title, opts) => show({ tone: 'error',   title, ...opts }),
    warning: (title, opts) => show({ tone: 'warning', title, ...opts }),
    info:    (title, opts) => show({ tone: 'info',    title, ...opts }),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none">
        {items.map(t => {
          const s = toneStyle[t.tone]
          return (
            <div
              key={t.id}
              role="alert"
              className={`pointer-events-auto ${s.bg} rounded-card shadow-pop p-4 animate-slide-up flex items-start gap-3`}
            >
              <div className={`flex-shrink-0 w-6 h-6 rounded-full text-white text-sm font-bold flex items-center justify-center ${iconBg[t.tone]}`}>
                {s.icon}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-ink-900 text-body-sm">{t.title}</p>
                {t.description && (
                  <p className="text-caption text-ink-500 mt-0.5">{t.description}</p>
                )}
              </div>
              <button
                onClick={() => remove(t.id)}
                className="text-ink-400 hover:text-ink-700 text-lg leading-none focus-ring rounded"
                aria-label="關閉"
              >✕</button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
