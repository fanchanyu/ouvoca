import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiListSOs, apiListCustomers, apiUpdateCustomer, apiDeleteCustomer,
  apiCancelSO, apiCreateCustomer, apiCreateSO,
  apiConfirmSO, apiShipSO,
  apiListProducts, type Product,
  type SalesOrder, type Customer,
} from '../lib/api'
import EntityRowActions from '../components/EntityRowActions'
import EntityFormModal, { type FieldDef } from '../components/EntityFormModal'
import PrintableDocument, { DocHeader, DocFooter } from '../components/PrintableDocument'

const CUSTOMER_FIELDS: FieldDef[] = [
  { name: 'name', label: '名稱', type: 'text', required: true },
  {
    name: 'grade', label: '分級', type: 'select',
    options: [
      { value: 'A', label: 'A (VIP)' },
      { value: 'B', label: 'B (主力)' },
      { value: 'C', label: 'C (一般)' },
      { value: 'D', label: 'D (低頻)' },
    ],
  },
  { name: 'contact_person', label: '聯絡人', type: 'text' },
  { name: 'contact_phone', label: '電話', type: 'text' },
  { name: 'payment_terms', label: '付款條件', type: 'text' },
  { name: 'credit_limit', label: '信用額度', type: 'number' },
  { name: 'is_active', label: '啟用', type: 'checkbox' },
]

