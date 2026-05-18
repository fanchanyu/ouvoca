import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiListPOs, apiListSuppliers, apiUpdateSupplier, apiDeleteSupplier,
  apiCancelPO, apiCreateSupplier, apiCreatePO,
  apiListParts, type Part,
  type PurchaseOrder, type Supplier,
} from '../lib/api'
import EntityRowActions from '../components/EntityRowActions'
import EntityFormModal, { type FieldDef } from '../components/EntityFormModal'

const SUPPLIER_FIELDS: FieldDef[] = [
  { name: 'name', label: '名稱', type: 'text', required: true },
  {
    name: 'tier', label: '等級', type: 'select',
    options: [
      { value: 'T1', label: 'T1 (策略)' },
      { value: 'T2', label: 'T2 (主力)' },
      { value: 'T3', label: 'T3 (一般)' },
    ],
  },
  { name: 'contact_person', label: '聯絡人', type: 'text' },
  { name: 'contact_phone', label: '電話', type: 'text' },
  { name: 'payment_terms', label: '付款條件', type: 'text' },
  { name: 'is_approved', label: '已核准', type: 'checkbox' },
  { name: 'is_active', label: '啟用', type: 'checkbox' },
]

export default function Purchase() {
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [tab, setTab] = useState<'orders' | 'suppliers'>('orders')
  const [editingSup, setEditingSup] = useState<Supplier | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [p, s] = await Promise.all([apiListPOs(filterStatus || undefined), apiListSuppliers()])
      setPos(p); setSuppliers(s)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [filterStatus])

  const cancelPO = async (po: PurchaseOrder) => {
    const reason = prompt(`取消採購單 ${po.po_no}\n\n請輸入取消原因：`)
    if (reason === null) return
    await apiCancelPO(po.id, reason)
    await load()
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">採購管理</h1>
        <div className="flex gap-3 items-center">
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setTab('orders')}
              className={`px-3 py-1.5 text-sm rounded ${tab === 'orders' ? 'bg-white shadow' : 'text-gray-500'}`}
            >📋 採購單</button>
            <button
              onClick={() => setTab('suppliers')}
              className={`px-3 py-1.5 text-sm rounded ${tab === 'suppliers' ? 'bg-white shadow' : 'text-gray-500'}`}
            >🏭 供應商</button>
          </div>
          {tab === 'orders' && (
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
              <option value="">全部狀態</option>
              <option value="draft">草稿</option>
              <option value="approved">已核准</option>
              <option value="sent">已發送</option>
              <option value="received">已收貨</option>
              <option value="partial_received">部分收貨</option>
              <option value="cancelled">已取消</option>
            </select>
          )}
        </div>
      </div>

      {/* v3.17: Quick create bar (Sprint K) */}
      <PurchaseQuickCreateBar suppliers={suppliers} onAfterCreate={load} />

      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat title="供應商總數" value={suppliers.length} />
        <Stat title="採購單總數" value={pos.length} />
        <Stat title="總金額 (TWD)" value={pos.reduce((sum, p) => sum + p.total_amount, 0).toLocaleString()} />
      </div>

      {tab === 'orders' ? (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">採購單號</th>
                <th className="text-left p-3">供應商</th>
                <th className="text-left p-3">狀態</th>
                <th className="text-right p-3">金額</th>
                <th className="text-left p-3">下單日期</th>
                <th className="text-right p-3 w-32">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">載入中…</td></tr>
              ) : pos.length === 0 ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無採購單資料</td></tr>
              ) : (
                pos.map(po => (
                  <tr key={po.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{po.po_no}</td>
                    <td className="p-3">{po.supplier?.name || po.supplier_id}</td>
                    <td className="p-3"><StatusBadge status={po.status} /></td>
                    <td className="p-3 text-right">{po.total_amount.toLocaleString()}</td>
                    <td className="p-3">{new Date(po.order_date).toLocaleDateString('zh-TW')}</td>
                    <td className="p-3 text-right">
                      {!['received', 'cancelled'].includes(po.status) && (
                        <button
                          onClick={() => cancelPO(po)}
                          className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded"
                          title="取消採購單"
                        >🚫 取消</button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">編號</th>
                <th className="text-left p-3">名稱</th>
                <th className="text-left p-3">等級</th>
                <th className="text-center p-3">已核准</th>
                <th className="text-center p-3">狀態</th>
                <th className="text-right p-3 w-32">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">載入中…</td></tr>
              ) : suppliers.length === 0 ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無供應商資料</td></tr>
              ) : (
                suppliers.map(s => (
                  <tr key={s.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{s.code}</td>
                    <td className="p-3">{s.name}</td>
                    <td className="p-3">{s.tier}</td>
                    <td className="p-3 text-center">{s.is_approved ? '✅' : '—'}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${s.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100'}`}>
                        {s.is_active ? '啟用' : '停用'}
                      </span>
                    </td>
                    <td className="p-3">
                      <EntityRowActions
                        entityLabel="供應商"
                        entityName={`${s.code} ${s.name}`}
                        onEdit={() => setEditingSup(s)}
                        onDelete={() => apiDeleteSupplier(s.id)}
                        onAfterDelete={load}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {editingSup && (
        <EntityFormModal
          title={`編輯供應商 ${editingSup.code}`}
          fields={SUPPLIER_FIELDS}
          initial={editingSup as unknown as Record<string, unknown>}
          onSubmit={(patch) => apiUpdateSupplier(editingSup.id, patch as Partial<Supplier>)}
          onClose={() => setEditingSup(null)}
          onSuccess={() => { setEditingSup(null); load() }}
        />
      )}
    </div>
  )
}

function Stat({ title, value }: { title: string; value: number | string }) {
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    approved: 'bg-blue-100 text-blue-800',
    sent: 'bg-purple-100 text-purple-800',
    received: 'bg-green-100 text-green-800',
    partial_received: 'bg-yellow-100 text-yellow-800',
    cancelled: 'bg-red-100 text-red-800',
  }
  return <span className={`px-2 py-1 rounded-full text-xs ${m[status] || 'bg-gray-100'}`}>{status}</span>
}

// ────────────────────────────────────────────────────────────
// Quick create bar — 新增供應商 + 快速建採購單（Sprint K v3.17）
// ────────────────────────────────────────────────────────────
function PurchaseQuickCreateBar({ suppliers, onAfterCreate }: {
  suppliers: Supplier[]
  onAfterCreate: () => void | Promise<void>
}) {
  const [mode, setMode] = useState<'closed' | 'supplier' | 'po'>('closed')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [parts, setParts] = useState<Part[]>([])
  const [sup, setSup] = useState({ code: '', name: '', tier: 'T2', lead_time_days: 7 })
  const [po, setPo] = useState({ supplier_id: '', part_id: '', ordered_qty: 1, unit_price: 0 })

  useEffect(() => {
    if (mode === 'po' && parts.length === 0) {
      void apiListParts().then(setParts).catch(() => setParts([]))
    }
  }, [mode])

  async function createSupplier() {
    if (!sup.code.trim() || !sup.name.trim()) { setErr('代碼 + 名稱必填'); return }
    setBusy(true); setErr(null)
    try {
      await apiCreateSupplier({ ...sup, is_approved: true })
      setSup({ code: '', name: '', tier: 'T2', lead_time_days: 7 })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
    finally { setBusy(false) }
  }

  async function createPO() {
    if (!po.supplier_id || !po.part_id || po.ordered_qty <= 0) {
      setErr('供應商 + 料件 + 數量必填'); return
    }
    setBusy(true); setErr(null)
    try {
      await apiCreatePO({
        supplier_id: po.supplier_id,
        items: [{ part_id: po.part_id, ordered_qty: po.ordered_qty, unit_price: po.unit_price }],
      })
      setPo({ supplier_id: '', part_id: '', ordered_qty: 1, unit_price: 0 })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '建單失敗') }
    finally { setBusy(false) }
  }

  return (
    <div className="bg-white rounded-xl shadow p-4 mb-6">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm font-medium text-gray-700 mr-2">新增：</span>
        <button onClick={() => setMode(mode === 'supplier' ? 'closed' : 'supplier')}
          className={`px-3 py-1.5 rounded text-sm ${mode === 'supplier' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}>
          ➕ 新增供應商
        </button>
        <button onClick={() => setMode(mode === 'po' ? 'closed' : 'po')}
          className={`px-3 py-1.5 rounded text-sm ${mode === 'po' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}>
          🛒 快速建採購單（1 項目）
        </button>
        <Link to="/chat" className="px-3 py-1.5 bg-purple-50 text-purple-700 hover:bg-purple-100 rounded text-sm">
          💬 用 AI 建多項目採購單
        </Link>
      </div>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mt-3 text-sm">{err}</div>}

      {mode === 'supplier' && (
        <div className="grid md:grid-cols-5 gap-2 mt-3 pt-3 border-t">
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="代碼* 例 SUP-001"
            value={sup.code} onChange={(e) => setSup({ ...sup, code: e.target.value })} />
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="名稱*"
            value={sup.name} onChange={(e) => setSup({ ...sup, name: e.target.value })} />
          <select className="border rounded px-2 py-1.5 text-sm" value={sup.tier}
            onChange={(e) => setSup({ ...sup, tier: e.target.value })}>
            <option value="T1">T1 (策略)</option>
            <option value="T2">T2 (主力)</option>
            <option value="T3">T3 (一般)</option>
          </select>
          <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="交期天數" min="1"
            value={sup.lead_time_days} onChange={(e) => setSup({ ...sup, lead_time_days: Number(e.target.value) })} />
          <button onClick={createSupplier} disabled={busy}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {busy ? '儲存中…' : '✓ 儲存'}
          </button>
        </div>
      )}

      {mode === 'po' && (
        <div className="mt-3 pt-3 border-t">
          <div className="grid md:grid-cols-5 gap-2">
            <select className="border rounded px-2 py-1.5 text-sm" value={po.supplier_id}
              onChange={(e) => setPo({ ...po, supplier_id: e.target.value })}>
              <option value="">選供應商*</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select className="border rounded px-2 py-1.5 text-sm" value={po.part_id}
              onChange={(e) => setPo({ ...po, part_id: e.target.value })}>
              <option value="">選料件*</option>
              {parts.map(p => <option key={p.id} value={p.id}>{p.part_no} {p.name}</option>)}
            </select>
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="數量*" min="1"
              value={po.ordered_qty} onChange={(e) => setPo({ ...po, ordered_qty: Number(e.target.value) })} />
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="單價"
              value={po.unit_price || ''} onChange={(e) => setPo({ ...po, unit_price: Number(e.target.value) })} />
            <button onClick={createPO} disabled={busy}
              className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-50">
              {busy ? '建單中…' : '✓ 建單'}
            </button>
          </div>
          {parts.length === 0 && (
            <p className="text-xs text-gray-500 mt-2">
              💡 還沒有料件？先去 <Link to="/inventory" className="text-blue-600 underline">庫存頁</Link> 新增。
            </p>
          )}
        </div>
      )}
    </div>
  )
}
