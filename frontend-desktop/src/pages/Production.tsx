import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiListWOs, apiReleaseWO, apiCancelWO,
  apiListProducts, apiCreateProduct, apiCreateWO,
  type ProductionOrder, type Product,
} from '../lib/api'

export default function Production() {
  const [wos, setWos] = useState<ProductionOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try { setWos(await apiListWOs()) } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function release(id: string) {
    setError(null)
    try { await apiReleaseWO(id); load() }
    catch (e: unknown) { setError(e instanceof Error ? e.message : '釋放失敗') }
  }

  async function cancel(wo: ProductionOrder) {
    const reason = prompt(`取消工單 ${wo.wo_no}\n\n請輸入取消原因：`)
    if (reason === null) return
    setError(null)
    try { await apiCancelWO(wo.id, reason); load() }
    catch (e: unknown) { setError(e instanceof Error ? e.message : '取消失敗') }
  }

  const inProgress = wos.filter(w => w.status === 'released' || w.status === 'in_progress').length
  const completed = wos.filter(w => w.status === 'completed').length
  const draft = wos.filter(w => w.status === 'draft').length

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">生產管理</h1>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg mb-4 text-sm">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Stat title="進行中工單" value={inProgress} color="blue" />
        <Stat title="已完成工單" value={completed} color="green" />
        <Stat title="待釋放工單" value={draft} color="yellow" />
      </div>

      {/* v3.17: Quick create bar (Sprint K) */}
      <ProductionQuickCreateBar onAfterCreate={load} />

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">工單號</th>
              <th className="text-left p-3">狀態</th>
              <th className="text-right p-3">訂單量</th>
              <th className="text-right p-3">完工量</th>
              <th className="text-right p-3">不良量</th>
              <th className="text-right p-3">進度</th>
              <th className="text-center p-3">動作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : wos.length === 0 ? (
              <tr><td colSpan={7} className="p-4 text-center text-gray-400">尚無工單</td></tr>
            ) : (
              wos.map(w => {
                const pct = w.ordered_qty > 0 ? Math.round((w.completed_qty / w.ordered_qty) * 100) : 0
                return (
                  <tr key={w.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{w.wo_no}</td>
                    <td className="p-3"><StatusBadge status={w.status} /></td>
                    <td className="p-3 text-right">{w.ordered_qty}</td>
                    <td className="p-3 text-right">{w.completed_qty}</td>
                    <td className="p-3 text-right text-red-600">{w.rejected_qty}</td>
                    <td className="p-3 text-right">{pct}%</td>
                    <td className="p-3 text-center">
                      <div className="flex gap-1 justify-center">
                        {w.status === 'draft' && (
                          <button onClick={() => release(w.id)} className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700">釋放</button>
                        )}
                        {!['completed', 'cancelled'].includes(w.status) && (
                          <button onClick={() => cancel(w)} className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded" title="取消工單">🚫 取消</button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Stat({ title, value, color }: { title: string; value: number; color: string }) {
  const m: Record<string, string> = { blue: 'border-blue-500', green: 'border-green-500', yellow: 'border-yellow-500' }
  return (
    <div className={`bg-white rounded-xl shadow p-6 border-l-4 ${m[color]}`}>
      <div className="text-gray-500 text-sm">{title}</div>
      <div className="text-3xl font-bold mt-1">{value}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    released: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-green-100 text-green-800',
    completed: 'bg-emerald-100 text-emerald-800',
    cancelled: 'bg-red-100 text-red-800',
  }
  return <span className={`px-2 py-1 rounded-full text-xs ${m[status] || 'bg-gray-100'}`}>{status}</span>
}

// ────────────────────────────────────────────────────────────
// Quick create bar — 新增產品 + 快速建工單（Sprint K v3.17）
// ────────────────────────────────────────────────────────────
function ProductionQuickCreateBar({ onAfterCreate }: {
  onAfterCreate: () => void | Promise<void>
}) {
  const [mode, setMode] = useState<'closed' | 'product' | 'wo'>('closed')
  const [products, setProducts] = useState<Product[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [prod, setProd] = useState({ product_no: '', name: '' })
  const [wo, setWo] = useState({ product_id: '', ordered_qty: 1, priority: 50 })

  async function loadProducts() {
    try { setProducts(await apiListProducts()) }
    catch { setProducts([]) }
  }

  useEffect(() => {
    if ((mode === 'wo' || mode === 'product') && products.length === 0) {
      void loadProducts()
    }
  }, [mode])

  async function createProduct() {
    if (!prod.product_no.trim() || !prod.name.trim()) { setErr('編號 + 名稱必填'); return }
    setBusy(true); setErr(null)
    try {
      await apiCreateProduct(prod)
      setProd({ product_no: '', name: '' })
      setMode('closed')
      await loadProducts()
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
    finally { setBusy(false) }
  }

  async function createWO() {
    if (!wo.product_id || wo.ordered_qty <= 0) { setErr('產品 + 數量必填'); return }
    setBusy(true); setErr(null)
    try {
      await apiCreateWO(wo)
      setWo({ product_id: '', ordered_qty: 1, priority: 50 })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '建單失敗') }
    finally { setBusy(false) }
  }

  return (
    <div className="bg-white rounded-xl shadow p-4 mb-6">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm font-medium text-gray-700 mr-2">新增：</span>
        <button onClick={() => setMode(mode === 'product' ? 'closed' : 'product')}
          className={`px-3 py-1.5 rounded text-sm ${mode === 'product' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}>
          ➕ 新增產品
        </button>
        <button onClick={() => setMode(mode === 'wo' ? 'closed' : 'wo')}
          className={`px-3 py-1.5 rounded text-sm ${mode === 'wo' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}>
          🏭 新增工單
        </button>
        <Link to="/chat" className="px-3 py-1.5 bg-purple-50 text-purple-700 hover:bg-purple-100 rounded text-sm">
          💬 用 AI 釋放工單
        </Link>
      </div>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mt-3 text-sm">{err}</div>}

      {mode === 'product' && (
        <div className="grid md:grid-cols-3 gap-2 mt-3 pt-3 border-t">
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="編號* 例 PROD-001"
            value={prod.product_no} onChange={(e) => setProd({ ...prod, product_no: e.target.value })} />
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="產品名稱*"
            value={prod.name} onChange={(e) => setProd({ ...prod, name: e.target.value })} />
          <button onClick={createProduct} disabled={busy}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {busy ? '儲存中…' : '✓ 儲存'}
          </button>
        </div>
      )}

      {mode === 'wo' && (
        <div className="mt-3 pt-3 border-t">
          <div className="grid md:grid-cols-4 gap-2">
            <select className="border rounded px-2 py-1.5 text-sm" value={wo.product_id}
              onChange={(e) => setWo({ ...wo, product_id: e.target.value })}>
              <option value="">選產品*</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.product_no} {p.name}</option>)}
            </select>
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="數量*" min="1"
              value={wo.ordered_qty} onChange={(e) => setWo({ ...wo, ordered_qty: Number(e.target.value) })} />
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="優先級 1-100" min="1" max="100"
              value={wo.priority} onChange={(e) => setWo({ ...wo, priority: Number(e.target.value) })} />
            <button onClick={createWO} disabled={busy}
              className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-50">
              {busy ? '建單中…' : '✓ 建單'}
            </button>
          </div>
          {products.length === 0 && (
            <p className="text-xs text-gray-500 mt-2">
              💡 還沒有產品？先按上面的「➕ 新增產品」建一個。
            </p>
          )}
        </div>
      )}
    </div>
  )
}
