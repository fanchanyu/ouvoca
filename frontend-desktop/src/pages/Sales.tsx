import { useEffect, useState } from 'react'
import {
  apiListSOs, apiListCustomers, apiUpdateCustomer, apiDeleteCustomer,
  apiCancelSO,
  type SalesOrder, type Customer,
} from '../lib/api'
import EntityRowActions from '../components/EntityRowActions'
import EntityFormModal, { type FieldDef } from '../components/EntityFormModal'

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

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">銷售管理</h1>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat title="客戶總數" value={customers.length} />
        <Stat title="訂單總數" value={sos.length} />
        <Stat title="累計營收 (TWD)" value={totalRevenue.toLocaleString()} />
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden mb-6">
        <div className="px-4 py-3 bg-gray-50 font-semibold">銷售訂單</div>
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
                    {!['shipped', 'delivered', 'closed', 'cancelled'].includes(so.status) && (
                      <button
                        onClick={() => cancelSO(so)}
                        className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded"
                        title="取消銷售訂單"
                      >🚫 取消</button>
                    )}
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
