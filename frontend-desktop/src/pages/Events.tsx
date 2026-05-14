import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '../store/auth'

interface DomainEvent {
  name: string
  domain: string
  entity_type: string
  entity_id: string
  data: Record<string, unknown>
  ts: string
}

const DOMAIN_COLORS: Record<string, string> = {
  inventory: 'bg-blue-100 text-blue-800',
  purchase: 'bg-purple-100 text-purple-800',
  production: 'bg-green-100 text-green-800',
  quality: 'bg-red-100 text-red-800',
  sales: 'bg-amber-100 text-amber-800',
  accounting: 'bg-indigo-100 text-indigo-800',
  warehouse: 'bg-cyan-100 text-cyan-800',
  crm: 'bg-pink-100 text-pink-800',
  mps_mrp: 'bg-slate-100 text-slate-800',
}

export default function EventsPage() {
  const [events, setEvents] = useState<DomainEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [filter, setFilter] = useState('')
  const sseRef = useRef<EventSource | null>(null)
  const token = useAuthStore(s => s.token)

  useEffect(() => {
    // SSE doesn't support custom Authorization headers; we open the URL plain.
    // Backend's /api/events/stream is public (anyone can subscribe to the stream).
    const es = new EventSource('/api/events/stream')
    sseRef.current = es

    es.addEventListener('open', () => setConnected(true))

    es.addEventListener('error', () => setConnected(false))

    const generic = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data) as Omit<DomainEvent, 'name'>
        setEvents(prev => [{ name: (ev as MessageEvent & { type: string }).type, ...data }, ...prev].slice(0, 200))
      } catch {/* ignore */}
    }

    // Subscribe to a number of known event names
    const names = [
      'inventory.changed', 'stock.below_safety', 'po.created', 'po.approved', 'po.received',
      'wo.created', 'wo.released', 'wo.completed', 'so.created', 'so.confirmed', 'so.shipped',
      'quality.inspected', 'nc.created', 'capa.created',
      'journal.created', 'journal.posted', 'month.end_close',
      'mrp.generated', 'pick.created', 'pick.completed',
      'lead.converted', 'opportunity.stage_changed',
    ]
    names.forEach(n => es.addEventListener(n, generic as EventListener))

    return () => { es.close() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const filtered = filter ? events.filter(e => e.name.includes(filter) || e.domain.includes(filter)) : events

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">即時事件流</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">{connected ? '已連線' : '未連線'}</span>
          </div>
          <input
            type="text" placeholder="過濾事件名稱…"
            value={filter} onChange={e => setFilter(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <div className="max-h-[calc(100vh-200px)] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              {connected ? '等待事件中…（試試在其他頁面操作來觸發）' : '尚未連線到事件流'}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left p-3">時間</th>
                  <th className="text-left p-3">領域</th>
                  <th className="text-left p-3">事件</th>
                  <th className="text-left p-3">實體</th>
                  <th className="text-left p-3">資料</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e, i) => (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="p-2 font-mono text-xs text-gray-500">
                      {new Date(e.ts).toLocaleTimeString('zh-TW', { hour12: false })}
                    </td>
                    <td className="p-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${DOMAIN_COLORS[e.domain] || 'bg-gray-100'}`}>
                        {e.domain}
                      </span>
                    </td>
                    <td className="p-2 font-mono text-xs">{e.name}</td>
                    <td className="p-2 text-xs">{e.entity_type}</td>
                    <td className="p-2 font-mono text-xs text-gray-600 max-w-md truncate">
                      {JSON.stringify(e.data)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
