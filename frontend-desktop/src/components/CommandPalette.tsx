/**
 * CommandPalette — Cmd+K / Ctrl+K 全系統快速搜尋（Sprint O v3.21）
 *
 * 對標 SAP B1 search bar / Linear / Notion / Raycast
 *
 * 功能：
 *  - 按 Cmd+K（Mac）/ Ctrl+K（Win）開啟
 *  - 模糊搜尋 customers / suppliers / parts / products / SO / PO / WO / leads
 *  - 分組顯示結果（最多每組 5 筆）
 *  - 鍵盤 ↑↓ Enter 導航；ESC 關閉
 *  - 點結果 → 跳到對應頁
 *  - 也支援快速命令：「new sales」「load demo」「ai chat」
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  apiListCustomers, apiListSuppliers, apiListParts,
  apiListProducts, apiListSOs, apiListPOs, apiListWOs, apiListLeads,
  type Customer, type Supplier, type Part, type Product,
  type SalesOrder, type PurchaseOrder, type ProductionOrder, type Lead,
} from '../lib/api'

interface CommandItem {
  id: string
  icon: string
  category: string
  primary: string
  secondary?: string
  to: string
}

const QUICK_COMMANDS: CommandItem[] = [
  { id: 'cmd-chat',       icon: '💬', category: '⚡ 快速命令', primary: 'AI 助手對話',           to: '/chat' },
  { id: 'cmd-crm',        icon: '🤝', category: '⚡ 快速命令', primary: 'CRM Lead 漏斗',         to: '/crm' },
  { id: 'cmd-accounting', icon: '📒', category: '⚡ 快速命令', primary: '會計（傳票 / AR）',     to: '/accounting' },
  { id: 'cmd-einvoice',   icon: '🧾', category: '⚡ 快速命令', primary: '開立電子發票',          to: '/einvoice' },
  { id: 'cmd-reports',    icon: '📈', category: '⚡ 快速命令', primary: '報表中心',              to: '/reports' },
  { id: 'cmd-settings',   icon: '⚙️', category: '⚡ 快速命令', primary: '設定（AI Key / 示範資料 / 上傳）', to: '/settings' },
  { id: 'cmd-inv',        icon: '📦', category: '⚡ 快速命令', primary: '庫存管理',              to: '/inventory' },
  { id: 'cmd-purchase',   icon: '🛒', category: '⚡ 快速命令', primary: '採購管理',              to: '/purchase' },
  { id: 'cmd-sales',      icon: '💰', category: '⚡ 快速命令', primary: '銷售管理',              to: '/sales' },
  { id: 'cmd-production', icon: '🏭', category: '⚡ 快速命令', primary: '生產管理',              to: '/production' },
]

export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<CommandItem[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  // Cmd/Ctrl + K to toggle
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(o => !o)
      } else if (e.key === 'Escape') {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
    else { setQuery(''); setItems([]); setActiveIndex(0) }
  }, [open])

  // Load all entities lazily once open
  useEffect(() => {
    if (!open) return
    setLoading(true)
    Promise.all([
      apiListCustomers().catch(() => [] as Customer[]),
      apiListSuppliers().catch(() => [] as Supplier[]),
      apiListParts().catch(() => [] as Part[]),
      apiListProducts().catch(() => [] as Product[]),
      apiListSOs().catch(() => [] as SalesOrder[]),
      apiListPOs().catch(() => [] as PurchaseOrder[]),
      apiListWOs().catch(() => [] as ProductionOrder[]),
      apiListLeads().catch(() => [] as Lead[]),
    ]).then(([customers, suppliers, parts, products, sos, pos, wos, leads]) => {
      const all: CommandItem[] = [
        ...QUICK_COMMANDS,
        ...customers.map(c => ({
          id: `cust-${c.id}`, icon: '👤', category: '👤 客戶',
          primary: c.name, secondary: c.code, to: '/sales',
        })),
        ...suppliers.map(s => ({
          id: `sup-${s.id}`, icon: '🏭', category: '🏭 供應商',
          primary: s.name, secondary: s.code, to: '/purchase',
        })),
        ...parts.map(p => ({
          id: `part-${p.id}`, icon: '📦', category: '📦 料件',
          primary: p.name, secondary: p.part_no, to: '/inventory',
        })),
        ...products.map(p => ({
          id: `prod-${p.id}`, icon: '🏷', category: '🏷 產品',
          primary: p.name, secondary: p.product_no, to: '/production',
        })),
        ...sos.map(s => ({
          id: `so-${s.id}`, icon: '💰', category: '💰 銷售單',
          primary: s.so_no, secondary: `${s.status} · NT$ ${s.total_amount.toLocaleString()}`,
          to: '/sales',
        })),
        ...pos.map(p => ({
          id: `po-${p.id}`, icon: '🛒', category: '🛒 採購單',
          primary: p.po_no, secondary: `${p.status} · NT$ ${p.total_amount.toLocaleString()}`,
          to: '/purchase',
        })),
        ...wos.map(w => ({
          id: `wo-${w.id}`, icon: '🏭', category: '🏭 工單',
          primary: w.wo_no, secondary: `${w.status} · ${w.completed_qty}/${w.ordered_qty}`,
          to: '/production',
        })),
        ...leads.map(l => ({
          id: `lead-${l.id}`, icon: '🆕', category: '🆕 Lead',
          primary: l.company_name, secondary: `${l.status}`,
          to: '/crm',
        })),
      ]
      setItems(all)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [open])

  // Fuzzy filter
  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    if (!q) return items.filter(i => i.category === '⚡ 快速命令').slice(0, 10)
    return items.filter(i =>
      i.primary.toLowerCase().includes(q) ||
      (i.secondary || '').toLowerCase().includes(q) ||
      i.category.toLowerCase().includes(q)
    ).slice(0, 30)
  }, [items, query])

  // Group by category, preserve order
  const grouped = useMemo(() => {
    const map = new Map<string, CommandItem[]>()
    for (const item of filtered) {
      const arr = map.get(item.category) || []
      arr.push(item); map.set(item.category, arr)
    }
    return Array.from(map.entries()).map(([cat, list]) => ({ category: cat, items: list.slice(0, 5) }))
  }, [filtered])

  const flatItems = useMemo(() => grouped.flatMap(g => g.items), [grouped])

  useEffect(() => { setActiveIndex(0) }, [query])

  function pick(item: CommandItem) {
    navigate(item.to)
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(i => Math.min(i + 1, flatItems.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (flatItems[activeIndex]) pick(flatItems[activeIndex])
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center pt-[15vh] p-4"
      onClick={() => setOpen(false)}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[70vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-2 border-b border-gray-100 p-3">
          <span className="text-gray-400 text-lg">🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="搜尋客戶 / 供應商 / 料件 / 訂單 / 命令…"
            className="flex-1 outline-none text-sm"
          />
          <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-xs text-gray-500 font-mono">ESC</kbd>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto">
          {loading && items.length === 0 ? (
            <div className="text-center text-gray-400 text-sm py-12">載入索引中…</div>
          ) : flatItems.length === 0 ? (
            <div className="text-center text-gray-400 text-sm py-12">
              {query ? `「${query}」沒結果` : '開始輸入搜尋…'}
            </div>
          ) : (
            <div className="py-2">
              {grouped.map(group => (
                <div key={group.category} className="mb-1">
                  <div className="px-3 py-1 text-xs text-gray-500 font-medium">{group.category}</div>
                  {group.items.map(item => {
                    const flatIdx = flatItems.indexOf(item)
                    const active = flatIdx === activeIndex
                    return (
                      <button
                        key={item.id}
                        onClick={() => pick(item)}
                        onMouseEnter={() => setActiveIndex(flatIdx)}
                        className={`w-full text-left px-3 py-2 flex items-center gap-3 ${active ? 'bg-blue-50' : 'hover:bg-gray-50'} transition-colors`}
                      >
                        <span className="text-base">{item.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-gray-800 truncate">{item.primary}</div>
                          {item.secondary && (
                            <div className="text-xs text-gray-500 truncate font-mono">{item.secondary}</div>
                          )}
                        </div>
                        {active && <span className="text-xs text-blue-600">↵ 開啟</span>}
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer hint */}
        <div className="border-t border-gray-100 px-3 py-2 text-xs text-gray-500 flex items-center justify-between bg-gray-50">
          <div>
            <kbd className="bg-white border border-gray-200 px-1.5 rounded font-mono">↑↓</kbd> 移動 ·
            <kbd className="bg-white border border-gray-200 px-1.5 rounded font-mono ml-1">↵</kbd> 開啟 ·
            <kbd className="bg-white border border-gray-200 px-1.5 rounded font-mono ml-1">ESC</kbd> 關閉
          </div>
          <div className="hidden md:block">
            隨時按 <kbd className="bg-white border border-gray-200 px-1.5 rounded font-mono">Ctrl K</kbd> 開啟
          </div>
        </div>
      </div>
    </div>
  )
}
