import { useState, useEffect } from 'react'
import { apiListParts, apiCreatePart, type Part } from '../lib/api'
import EmptyState from '../components/EmptyState'

export default function Inventory() {
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    part_no: '', name: '', category: 'raw_material', unit: 'pcs',
    safety_stock: 0, unit_cost: 0, lead_time_days: 0,
  })

  async function load() {
    setLoading(true)
    try {
      setParts(await apiListParts())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function submit() {
    setError(null)
    try {
      await apiCreatePart(form)
      setShowForm(false)
      setForm({ part_no: '', name: '', category: 'raw_material', unit: 'pcs', safety_stock: 0, unit_cost: 0, lead_time_days: 0 })
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '新增失敗')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">庫存管理</h1>
        <button onClick={() => setShowForm(!showForm)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {showForm ? '取消' : '新增零件'}
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg mb-4 text-sm">{error}</div>}

      {showForm && (
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">新增零件</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="料號 *"><input value={form.part_no} onChange={e => setForm({...form, part_no: e.target.value})} className="input" /></Field>
            <Field label="名稱 *"><input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="input" /></Field>
            <Field label="類別">
              <select value={form.category} onChange={e => setForm({...form, category: e.target.value})} className="input">
                <option value="raw_material">原料</option>
                <option value="semi_finished">半成品</option>
                <option value="component">零組件</option>
                <option value="consumable">耗材</option>
                <option value="packaging">包裝</option>
              </select>
            </Field>
            <Field label="單位"><input value={form.unit} onChange={e => setForm({...form, unit: e.target.value})} className="input" /></Field>
            <Field label="安全庫存"><input type="number" value={form.safety_stock} onChange={e => setForm({...form, safety_stock: +e.target.value})} className="input" /></Field>
            <Field label="單位成本"><input type="number" value={form.unit_cost} onChange={e => setForm({...form, unit_cost: +e.target.value})} className="input" /></Field>
            <Field label="前置時間 (天)"><input type="number" value={form.lead_time_days} onChange={e => setForm({...form, lead_time_days: +e.target.value})} className="input" /></Field>
          </div>
          <button onClick={submit} className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">送出</button>
        </div>
      )}

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">料號</th>
              <th className="text-left p-3">名稱</th>
              <th className="text-left p-3">類別</th>
              <th className="text-right p-3">安全庫存</th>
              <th className="text-right p-3">單位成本</th>
              <th className="text-right p-3">前置時間</th>
              <th className="text-center p-3">狀態</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : parts.length === 0 ? (
              <tr><td colSpan={7}>
                <EmptyState
                  icon="📦"
                  title="你還沒有任何料件"
                  subtitle="先載入示範資料試試手感，或直接新增第一個料件"
                  primaryAction={{ label: '➕ 新增第一個料件', onClick: () => setShowForm(true) }}
                  secondaryAction={{ label: '⚙️ 載入示範資料', to: '/settings' }}
                  compact
                />
              </td></tr>
            ) : (
              parts.map(p => (
                <tr key={p.id} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-mono">{p.part_no}</td>
                  <td className="p-3">{p.name}</td>
                  <td className="p-3">{p.category}</td>
                  <td className="p-3 text-right">{p.safety_stock}</td>
                  <td className="p-3 text-right">{p.unit_cost.toFixed(2)}</td>
                  <td className="p-3 text-right">{p.lead_time_days}d</td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs ${p.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100'}`}>
                      {p.is_active ? '啟用' : '停用'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <style>{`.input { width: 100%; border: 1px solid #d1d5db; border-radius: 0.5rem; padding: 0.5rem 0.75rem; }`}</style>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
