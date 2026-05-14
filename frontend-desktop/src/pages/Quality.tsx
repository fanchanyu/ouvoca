import { useEffect, useState } from 'react'
import { apiListInspections, apiListNCs } from '../lib/api'

export default function Quality() {
  const [inspections, setInspections] = useState<Array<{ id: string; inspection_no: string; part_id: string; accepted_qty: number; rejected_qty: number; status: string }>>([])
  const [ncs, setNcs] = useState<Array<{ id: string; nc_no: string; severity: string; description: string; qty_affected: number }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([apiListInspections().catch(() => []), apiListNCs().catch(() => [])])
      .then(([i, n]) => { setInspections(i); setNcs(n); setLoading(false) })
  }, [])

  const totalInspected = inspections.reduce((s, i) => s + (i.accepted_qty + i.rejected_qty), 0)
  const totalRejected = inspections.reduce((s, i) => s + i.rejected_qty, 0)
  const passRate = totalInspected > 0 ? ((1 - totalRejected / totalInspected) * 100).toFixed(2) : '—'

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">品質管理</h1>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Stat title="檢驗單" value={inspections.length} />
        <Stat title="合格率" value={`${passRate}%`} />
        <Stat title="不良品 (NC)" value={ncs.length} color="red" />
        <Stat title="總抽檢量" value={totalInspected} />
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden mb-6">
        <div className="px-4 py-3 bg-gray-50 font-semibold">檢驗單</div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-t">
            <tr>
              <th className="text-left p-3">檢驗單號</th>
              <th className="text-right p-3">合格量</th>
              <th className="text-right p-3">不良量</th>
              <th className="text-left p-3">狀態</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : inspections.length === 0 ? (
              <tr><td colSpan={4} className="p-4 text-center text-gray-400">尚無檢驗單</td></tr>
            ) : (
              inspections.map(i => (
                <tr key={i.id} className="border-t">
                  <td className="p-3 font-mono text-xs">{i.inspection_no}</td>
                  <td className="p-3 text-right">{i.accepted_qty}</td>
                  <td className="p-3 text-right text-red-600">{i.rejected_qty}</td>
                  <td className="p-3"><span className="px-2 py-1 bg-gray-100 rounded-full text-xs">{i.status}</span></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 font-semibold">不良品 (NC)</div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-t">
            <tr>
              <th className="text-left p-3">NC 編號</th>
              <th className="text-center p-3">嚴重度</th>
              <th className="text-left p-3">說明</th>
              <th className="text-right p-3">影響數量</th>
            </tr>
          </thead>
          <tbody>
            {ncs.length === 0 ? (
              <tr><td colSpan={4} className="p-4 text-center text-gray-400">尚無不良品記錄</td></tr>
            ) : (
              ncs.map(n => (
                <tr key={n.id} className="border-t">
                  <td className="p-3 font-mono text-xs">{n.nc_no}</td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      n.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      n.severity === 'major' ? 'bg-orange-100 text-orange-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>{n.severity}</span>
                  </td>
                  <td className="p-3">{n.description}</td>
                  <td className="p-3 text-right">{n.qty_affected}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Stat({ title, value, color }: { title: string; value: number | string; color?: string }) {
  const c = color === 'red' ? 'border-red-500' : ''
  return (
    <div className={`bg-white rounded-xl shadow p-4 border-l-4 ${c || 'border-blue-500'}`}>
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  )
}
