/**
 * EntityRowActions — 表格 row 右側的 Edit / Delete 按鈕（v3.11）。
 *
 * 用法：
 *   <EntityRowActions
 *     entityLabel="料件"
 *     entityName={part.part_no}
 *     onEdit={() => setEditing(part)}
 *     onDelete={async () => apiDeletePart(part.id)}
 *     onAfterDelete={load}
 *   />
 *
 * 設計：
 *   - 點 Edit → 觸發 onEdit callback（父層自己處理 modal 開啟）
 *   - 點 Delete → 跳 confirm() → 呼 onDelete → onAfterDelete refresh
 *   - 錯誤訊息 inline 顯示，不蓋掉整頁
 */
import { useState } from 'react'

interface Props {
  entityLabel: string             // e.g. "料件"
  entityName: string              // e.g. "M6-BOLT-20" 顯示在 confirm dialog
  onEdit?: () => void
  onDelete?: () => Promise<unknown>
  onAfterDelete?: () => void | Promise<void>
  disabled?: boolean
}

export default function EntityRowActions({
  entityLabel, entityName,
  onEdit, onDelete, onAfterDelete,
  disabled,
}: Props) {
  const [busy, setBusy] = useState<'edit' | 'delete' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!onDelete) return
    if (!confirm(`確定刪除 ${entityLabel} 「${entityName}」？\n\n此動作不可復原。`)) {
      return
    }
    setBusy('delete')
    setError(null)
    try {
      await onDelete()
      await onAfterDelete?.()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '刪除失敗'
      setError(msg)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex items-center gap-1 justify-end">
      {onEdit && (
        <button
          onClick={onEdit}
          disabled={disabled || busy !== null}
          className="px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 rounded disabled:opacity-50"
          title={`編輯 ${entityLabel}`}
        >
          ✏️ 編輯
        </button>
      )}
      {onDelete && (
        <button
          onClick={handleDelete}
          disabled={disabled || busy !== null}
          className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded disabled:opacity-50"
          title={`刪除 ${entityLabel}`}
        >
          {busy === 'delete' ? '刪除中…' : '🗑 刪除'}
        </button>
      )}
      {error && (
        <span className="text-xs text-red-600 ml-2" title={error}>
          ⚠️ {error.length > 40 ? error.slice(0, 40) + '…' : error}
        </span>
      )}
    </div>
  )
}
