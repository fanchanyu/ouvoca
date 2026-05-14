import { useEffect, useState } from 'react'
import { apiListWOs, apiReleaseWO, type ProductionOrder } from '../lib/api'

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
                      {w.status === 'draft' && (
                        <button onClick={() => release(w.id)} className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700">釋放</button>
                      )}
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
