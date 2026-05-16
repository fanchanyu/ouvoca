/**
 * CRM — 全新 CRM 主頁（Sprint I v3.15）
 *
 * 3 個 tab，學 HubSpot + Salesforce + Pipedrive：
 *  1. 📋 Lead Pipeline — 4 欄漏斗（新進 / 接觸中 / 已驗證 / 失敗）
 *  2. 💼 商機 Kanban — 5 欄階段（探索 / 提案 / 議價 / 成交 / 失敗）
 *  3. 👤 客戶 360 — 選客戶 → 看訂單 / 商機 / 活動時間軸
 *
 * 設計重點：
 *  - 不做 drag-and-drop（複雜，下個 sprint 再說）
 *  - 用「快速階段移動」按鈕代替
 *  - 空狀態走 EmptyState 給 actionable 出路
 */
import { useEffect, useMemo, useState } from 'react'
import {
  apiListLeads, apiCreateLead, apiConvertLead,
  apiListOpps, apiCreateOpp, apiUpdateOppStage,
  apiListCustomers, apiListSOs, apiListCrmEvents, apiCreateCrmEvent,
  type Lead, type Opportunity, type CrmEvent,
  type Customer, type SalesOrder,
} from '../lib/api'
import EmptyState from '../components/EmptyState'

type Tab = 'pipeline' | 'kanban' | 'customer360'

const LEAD_STAGES: { value: string; label: string; color: string }[] = [
  { value: 'new',       label: '🆕 新進',     color: 'border-t-gray-400 bg-gray-50' },
  { value: 'contacted', label: '📞 已接觸',   color: 'border-t-blue-400 bg-blue-50' },
  { value: 'qualified', label: '✅ 已驗證',   color: 'border-t-emerald-400 bg-emerald-50' },
  { value: 'lost',      label: '❌ 失敗',     color: 'border-t-red-400 bg-red-50' },
]

const OPP_STAGES: { value: string; label: string; color: string }[] = [
  { value: 'prospect',    label: '🔍 探索',     color: 'border-t-gray-400 bg-gray-50' },
  { value: 'proposal',    label: '📝 提案',     color: 'border-t-blue-400 bg-blue-50' },
  { value: 'negotiation', label: '🤝 議價',     color: 'border-t-amber-400 bg-amber-50' },
  { value: 'won',         label: '🎉 成交',     color: 'border-t-emerald-400 bg-emerald-50' },
  { value: 'lost',        label: '❌ 失敗',     color: 'border-t-red-400 bg-red-50' },
]

