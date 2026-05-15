/**
 * ConfirmCard — 對話式 hard-write 的「人類確認卡」。
 *
 * 顯示 AI 解析出的執行參數（slots）+ 摘要 + 倒數計時，
 * 使用者點「確認」才呼叫 API 真執行；點「取消」則丟棄。
 *
 * 設計：see docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5
 */
import { useEffect, useState } from 'react'
import { apiCancelCard, apiConfirmCard } from '../lib/api'
import type { ConfirmCardData, ConfirmCardResult } from '../lib/api'

interface Props {
  card: ConfirmCardData
  onResult: (result: ConfirmCardResult) => void
  onCancel: (cardId: string) => void
  onExpired: (cardId: string) => void
}

export default function ConfirmCard({ card, onResult, onCancel, onExpired }: Props) {
  const [busy, setBusy] = useState<'confirm' | 'cancel' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [remaining, setRemaining] = useState<number>(() => {
    return Math.max(0, Math.floor((new Date(card.expires_at).getTime() - Date.now()) / 1000))
  })

  // 倒數計時
  useEffect(() => {
    const tick = () => {
      const left = Math.max(0, Math.floor((new Date(card.expires_at).getTime() - Date.now()) / 1000))
      setRemaining(left)
      if (left <= 0) onExpired(card.id)
    }
    const t = setInterval(tick, 1000)
    return () => clearInterval(t)
  }, [card.expires_at, card.id, onExpired])

  const handleConfirm = async () => {
    setBusy('confirm')
    setError(null)
    try {
      const result = await apiConfirmCard(card.id)
      onResult(result)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '執行失敗'
      setError(msg)
    } finally {
      setBusy(null)
    }
  }

  const handleCancel = async () => {
    setBusy('cancel')
    try {
      await apiCancelCard(card.id)
    } catch {
      /* ignore — 即使 API fail 也視為取消 */
    } finally {
      onCancel(card.id)
      setBusy(null)
    }
  }

  const riskColor =
    card.risk_tier === 'hard-write'
      ? 'border-amber-300 bg-amber-50'
      : card.risk_tier === 'soft-write'
      ? 'border-blue-300 bg-blue-50'
      : 'border-gray-300 bg-gray-50'

  const riskLabel =
    card.risk_tier === 'hard-write' ? '⚠️ 高風險操作' : card.risk_tier === 'soft-write' ? '🛠 一般寫入' : '🔍 唯讀'

  return (
    <div className={`my-3 p-4 border-2 rounded-2xl shadow-sm ${riskColor}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-gray-900">{card.title}</h3>
            <span className="text-xs px-2 py-0.5 rounded bg-white border border-amber-200 text-amber-800">
              {riskLabel}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            tool: <code className="bg-white px-1.5 py-0.5 rounded">{card.tool_name}</code>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">剩餘有效</div>
          <div className={`text-sm font-mono ${remaining < 30 ? 'text-red-600 font-bold' : 'text-gray-700'}`}>
            {Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, '0')}
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white rounded-lg px-3 py-2 mb-3 border border-gray-200">
        <div className="text-xs font-semibold text-gray-700 mb-1">將執行的內容：</div>
        <ul className="text-sm text-gray-800 space-y-0.5">
          {card.summary.map((line, i) => (
            <li key={i} className={line.startsWith('  •') ? 'pl-3' : ''}>{line}</li>
          ))}
        </ul>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm mb-3">
          ❌ {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <button
          onClick={handleCancel}
          disabled={busy !== null || remaining <= 0}
          className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {busy === 'cancel' ? '取消中…' : '取消'}
        </button>
        <button
          onClick={handleConfirm}
          disabled={busy !== null || remaining <= 0}
          className="px-5 py-2 text-white bg-amber-600 hover:bg-amber-700 rounded-lg font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {busy === 'confirm' ? '執行中…' : '✓ 確認執行'}
        </button>
      </div>
    </div>
  )
}
