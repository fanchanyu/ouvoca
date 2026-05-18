/**
 * NotesEditor — 單據備註編輯 modal（Sprint P v3.22）
 *
 * 對標鼎新 / 正航 / SAP B1：每張單據可留 internal remarks（給內部交接 / 主管看）
 *
 * 直接用 api.patch() 不加新 helper 避免 lib/api.ts conflict。
 */
import { useState } from 'react'
import { api } from '../lib/api'

interface Props {
  entityType: 'po' | 'so' | 'wo'
  entityId: string
  entityLabel: string  // 例：「PO-2026-0042」
  initialRemark: string | null
  onClose: () => void
  onSaved: () => void
}

export default function NotesEditor({
  entityType, entityId, entityLabel, initialRemark, onClose, onSaved,
}: Props) {
  const [remark, setRemark] = useState(initialRemark || '')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const pathMap = {
    po: `/purchase/orders/${entityId}`,
    so: `/sales/orders/${entityId}`,
    wo: `/production/work-orders/${entityId}`,
  } as const

  async function save() {
    setBusy(true); setErr(null)
    try {
      await api.patch(pathMap[entityType], { remark })
      onSaved()
      onClose()
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '儲存失敗')
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-3 border-b">
          <h2 className="font-semibold">📝 編輯備註 — {entityLabel}</h2>
          <button onClick={onClose} className="text-gray-500 hover:bg-gray-100 px-2 py-1 rounded text-sm">✕</button>
        </div>
        <div className="p-4">
          {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
          <label className="block text-xs text-gray-600 mb-1">
            內部備註（給同事 / 主管看，不會印在客戶單據上）
          </label>
          <textarea
            value={remark}
            onChange={(e) => setRemark(e.target.value)}
            placeholder="例：客戶說週五前到，否則退單 / 這家供應商長期合作可延付 30 天 / ..."
            className="w-full border rounded p-2 text-sm h-32 resize-none focus:outline-none focus:border-blue-400"
          />
          <div className="text-xs text-gray-400 mt-1">{remark.length} / 500 字</div>
          <div className="flex justify-end gap-2 mt-4">
            <button onClick={onClose} className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded">
              取消
            </button>
            <button onClick={save} disabled={busy}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
              {busy ? '儲存中…' : '✓ 儲存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