export default function Crm() {
  const [tab, setTab] = useState<Tab>('pipeline')

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">🤝 CRM 客戶關係管理</h1>
          <p className="text-sm text-gray-500 mt-1">
            管理潛在客戶（Lead）、商機追蹤（Opportunity）、客戶 360 視圖
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {[
          { key: 'pipeline' as Tab,   label: '📋 Lead 漏斗' },
          { key: 'kanban' as Tab,     label: '💼 商機 Kanban' },
          { key: 'customer360' as Tab, label: '👤 客戶 360' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={[
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'pipeline' && <LeadPipeline />}
      {tab === 'kanban' && <OpportunityKanban />}
      {tab === 'customer360' && <Customer360 />}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 1. Lead Pipeline
// ────────────────────────────────────────────────────────────
function LeadPipeline() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [newLead, setNewLead] = useState({ company_name: '', contact_person: '', contact_phone: '', source: '' })

  async function load() {
    setLoading(true)
    try { setLeads(await apiListLeads()) }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function createLead() {
    if (!newLead.company_name.trim()) { setErr('公司名稱必填'); return }
    setErr(null)
    try {
      await apiCreateLead(newLead)
      setNewLead({ company_name: '', contact_person: '', contact_phone: '', source: '' })
      setCreating(false)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
  }

  async function convert(lead: Lead) {
    const code = prompt(`轉換 ${lead.company_name} 為客戶\n\n請輸入客戶代碼（例：CUST-${Date.now().toString().slice(-6)}）：`)
    if (!code) return
    try {
      await apiConvertLead(lead.id, { code, name: lead.company_name })
      alert(`✅ 已轉為客戶（代碼 ${code}）`)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '轉換失敗') }
  }

  const grouped = useMemo(() => {
    const g: Record<string, Lead[]> = { new: [], contacted: [], qualified: [], lost: [] }
    for (const l of leads) (g[l.status] || g.new).push(l)
    // 已轉換的算 qualified 的一個變化
    return g
  }, [leads])

  if (loading) return <div className="text-center text-gray-400 py-12">載入中…</div>

  return (
    <div>
      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}

      <div className="flex justify-end mb-4">
        <button
          onClick={() => setCreating(c => !c)}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          {creating ? '取消' : '➕ 新增 Lead'}
        </button>
      </div>

      {creating && (
        <div className="bg-white rounded-lg shadow p-4 mb-4 grid md:grid-cols-4 gap-3">
          <input
            type="text" placeholder="公司名稱（必填）"
            value={newLead.company_name} onChange={(e) => setNewLead({ ...newLead, company_name: e.target.value })}
            className="border rounded px-2 py-1.5 text-sm"
          />
          <input
            type="text" placeholder="聯絡人"
            value={newLead.contact_person} onChange={(e) => setNewLead({ ...newLead, contact_person: e.target.value })}
            className="border rounded px-2 py-1.5 text-sm"
          />
          <input
            type="text" placeholder="電話"
            value={newLead.contact_phone} onChange={(e) => setNewLead({ ...newLead, contact_phone: e.target.value })}
            className="border rounded px-2 py-1.5 text-sm"
          />
          <div className="flex gap-2">
            <input
              type="text" placeholder="來源（展會/介紹/...）"
              value={newLead.source} onChange={(e) => setNewLead({ ...newLead, source: e.target.value })}
              className="border rounded px-2 py-1.5 text-sm flex-1"
            />
            <button onClick={createLead} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
              儲存
            </button>
          </div>
        </div>
      )}

      {leads.length === 0 ? (
        <div className="bg-white rounded-xl shadow">
          <EmptyState
            icon="📋"
            title="還沒有任何 Lead"
            subtitle="Lead = 潛在客戶。從展會 / 廣告 / 介紹來的還沒成交的對象，先記在這裡追蹤。"
            primaryAction={{ label: '➕ 新增第一個 Lead', onClick: () => setCreating(true) }}
            secondaryAction={{ label: '⚙️ 載入示範資料', to: '/settings' }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {LEAD_STAGES.map(stage => (
            <div key={stage.value} className={`rounded-lg border-t-4 ${stage.color} p-3`}>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm">{stage.label}</h3>
                <span className="text-xs px-1.5 py-0.5 rounded-full bg-white text-gray-600 font-mono">
                  {grouped[stage.value].length}
                </span>
              </div>
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {grouped[stage.value].length === 0 ? (
                  <div className="text-xs text-gray-400 italic text-center py-4">空</div>
                ) : (
                  grouped[stage.value].map(l => (
                    <div key={l.id} className="bg-white rounded p-2 shadow-sm border border-gray-100">
                      <div className="font-medium text-sm text-gray-800 truncate" title={l.company_name}>
                        {l.company_name}
                      </div>
                      {l.contact_person && (
                        <div className="text-xs text-gray-500 mt-0.5 truncate">👤 {l.contact_person}</div>
                      )}
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(l.created_at).toLocaleDateString('zh-TW')}
                      </div>
                      {stage.value === 'qualified' && !l.converted_to_customer_id && (
                        <button
                          onClick={() => convert(l)}
                          className="mt-2 w-full px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-xs hover:bg-emerald-200"
                        >
                          🎯 轉為正式客戶
                        </button>
                      )}
                      {l.converted_to_customer_id && (
                        <div className="mt-2 text-xs text-emerald-600 font-medium">✅ 已轉客戶</div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 2. Opportunity Kanban
// ────────────────────────────────────────────────────────────
function OpportunityKanban() {
  const [opps, setOpps] = useState<Opportunity[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [newOpp, setNewOpp] = useState({ customer_id: '', name: '', amount: 0, probability: 50 })

  async function load() {
    setLoading(true)
    try {
      const [o, c] = await Promise.all([apiListOpps(), apiListCustomers().catch(() => [])])
      setOpps(o); setCustomers(c)
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function createOpp() {
    if (!newOpp.customer_id || !newOpp.name) { setErr('客戶 + 商機名稱必填'); return }
    setErr(null)
    try {
      await apiCreateOpp(newOpp)
      setNewOpp({ customer_id: '', name: '', amount: 0, probability: 50 })
      setCreating(false)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
  }

  async function moveStage(opp: Opportunity, newStage: string) {
    try { await apiUpdateOppStage(opp.id, newStage); await load() }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '更新失敗') }
  }

  const grouped = useMemo(() => {
    const g: Record<string, Opportunity[]> = { prospect: [], proposal: [], negotiation: [], won: [], lost: [] }
    for (const o of opps) (g[o.stage] || g.prospect).push(o)
    return g
  }, [opps])

  const totalValue = opps.filter(o => o.status === 'open').reduce((sum, o) => sum + (o.amount * o.probability / 100), 0)
  const customerName = (id: string) => customers.find(c => c.id === id)?.name || id.slice(0, 8)

  if (loading) return <div className="text-center text-gray-400 py-12">載入中…</div>

  return (
    <div>
      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}

      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-600">
          📊 開放商機加權總值：<strong className="text-blue-700 text-base">
            NT$ {totalValue.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}
          </strong>
        </div>
        <button
          onClick={() => setCreating(c => !c)}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          {creating ? '取消' : '➕ 新增商機'}
        </button>
      </div>

      {creating && (
        <div className="bg-white rounded-lg shadow p-4 mb-4 grid md:grid-cols-4 gap-3">
          <select
            value={newOpp.customer_id} onChange={(e) => setNewOpp({ ...newOpp, customer_id: e.target.value })}
            className="border rounded px-2 py-1.5 text-sm"
          >
            <option value="">選客戶</option>
            {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <input
            type="text" placeholder="商機名稱"
            value={newOpp.name} onChange={(e) => setNewOpp({ ...newOpp, name: e.target.value })}
            className="border rounded px-2 py-1.5 text-sm"
          />
          <input
            type="number" placeholder="金額"
            value={newOpp.amount || ''} onChange={(e) => setNewOpp({ ...newOpp, amount: Number(e.target.value) })}
            className="border rounded px-2 py-1.5 text-sm"
          />
          <div className="flex gap-2">
            <input
              type="number" placeholder="勝率 %" min="0" max="100"
              value={newOpp.probability} onChange={(e) => setNewOpp({ ...newOpp, probability: Number(e.target.value) })}
              className="border rounded px-2 py-1.5 text-sm flex-1"
            />
            <button onClick={createOpp} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
              儲存
            </button>
          </div>
        </div>
      )}

      {opps.length === 0 ? (
        <div className="bg-white rounded-xl shadow">
          <EmptyState
            icon="💼"
            title="還沒有任何商機"
            subtitle="商機 = 已有付費意向的客戶機會。把每個業務追蹤中的案子記在這裡，看金額和勝率走勢。"
            primaryAction={{ label: '➕ 新增第一個商機', onClick: () => setCreating(true) }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {OPP_STAGES.map((stage, idx) => (
            <div key={stage.value} className={`rounded-lg border-t-4 ${stage.color} p-3`}>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm">{stage.label}</h3>
                <span className="text-xs px-1.5 py-0.5 rounded-full bg-white text-gray-600 font-mono">
                  {grouped[stage.value].length}
                </span>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                小計 NT$ {grouped[stage.value].reduce((s, o) => s + o.amount, 0).toLocaleString('zh-TW')}
              </div>
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {grouped[stage.value].length === 0 ? (
                  <div className="text-xs text-gray-400 italic text-center py-4">空</div>
                ) : (
                  grouped[stage.value].map(o => (
                    <div key={o.id} className="bg-white rounded p-2 shadow-sm border border-gray-100">
                      <div className="font-medium text-sm text-gray-800 truncate" title={o.name}>{o.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5 truncate">{customerName(o.customer_id)}</div>
                      <div className="flex items-center justify-between mt-1.5">
                        <span className="text-xs font-mono text-gray-700">
                          NT$ {o.amount.toLocaleString('zh-TW')}
                        </span>
                        <span className="text-xs text-blue-600">{o.probability}%</span>
                      </div>
                      {idx < OPP_STAGES.length - 1 && o.status === 'open' && (
                        <div className="flex gap-1 mt-2">
                          {idx > 0 && (
                            <button
                              onClick={() => moveStage(o, OPP_STAGES[idx - 1].value)}
                              className="px-1.5 py-0.5 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                              title="退到上一階段"
                            >←</button>
                          )}
                          <button
                            onClick={() => moveStage(o, OPP_STAGES[idx + 1].value)}
                            className="flex-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 rounded font-medium"
                          >
                            進到 {OPP_STAGES[idx + 1].label} →
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 3. Customer 360
// ────────────────────────────────────────────────────────────
function Customer360() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selected, setSelected] = useState<Customer | null>(null)
  const [orders, setOrders] = useState<SalesOrder[]>([])
  const [opps, setOpps] = useState<Opportunity[]>([])
  const [events, setEvents] = useState<CrmEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      setLoading(true)
      try { setCustomers(await apiListCustomers()) }
      catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
      finally { setLoading(false) }
    })()
  }, [])

  useEffect(() => {
    if (!selected) { setOrders([]); setOpps([]); setEvents([]); return }
    (async () => {
      try {
        const [allOrders, allOpps, ev] = await Promise.all([
          apiListSOs().catch(() => []),
          apiListOpps().catch(() => []),
          apiListCrmEvents(selected.id, 50).catch(() => []),
        ])
        setOrders(allOrders.filter(o => o.customer_id === selected.id))
        setOpps(allOpps.filter(o => o.customer_id === selected.id))
        setEvents(ev)
      } catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
    })()
  }, [selected])

  async function addNote() {
    if (!selected) return
    const subject = prompt('加一筆活動記錄：\n\n主旨（例：電話拜訪 / 報價追蹤）')
    if (!subject) return
    const desc = prompt('內容（選填）') || undefined
    try {
      await apiCreateCrmEvent({
        customer_id: selected.id, event_type: 'note',
        subject, description: desc,
      })
      setEvents(await apiListCrmEvents(selected.id, 50))
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
  }

  if (loading) return <div className="text-center text-gray-400 py-12">載入中…</div>

  if (customers.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow">
        <EmptyState
          icon="👤"
          title="還沒有任何客戶"
          subtitle="先去銷售頁新增客戶，或在 Lead 漏斗轉換 qualified 為正式客戶。"
          primaryAction={{ label: '💰 去銷售頁', to: '/sales' }}
          secondaryAction={{ label: '⚙️ 載入示範資料', to: '/settings' }}
        />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {err && <div className="md:col-span-4 bg-red-50 text-red-700 px-3 py-2 rounded text-sm">{err}</div>}

      {/* 左側客戶清單 */}
      <div className="md:col-span-1 bg-white rounded-xl shadow p-3 max-h-[700px] overflow-y-auto">
        <h3 className="font-semibold text-sm mb-2 px-1">客戶</h3>
        {customers.map(c => (
          <button
            key={c.id} onClick={() => setSelected(c)}
            className={[
              'w-full text-left px-2 py-1.5 rounded text-sm hover:bg-gray-50 transition-colors',
              selected?.id === c.id ? 'bg-blue-50 text-blue-700 font-medium' : '',
            ].join(' ')}
          >
            <div className="truncate">{c.name}</div>
            <div className="text-xs text-gray-400">{c.code}</div>
          </button>
        ))}
      </div>

      {/* 右側 360 視圖 */}
      <div className="md:col-span-3 space-y-4">
        {!selected ? (
          <div className="bg-white rounded-xl shadow">
            <EmptyState icon="👈" title="從左邊選一個客戶" subtitle="會顯示這個客戶的訂單、商機、活動記錄全貌" compact />
          </div>
        ) : (
          <>
            {/* 客戶基本資訊 */}
            <div className="bg-white rounded-xl shadow p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-bold">{selected.name}</h2>
                  <div className="text-xs text-gray-500 mt-1 space-x-3">
                    <span>📋 {selected.code}</span>
                    {selected.grade && <span>⭐ {selected.grade} 級</span>}
                    {selected.contact_person && <span>👤 {selected.contact_person}</span>}
                    {selected.contact_phone && <span>📞 {selected.contact_phone}</span>}
                  </div>
                </div>
                <button onClick={addNote} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                  📝 加活動記錄
                </button>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
                <Stat label="訂單數" value={orders.length} />
                <Stat label="商機數" value={opps.length} />
                <Stat label="活動數" value={events.length} />
              </div>
            </div>

            {/* 訂單 + 商機 + 活動 timeline */}
            <div className="grid md:grid-cols-2 gap-4">
              <SectionList title={`📋 訂單（${orders.length}）`} empty="尚無訂單">
                {orders.slice(0, 10).map(o => (
                  <Item key={o.id} title={o.so_no} sub={`${o.status} · NT$ ${Number(o.total_amount).toLocaleString('zh-TW')}`} />
                ))}
              </SectionList>

              <SectionList title={`💼 商機（${opps.length}）`} empty="尚無商機">
                {opps.map(o => (
                  <Item key={o.id} title={o.name} sub={`${o.stage} · ${o.probability}% · NT$ ${o.amount.toLocaleString('zh-TW')}`} />
                ))}
              </SectionList>
            </div>

            <div className="bg-white rounded-xl shadow p-4">
              <h3 className="font-semibold text-sm mb-3">⏱ 活動時間軸（{events.length}）</h3>
              {events.length === 0 ? (
                <div className="text-xs text-gray-400 text-center py-4">尚無活動記錄，點上方「📝 加活動記錄」</div>
              ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {events.map(e => (
                    <div key={e.id} className="flex gap-3 pb-2 border-b border-gray-100 last:border-0">
                      <div className="text-xs text-gray-400 font-mono whitespace-nowrap">
                        {new Date(e.created_at).toLocaleString('zh-TW', { hour12: false, year: '2-digit', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">
                          <span className="mr-1">{eventIcon(e.event_type)}</span>
                          {e.subject}
                        </div>
                        {e.description && <div className="text-xs text-gray-500 mt-0.5">{e.description}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function eventIcon(type: string): string {
  return { call: '📞', email: '📧', meeting: '🤝', note: '📝', task: '✅' }[type] || '•'
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-50 rounded p-2">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-base font-semibold mt-0.5">{value}</div>
    </div>
  )
}

function SectionList({ title, empty, children }: { title: string; empty: string; children: React.ReactNode }) {
  const arr = Array.isArray(children) ? children : [children].filter(Boolean)
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <h3 className="font-semibold text-sm mb-3">{title}</h3>
      {arr.length === 0 ? (
        <div className="text-xs text-gray-400 text-center py-4">{empty}</div>
      ) : (
        <div className="space-y-1.5 max-h-[200px] overflow-y-auto">{children}</div>
      )}
    </div>
  )
}

function Item({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="text-sm border-l-2 border-blue-200 pl-2 py-1">
      <div className="font-medium truncate">{title}</div>
      <div className="text-xs text-gray-500">{sub}</div>
    </div>
  )
}
