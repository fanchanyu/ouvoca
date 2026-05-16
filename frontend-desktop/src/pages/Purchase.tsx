import { useEffect, useState } from 'react'
import {
  apiListPOs, apiListSuppliers, apiUpdateSupplier, apiDeleteSupplier,
  apiCancelPO,
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
