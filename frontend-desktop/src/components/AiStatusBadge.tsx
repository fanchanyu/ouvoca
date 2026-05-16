/**
 * AiStatusBadge — header 常駐 AI 啟用狀態指示器（Sprint H v3.14）
 *
 * 設計：
 *  - ✅ 已啟用（綠燈，DeepSeek/OpenAI/...）：滑鼠 hover 顯示 provider+model
 *  - ⚠️ 未設定（黃燈）：點擊跳轉 /settings 設定
 *  - 載入中：旋轉中
 *  - 每 60 秒輪詢一次 status
 *
 * 參考其他 ERP：NetSuite 把整合狀態做成 dashboard widget；
 * 我們做成 header 持續可見的小指示燈，更符合「永遠提醒小白要去設」。
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiLlmStatus, type LlmStatus } from '../lib/api'

const POLL_MS = 60_000

export default function AiStatusBadge() {
  const nav = useNavigate()
  const [status, setStatus] = useState<LlmStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let stop = false
    async function tick() {
      try {
        const s = await apiLlmStatus()
        if (!stop) { setStatus(s); setLoading(false) }
      } catch {
        if (!stop) setLoading(false)
      }
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { stop = true; clearInterval(id) }
  }, [])

  if (loading) {
    return (
      <span className="flex items-center gap-1 px-2 h-7 rounded text-caption text-ink-400" title="檢查 AI 狀態...">
        <span className="w-1.5 h-1.5 rounded-full bg-ink-300 animate-pulse" />
        AI
      </span>
    )
  }

  if (!status) return null

  if (!status.configured) {
    return (
      <button
        onClick={() => nav('/settings')}
        className="flex items-center gap-1.5 px-2 h-7 rounded-full text-caption bg-amber-50 hover:bg-amber-100 text-amber-700 font-medium transition-colors focus-ring"
        title="點擊去設定 AI 助手"
      >
        <span className="text-sm leading-none">⚠️</span>
        <span className="hidden md:inline">AI 未設定</span>
        <span className="md:hidden">AI</span>
      </button>
    )
  }

  return (
    <button
      onClick={() => nav('/settings')}
      className="flex items-center gap-1.5 px-2 h-7 rounded-full text-caption bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-medium transition-colors focus-ring"
      title={`AI 已啟用：${status.provider} (${status.model})`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      <span className="hidden md:inline">AI · {status.provider}</span>
      <span className="md:hidden">AI</span>
    </button>
  )
}
