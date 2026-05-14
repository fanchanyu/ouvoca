import { useEffect, useState } from 'react'
import { apiListPOs, apiListSuppliers, type PurchaseOrder, type Supplier } from '../lib/api'

export default function Purchase() {
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<string>('')

  async function load() {
    setLoading(true)
    try {
      const [p, s] = await Promise.all([apiListPOs(filterStatus || undefined), apiListSuppliers()])
      setPos(p); setSuppliers(s)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [filterStatus])

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">採購管理</h1>
        <div className="flex gap-3 items-center">
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
            <option value="">全部狀態</option>
            <option value="draft">草稿</option>
            <option value="approved">已核准</option>
            <option value="sent">已發送</option>
            <option value="received">已收貨</option>
            <option value="partial_received">部分收貨</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat title="供應商總數" value={suppliers.length} />
        <Stat title="採購單總數" value={pos.length} />
        <Stat title="總金額 (TWD)" value={pos.reduce((sum, p) => sum + p.total_amount, 0).toLocaleString()} />
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">採購單號</th>
              <th className="text-left p-3">供應商</th>
              <th className="text-left p-3">狀態</th>
              <th className="text-right p-3">金額</th>
              <th className="text-left p-3">下單日期</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : pos.length === 0 ? (
              <tr><td colSpan={5} className="p-4 text-center text-gray-400">尚無採購單資料</td></tr>
            ) : (
              pos.map(po => (
                <tr key={po.id} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-mono text-xs">{po.po_no}</td>
                  <td className="p-3">{po.supplier?.name || po.supplier_id}</td>
                  <td className="p-3"><StatusBadge status={po.status} /></td>
                  <td className="p-3 text-right">{po.total_amount.toLocaleString()}</td>
                  <td className="p-3">{new Date(po.order_date).toLocaleDateString('zh-TW')}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
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
