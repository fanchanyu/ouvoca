/**
 * EntityFormModal — 簡單的 edit form 彈窗（v3.11）。
 *
 * 用法：
 *   <EntityFormModal
 *     title="編輯料件"
 *     fields={[
 *       { name: 'name', label: '名稱', type: 'text', required: true },
 *       { name: 'safety_stock', label: '安全庫存', type: 'number' },
 *     ]}
 *     initial={part}
 *     onSubmit={async (patch) => apiUpdatePart(part.id, patch)}
 *     onClose={() => setEditing(null)}
 *     onSuccess={() => { setEditing(null); load() }}
 *   />
 */
import { useState } from 'react'

export interface FieldDef {
  name: string
  label: string
  type: 'text' | 'number' | 'select' | 'checkbox'
  required?: boolean
  options?: Array<{ value: string; label: string }>
  step?: string
}

interface Props {
  title: string
  fields: FieldDef[]
  initial: Record<string, unknown>
  onSubmit: (patch: Record<string, unknown>) => Promise<unknown>
  onClose: () => void
  onSuccess: () => void
}

export default function EntityFormModal({
  title, fields, initial, onSubmit, onClose, onSuccess,
}: Props) {
  const [values, setValues] = useState<Record<string, unknown>>(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setField = (name: string, value: unknown) =>
    setValues(prev => ({ ...prev, [name]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      // Compute patch: 只送有變動的欄位（避免不必要 update）
      const patch: Record<string, unknown> = {}
      for (const f of fields) {
        if (values[f.name] !== initial[f.name]) {
          patch[f.name] = values[f.name]
        }
      }
      if (Object.keys(patch).length === 0) {
        onClose()
        return
      }
      await onSubmit(patch)
      onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '儲存失敗')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="bg-gradient-to-r from-blue-500 to-blue-700 px-5 py-3 text-white flex justify-between items-center">
          <h3 className="font-bold">{title}</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white text-xl leading-none">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          {fields.map(f => (
            <div key={f.name}>
              <label className="block text-sm text-gray-700 mb-1">
                {f.label}{f.required && <span className="text-red-500"> *</span>}
              </label>
              {f.type === 'select' ? (
                <select
                  value={String(values[f.name] ?? '')}
                  onChange={e => setField(f.name, e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  required={f.required}
                >
                  {f.options?.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : f.type === 'checkbox' ? (
                <input
                  type="checkbox"
                  checked={Boolean(values[f.name])}
                  onChange={e => setField(f.name, e.target.checked)}
                  className="rounded"
                />
              ) : (
                <input
                  type={f.type}
                  value={String(values[f.name] ?? '')}
                  onChange={e => setField(
                    f.name,
                    f.type === 'number' ? (e.target.value === '' ? null : +e.target.value) : e.target.value,
                  )}
                  step={f.step}
                  required={f.required}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
                />
              )}
            </div>
          ))}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
              ❌ {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-3 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={busy}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {busy ? '儲存中…' : '✓ 儲存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
