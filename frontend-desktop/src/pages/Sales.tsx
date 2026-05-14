import { useEffect, useState } from 'react'
import { apiListSOs, apiListCustomers, type SalesOrder } from '../lib/api'

export default function Sales() {
  const [sos, setSos] = useState<SalesOrder[]>([])
  const [customers, setCustomers] = useState<Array<{ id: string; name: string; grade: string }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([apiListSOs().catch(() => []), apiListCustomers().catch(() => [])])
      .then(([s, c]) => { setSos(s); setCustomers(c); setLoading(false) })
  }, [])

  const totalRevenue = sos.reduce((sum, s) => sum + s.total_amount, 0)

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
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : sos.length === 0 ? (
              <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無訂單</td></tr>
            ) : (
              sos.map(so => (
                <tr key={so.id} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-mono text-xs">{so.so_no}</td>
                  <td className="p-3">{so.customer?.name || so.customer_id}</td>
                  <td className="p-3">
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">{so.status}</span>
                  </td>
                  <td className="p-3 text-right">{so.total_amount.toLocaleString()}</td>
                  <td className="p-3"><span className="text-xs text-gray-500">{so.payment_status}</span></td>
                  <td className="p-3 text-xs">{new Date(so.order_date).toLocaleDateString('zh-TW')}</td>
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
            <tr><th className="text-left p-3">客戶</th><th className="text-center p-3">分級</th></tr>
          </thead>
          <tbody>
            {customers.length === 0 ? (
              <tr><td colSpan={2} className="p-4 text-center text-gray-400">尚無客戶</td></tr>
            ) : (
              customers.map(c => (
                <tr key={c.id} className="border-t">
                  <td className="p-3">{c.name}</td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      c.grade === 'A' ? 'bg-purple-100 text-purple-800' :
                      c.grade === 'B' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100'
                    }`}>{c.grade}</span>
                  </td>
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