export default function Sales() {
  const [sos, setSos] = useState<SalesOrder[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [editingCust, setEditingCust] = useState<Customer | null>(null)
  const [printSO, setPrintSO] = useState<SalesOrder | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [s, c] = await Promise.all([
        apiListSOs().catch(() => []),
        apiListCustomers().catch(() => []),
      ])
      setSos(s)
      setCustomers(c as Customer[])
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [])

  const totalRevenue = sos.reduce((sum, s) => sum + s.total_amount, 0)

  const cancelSO = async (so: SalesOrder) => {
    const reason = prompt(`取消銷售訂單 ${so.so_no}\n\n請輸入取消原因：`)
    if (reason === null) return
    await apiCancelSO(so.id, reason)
    await load()
  }

  // v3.18：確認單（草稿 → confirmed）
  const confirmSO = async (so: SalesOrder) => {
    if (!confirm(`確認銷售訂單 ${so.so_no}？\n\n之後可出貨。`)) return
    try { await apiConfirmSO(so.id); await load() }
    catch (e: unknown) { alert(e instanceof Error ? e.message : '確認失敗') }
  }

  // v3.18：出貨（自動扣庫存 + 開 AR）
  const shipSO = async (so: SalesOrder) => {
    if (!confirm(`出貨 ${so.so_no}？\n\n動作：① 扣庫存 ② 改狀態為 shipped ③ 自動產 CrmEvent`)) return
    try {
      await apiShipSO(so.id)
      await load()
      alert(`🚚 ${so.so_no} 已出貨`)
    } catch (e: unknown) { alert(e instanceof Error ? e.message : '出貨失敗') }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">銷售管理</h1>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat title="客戶總數" value={customers.length} />
        <Stat title="訂單總數" value={sos.length} />
        <Stat title="累計營收 (TWD)" value={totalRevenue.toLocaleString()} />
      </div>

      {/* v3.17: Quick create bar (Sprint K — 補小白沒 AI 也能建單的能力) */}
      <QuickCreateBar onAfterCreate={load} customers={customers} />

      <div className="bg-white rounded-xl shadow overflow-hidden mb-6">
        <div className="px-4 py-3 bg-gray-50 font-semibold flex items-center justify-between">
          <span>銷售訂單</span>
          <Link to="/chat" className="text-xs text-blue-600 hover:underline">💬 用 AI 建多項目訂單 →</Link>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-t">
            <tr>
              <th className="text-left p-3">訂單號</th>
              <th className="text-left p-3">客戶</th>
              <th className="text-left p-3">狀態</th>
              <th className="text-right p-3">金額</th>
              <th className="text-left p-3">付款</th>
              <th className="text-left p-3">日期</th>
              <th className="text-right p-3 w-32">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : sos.length === 0 ? (
              <tr><td colSpan={7} className="p-4 text-center text-gray-400">尚無訂單</td></tr>
            ) : (
              sos.map(so => (
                <tr key={so.id} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-mono text-xs">{so.so_no}</td>
                  <td className="p-3">{so.customer?.name || so.customer_id}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      so.status === 'cancelled' ? 'bg-red-100 text-red-800' :
                      so.status === 'shipped' ? 'bg-green-100 text-green-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>{so.status}</span>
                  </td>
                  <td className="p-3 text-right">{so.total_amount.toLocaleString()}</td>
                  <td className="p-3"><span className="text-xs text-gray-500">{so.payment_status}</span></td>
                  <td className="p-3 text-xs">{new Date(so.order_date).toLocaleDateString('zh-TW')}</td>
                  <td className="p-3 text-right">
                    <div className="flex gap-1 justify-end">
                      <button onClick={() => setPrintSO(so)}
                        className="px-2 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded"
                        title="列印 PDF（給客戶）">🖨</button>
                      {so.status === 'draft' && (
                        <button onClick={() => confirmSO(so)}
                          className="px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 rounded"
                          title="確認銷售單">✓ 確認</button>
                      )}
                      {['confirmed', 'production', 'ready_to_ship'].includes(so.status) && (
                        <button onClick={() => shipSO(so)}
                          className="px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-50 rounded"
                          title="出貨">📦 出貨</button>
                      )}
                      {!['shipped', 'delivered', 'closed', 'cancelled'].includes(so.status) && (
                        <button onClick={() => cancelSO(so)}
                          className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded"
                          title="取消銷售訂單">🚫</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 font-semibold">客戶</div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-t">
            <tr>
              <th className="text-left p-3">編號</th>
              <th className="text-left p-3">名稱</th>
              <th className="text-center p-3">分級</th>
              <th className="text-right p-3">信用額度</th>
              <th className="text-center p-3">狀態</th>
              <th className="text-right p-3 w-32">操作</th>
            </tr>
          </thead>
          <tbody>
            {customers.length === 0 ? (
              <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無客戶</td></tr>
            ) : (
              customers.map(c => (
                <tr key={c.id} className="border-t">
                  <td className="p-3 font-mono text-xs">{c.code}</td>
                  <td className="p-3">{c.name}</td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      c.grade === 'A' ? 'bg-purple-100 text-purple-800' :
                      c.grade === 'B' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100'
                    }`}>{c.grade}</span>
                  </td>
                  <td className="p-3 text-right">{(c.credit_limit || 0).toLocaleString()}</td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs ${c.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100'}`}>
                      {c.is_active ? '啟用' : '停用'}
                    </span>
                  </td>
                  <td className="p-3">
                    <EntityRowActions
                      entityLabel="客戶"
                      entityName={`${c.code} ${c.name}`}
                      onEdit={() => setEditingCust(c)}
                      onDelete={() => apiDeleteCustomer(c.id)}
                      onAfterDelete={load}
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {editingCust && (
        <EntityFormModal
          title={`編輯客戶 ${editingCust.code}`}
          fields={CUSTOMER_FIELDS}
          initial={editingCust as unknown as Record<string, unknown>}
          onSubmit={(patch) => apiUpdateCustomer(editingCust.id, patch as Partial<Customer>)}
          onClose={() => setEditingCust(null)}
          onSuccess={() => { setEditingCust(null); load() }}
        />
      )}

      {/* v3.21: 列印 SO PDF */}
      {printSO && (
        <PrintableDocument title={`銷售單 ${printSO.so_no}`} onClose={() => setPrintSO(null)}>
          <DocHeader docType="銷售單 Sales Order" docNo={printSO.so_no}
            date={new Date(printSO.order_date).toLocaleDateString('zh-TW')} />
          <table className="w-full text-sm mb-4">
            <tbody>
              <tr><td className="text-gray-600 py-1 w-32">客戶</td><td>{printSO.customer?.name || printSO.customer_id}</td></tr>
              <tr><td className="text-gray-600 py-1">狀態</td>
                <td><span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">{printSO.status}</span></td></tr>
              <tr><td className="text-gray-600 py-1">付款狀態</td><td>{printSO.payment_status}</td></tr>
              <tr><td className="text-gray-600 py-1">金額（含稅）</td><td className="font-bold text-lg text-blue-700">NT$ {printSO.total_amount.toLocaleString()}</td></tr>
              <tr><td className="text-gray-600 py-1">下單日期</td><td>{new Date(printSO.order_date).toLocaleDateString('zh-TW')}</td></tr>
            </tbody>
          </table>
          <div className="text-xs text-gray-500 italic mb-4">
            ※ 完整品項明細請至 erpilot 系統查詢，或請 AI 列出。
          </div>
          <DocFooter note="請確認規格、數量、價格、交期後簽回。" />
        </PrintableDocument>
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

// ────────────────────────────────────────────────────────────
// QuickCreateBar — 新增客戶 + 快速建單（Sprint K v3.17）
// 補上 Sales 頁先前缺的「新增」入口（之前只能靠 AI 對話）
// ────────────────────────────────────────────────────────────
function QuickCreateBar({ onAfterCreate, customers }: {
  onAfterCreate: () => void | Promise<void>
  customers: Customer[]
}) {
  const [mode, setMode] = useState<'closed' | 'customer' | 'so'>('closed')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [cust, setCust] = useState({ code: '', name: '', grade: 'B', contact_person: '', contact_phone: '' })
  const [so, setSo] = useState({ customer_id: '', product_id: '', ordered_qty: 1, unit_price: 0 })

  useEffect(() => {
    if (mode === 'so' && products.length === 0) {
      void apiListProducts().then(setProducts).catch(() => setProducts([]))
    }
  }, [mode])

  async function createCustomer() {
    if (!cust.code.trim() || !cust.name.trim()) { setErr('代碼 + 名稱必填'); return }
    setBusy(true); setErr(null)
    try {
      await apiCreateCustomer(cust)
      setCust({ code: '', name: '', grade: 'B', contact_person: '', contact_phone: '' })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
    finally { setBusy(false) }
  }

  async function createSO() {
    if (!so.customer_id || !so.product_id || so.ordered_qty <= 0) {
      setErr('客戶 + 產品 + 數量必填'); return
    }
    setBusy(true); setErr(null)
    try {
      await apiCreateSO({
        customer_id: so.customer_id,
        items: [{ product_id: so.product_id, ordered_qty: so.ordered_qty, unit_price: so.unit_price }],
      })
      setSo({ customer_id: '', product_id: '', ordered_qty: 1, unit_price: 0 })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '建單失敗') }
    finally { setBusy(false) }
  }

  return (
    <div className="bg-white rounded-xl shadow p-4 mb-6">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm font-medium text-gray-700 mr-2">新增：</span>
        <button onClick={() => setMode(mode === 'customer' ? 'closed' : 'customer')}
          className={`px-3 py-1.5 rounded text-sm transition-colors ${mode === 'customer' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}>
          ➕ 新增客戶
        </button>
        <button onClick={() => setMode(mode === 'so' ? 'closed' : 'so')}
          className={`px-3 py-1.5 rounded text-sm transition-colors ${mode === 'so' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}>
          📝 快速建單（1 項目）
        </button>
        <Link to="/chat" className="px-3 py-1.5 bg-purple-50 text-purple-700 hover:bg-purple-100 rounded text-sm">
          💬 用 AI 建單（多項目）
        </Link>
      </div>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mt-3 text-sm">{err}</div>}

      {mode === 'customer' && (
        <div className="grid md:grid-cols-5 gap-2 mt-3 pt-3 border-t">
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="代碼* 例 CUST-001"
            value={cust.code} onChange={(e) => setCust({ ...cust, code: e.target.value })} />
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="名稱*"
            value={cust.name} onChange={(e) => setCust({ ...cust, name: e.target.value })} />
          <select className="border rounded px-2 py-1.5 text-sm" value={cust.grade}
            onChange={(e) => setCust({ ...cust, grade: e.target.value })}>
            <option value="A">A (VIP)</option><option value="B">B (主力)</option>
            <option value="C">C (一般)</option><option value="D">D (低頻)</option>
          </select>
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="聯絡人"
            value={cust.contact_person} onChange={(e) => setCust({ ...cust, contact_person: e.target.value })} />
          <button onClick={createCustomer} disabled={busy}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {busy ? '儲存中…' : '✓ 儲存'}
          </button>
        </div>
      )}

      {mode === 'so' && (
        <div className="mt-3 pt-3 border-t">
          <div className="grid md:grid-cols-5 gap-2">
            <select className="border rounded px-2 py-1.5 text-sm" value={so.customer_id}
              onChange={(e) => setSo({ ...so, customer_id: e.target.value })}>
              <option value="">選客戶*</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select className="border rounded px-2 py-1.5 text-sm" value={so.product_id}
              onChange={(e) => setSo({ ...so, product_id: e.target.value })}>
              <option value="">選產品*</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.product_no} {p.name}</option>)}
            </select>
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="數量*" min="1"
              value={so.ordered_qty} onChange={(e) => setSo({ ...so, ordered_qty: Number(e.target.value) })} />
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="單價"
              value={so.unit_price || ''} onChange={(e) => setSo({ ...so, unit_price: Number(e.target.value) })} />
            <button onClick={createSO} disabled={busy}
              className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-50">
              {busy ? '建單中…' : '✓ 建單'}
            </button>
          </div>
          {products.length === 0 && (
            <p className="text-xs text-gray-500 mt-2">
              💡 還沒有產品？先去 <Link to="/production" className="text-blue-600 underline">生產頁</Link> 新增產品。
              或<Link to="/settings" className="text-blue-600 underline">⚙️ 設定頁</Link>載入示範資料。
            </p>
          )}
        </div>
      )}
    </div>
  )
}
