/**
 * DesktopNotifications — v3.3 桌機 Toast 通知（Browser Notification + SSE）。
 *
 * 訂閱 /api/events/stream，把 critical 事件轉成桌面通知：
 *   - inventory.below_safety  → 「⚠️ M6 螺絲低於安全庫存」
 *   - so.created              → 「📥 新訂單 SO-XXX，金額 $1000」
 *   - so.shipped              → 「🚚 SO-XXX 已出貨」
 *   - po.received             → 「✅ PO-XXX 已收貨」
 *   - wo.completed            → 「🏁 WO-XXX 已完工」
 *
 * 設計：see ROADMAP Phase 3 G-301。
 *
 * 整合方式：在 App.tsx 或 Layout 內放 <DesktopNotifications /> 元件即可。
 */
import { useEffect, useRef, useState } from 'react'

interface SseEvent {
  event: string
  data: string
}

interface NotificationRule {
  eventPrefix: string                         // 「inventory.below_safety」「so.created」
  build: (data: Record<string, unknown>) => { title: string; body: string; icon?: string } | null
}

/**
 * 通知規則：把 backend domain event payload 轉成桌面通知內容。
 * 順序：先 match 的優先。
 */
const RULES: NotificationRule[] = [
  {
    eventPrefix: 'inventory.below_safety',
    build: (d) => ({
      title: '⚠️ 庫存低於安全水位',
      body: `${d.part_no || '?'}：剩 ${d.qty_available ?? '?'} / 安全 ${d.safety_stock ?? '?'}`,
    }),
  },
  {
    eventPrefix: 'inventory.changed',
    build: (d) => {
      // 只通知大量出入庫（避免 spam）
      if (typeof d.qty === 'number' && d.qty >= 100) {
        return {
          title: `📦 庫存變動 ${d.type}`,
          body: `${d.part_id || ''} ${d.qty}（在手 ${d.qty_on_hand}）`,
        }
      }
      return null
    },
  },
  {
    eventPrefix: 'so.created',
    build: (d) => ({
      title: '📥 新銷售訂單',
      body: `${d.so_no || '?'}  金額 $${Number(d.total || 0).toLocaleString()}`,
    }),
  },
  {
    eventPrefix: 'so.shipped',
    build: (d) => ({
      title: '🚚 訂單已出貨',
      body: `${d.so_no || '?'}  金額 $${Number(d.total_amount || 0).toLocaleString()}`,
    }),
  },
  {
    eventPrefix: 'po.received',
    build: (d) => ({
      title: '✅ 採購已收貨',
      body: `${d.po_no || '?'}（狀態 ${d.status}）`,
    }),
  },
  {
    eventPrefix: 'po.created',
    build: (d) => ({
      title: '🛒 新採購單',
      body: `${d.po_no || '?'}  金額 $${Number(d.total || 0).toLocaleString()}`,
    }),
  },
  {
    eventPrefix: 'wo.completed',
    build: (d) => ({
      title: '🏁 工單完工',
      body: `${d.wo_no || '?'}  完工 ${d.completed_qty} 件`,
    }),
  },
  {
    eventPrefix: 'stock.below_safety',
    build: (d) => ({
      title: '⚠️ 安全庫存警報',
      body: `${d.part_no || '?'}：可用 ${d.qty_available} / 安全 ${d.safety_stock}`,
    }),
  },
]


/**
 * In-memory toast log（給 UI 顯示「最近 10 則通知」用）。
 */
export interface ToastEntry {
  id: number
  title: string
  body: string
  ts: number
  eventName: string
}


/**
 * 元件 props：可選 callback 讓父層拿到新通知，整合 in-app toast banner。
 */
interface Props {
  onToast?: (entry: ToastEntry) => void
  /** 是否要求 Notification 權限（預設 true） */
  requestPermission?: boolean
}


export default function DesktopNotifications({
  onToast,
  requestPermission = true,
}: Props) {
  const [status, setStatus] = useState<'idle' | 'connected' | 'denied' | 'unsupported'>('idle')
  const [count, setCount] = useState(0)
  const idRef = useRef(0)

  useEffect(() => {
    // 1. 確認瀏覽器支援
    if (typeof Notification === 'undefined') {
      setStatus('unsupported')
      console.warn('[DesktopNotifications] Browser does not support Notification API')
      return
    }

    // 2. 要求權限
    if (requestPermission && Notification.permission === 'default') {
      void Notification.requestPermission()
    }
    if (Notification.permission === 'denied') {
      setStatus('denied')
    }

    // 3. 開 SSE
    // 注意：EventSource 不能帶 Authorization header（瀏覽器限制）
    // 若需要 auth，要靠 cookie 或 query param token。Demo 階段 SSE 是 public。
    const es = new EventSource('/api/events/stream')

    es.onopen = () => {
      setStatus('connected')
      console.log('[DesktopNotifications] SSE connected')
    }

    es.onerror = (e) => {
      console.warn('[DesktopNotifications] SSE error', e)
      // EventSource auto-reconnects on its own
    }

    // 通用 message handler — 訂閱所有 named events
    const handleEvent = (eventName: string, raw: string) => {
      let data: Record<string, unknown> = {}
      try {
        const parsed = JSON.parse(raw)
        data = (parsed.data || parsed) as Record<string, unknown>
      } catch {
        return
      }
      // 找匹配的 rule
      const rule = RULES.find((r) => eventName.startsWith(r.eventPrefix))
      if (!rule) return
      const content = rule.build(data)
      if (!content) return

      // 觸發桌面通知
      if (Notification.permission === 'granted') {
        try {
          new Notification(content.title, { body: content.body, tag: eventName })
        } catch (err) {
          console.warn('[DesktopNotifications] notify failed:', err)
        }
      }

      // 給父層 in-app toast 用
      idRef.current += 1
      const entry: ToastEntry = {
        id: idRef.current,
        title: content.title,
        body: content.body,
        ts: Date.now(),
        eventName,
      }
      onToast?.(entry)
      setCount((c) => c + 1)
    }

    // 監聽 backend 的 named events（不是 'message'）
    const watched = RULES.map((r) => r.eventPrefix)
    // SSE 的 event name 是固定字串，所以對每個前綴的「精確 name」都註冊
    const exactNames = [
      'inventory.below_safety', 'inventory.changed',
      'so.created', 'so.shipped', 'so.confirmed',
      'po.created', 'po.received', 'po.approved',
      'wo.completed', 'wo.released', 'wo.created',
      'stock.below_safety',
    ]
    const listeners: Array<[string, (e: MessageEvent) => void]> = []
    for (const name of exactNames) {
      const fn = (e: MessageEvent) => handleEvent(name, e.data as string)
      es.addEventListener(name, fn as EventListener)
      listeners.push([name, fn])
    }
    void watched  // suppress unused

    return () => {
      for (const [name, fn] of listeners) {
        es.removeEventListener(name, fn as EventListener)
      }
      es.close()
    }
  }, [onToast, requestPermission])

  // 元件本身不畫東西（純背景訂閱），但 export status 給 debug 用
  // 父層可以靠 onToast callback 顯示 in-app banner
  if (import.meta.env.DEV) {
    return (
      <div className="fixed bottom-2 right-2 px-2 py-1 text-xs text-gray-400 bg-white/70 rounded shadow z-50 pointer-events-none">
        🔔 {status} · {count} notif
      </div>
    )
  }
  return null
}
