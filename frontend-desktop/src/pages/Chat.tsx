import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { apiChat } from '../lib/api'
import type { ConfirmCardData, ConfirmCardResult } from '../lib/api'
import ConfirmCard from '../components/ConfirmCard'
import AiSetupGuide from '../components/AiSetupGuide'

interface Msg {
  role: 'user' | 'assistant' | 'system'
  content: string
  agent?: string
  timestamp?: number
  isError?: boolean
  /** v3.1：hard-write tool 在此 turn 出的確認卡（若有） */
  card?: ConfirmCardData
  /** 是否已處理（確認 / 取消 / 過期） — 決定是否還可互動 */
  cardSettled?: 'confirmed' | 'cancelled' | 'expired'
  /** v3.14：當 backend 回 setup_required=true 時 render 申請引導卡 */
  setupGuide?: { reason: 'no_api_key' | 'invalid_key' | 'quota_exceeded'; intent?: string }
}

/**
 * 從 chat-v2 回傳的 tool_calls 內找最後一張 ConfirmCard。
 * 每個 tool_call.result 是 JSON-stringified；若 parse 結果含 {type: "confirm_card"}，
 * 就把卡撈出來給前端 render。
 */
function extractCard(tool_calls?: Array<{ tool: string; result: string | unknown }>): ConfirmCardData | undefined {
  if (!tool_calls || tool_calls.length === 0) return undefined
  // 反向找最後一張（最新）
  for (let i = tool_calls.length - 1; i >= 0; i--) {
    const r = tool_calls[i].result
    try {
      const parsed = typeof r === 'string' ? JSON.parse(r) : r
      if (parsed && typeof parsed === 'object' && (parsed as { type?: string }).type === 'confirm_card') {
        return (parsed as { card: ConfirmCardData }).card
      }
    } catch { /* not JSON, skip */ }
  }
  return undefined
}

const HISTORY_KEY = 'erpilot_chat_history'
const MAX_HISTORY = 200

const SUGGESTIONS = [
  '哪些零件低於安全庫存？',
  '今天工廠運營狀況如何？',
  '我們有哪些客戶？',
  '最近進行中的工單',
  '列出所有供應商',
  '本月有逾期的應收帳款嗎？',
]

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY)
      return raw ? (JSON.parse(raw) as Msg[]) : []
    } catch {
      return []
    }
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingSeconds, setLoadingSeconds] = useState(0)  // v3.35: 計時用於漸進式提示
  const [sessionId] = useState(() => 'sess-' + Math.random().toString(36).slice(2))
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 自動捲到底
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  // v3.35：等待計時 — 讓「以為當機」之客戶看到 AI 還在做事
  useEffect(() => {
    if (!loading) {
      setLoadingSeconds(0)
      return
    }
    const t = setInterval(() => setLoadingSeconds(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [loading])

  // v3.35：依等待時間給友善訊息
  const loadingHint = (() => {
    if (loadingSeconds < 3) return 'AI 思考中…'
    if (loadingSeconds < 8) return `AI 正在查詢資料… (${loadingSeconds} 秒)`
    if (loadingSeconds < 15) return `AI 正在計算… (${loadingSeconds} 秒，請稍候)`
    if (loadingSeconds < 30) return `AI 正在跑複雜分析… (${loadingSeconds} 秒，快好了)`
    return `已等 ${loadingSeconds} 秒 — 若超過 60 秒請刷新頁面或洽 IT`
  })()

  // 持久化（截短最近 N 筆）
  useEffect(() => {
    try {
      const recent = messages.slice(-MAX_HISTORY)
      localStorage.setItem(HISTORY_KEY, JSON.stringify(recent))
    } catch {/* ignore */}
  }, [messages])

  const send = useCallback(async (textArg?: string) => {
    const text = (textArg ?? input).trim()
    if (!text || loading) return
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: Date.now() }])
    setInput('')
    setLoading(true)
    try {
      const data = await apiChat(text, sessionId)
      const card = extractCard(data.tool_calls)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply || (card ? '請確認以下操作：' : '(無回應)'),
        agent: data.agent,
        timestamp: Date.now(),
        card,
        // v3.14：把 backend 結構化 setup_required flag 帶到前端 render
        setupGuide: data.setup_required
          ? { reason: data.setup_reason || 'no_api_key', intent: data.agent }
          : undefined,
      }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '連線錯誤'
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ ${msg}`,
        timestamp: Date.now(),
        isError: true,
      }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, sessionId])

  const regenerate = useCallback(() => {
    // 找最後一筆 user message → 重發
    const lastUser = [...messages].reverse().find(m => m.role === 'user')
    if (!lastUser || loading) return
    // 移除最後一筆 assistant
    setMessages(prev => {
      const idx = [...prev].reverse().findIndex(m => m.role === 'assistant')
      if (idx === -1) return prev
      const realIdx = prev.length - 1 - idx
      return prev.slice(0, realIdx)
    })
    void send(lastUser.content)
  }, [messages, loading, send])

  const clearHistory = useCallback(() => {
    if (!confirm('確定清空對話記錄？此動作不可復原。')) return
    setMessages([])
    localStorage.removeItem(HISTORY_KEY)
  }, [])

  const copyToClipboard = useCallback(async (text: string) => {
    try { await navigator.clipboard.writeText(text) } catch {/* ignore */}
  }, [])

  // v3.1: ConfirmCard 回呼
  const handleCardResult = useCallback((cardId: string, result: ConfirmCardResult) => {
    // 標記原訊息為 confirmed
    setMessages(prev =>
      prev.map(m => (m.card?.id === cardId ? { ...m, cardSettled: 'confirmed' as const } : m))
    )
    // 附一則 assistant 訊息顯示執行結果
    const r = result.result as Record<string, unknown>
    const message =
      (typeof r === 'object' && r !== null && typeof r.message === 'string'
        ? r.message
        : `✅ 已執行 ${result.tool_name}`)
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: message,
      timestamp: Date.now(),
    }])
  }, [])

  const handleCardCancel = useCallback((cardId: string) => {
    setMessages(prev =>
      prev.map(m => (m.card?.id === cardId ? { ...m, cardSettled: 'cancelled' as const } : m))
    )
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: '🚫 已取消此操作',
      timestamp: Date.now(),
    }])
  }, [])

  const handleCardExpired = useCallback((cardId: string) => {
    setMessages(prev =>
      prev.map(m => (m.card?.id === cardId && !m.cardSettled ? { ...m, cardSettled: 'expired' as const } : m))
    )
  }, [])

  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">AI 助手</h1>
        <div className="flex items-center gap-2 text-sm">
          {messages.length > 0 && (
            <>
              <span className="text-gray-400">{messages.length} 則訊息</span>
              <button
                onClick={clearHistory}
                className="px-3 py-1 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition"
                title="清空對話記錄"
              >
                🗑 清空
              </button>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 bg-white rounded-xl shadow p-4 overflow-y-auto mb-4">
        {messages.length === 0 && (
          <div className="text-gray-500 text-center mt-20">
            <div className="text-5xl mb-4">💬</div>
            <div className="mb-6 text-base">向 AI 助手詢問任何 ERP 相關問題</div>
            <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="px-4 py-2 bg-gradient-to-br from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 text-sm rounded-full border border-blue-100 text-blue-700 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`group mb-4 ${msg.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}
          >
            <div
              className={`inline-block max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : msg.isError
                  ? 'bg-red-50 text-red-800 border border-red-200'
                  : 'bg-gray-50 text-gray-800 border border-gray-200'
              }`}
            >
              {msg.role === 'assistant' && !msg.isError ? (
                <div className="prose prose-sm max-w-none prose-table:my-2 prose-th:bg-gray-100 prose-th:px-3 prose-th:py-1.5 prose-td:px-3 prose-td:py-1.5 prose-td:border prose-th:border prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-code:text-pink-600 prose-code:before:content-none prose-code:after:content-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="whitespace-pre-wrap break-words">{msg.content}</div>
              )}
            </div>

            {/* v3.14: AI 設定引導卡（no_api_key / invalid_key / quota_exceeded） */}
            {msg.setupGuide && (
              <div className="w-full max-w-[85%]">
                <AiSetupGuide reason={msg.setupGuide.reason} detectedIntent={msg.setupGuide.intent} />
              </div>
            )}

            {/* v3.1: ConfirmCard 內嵌（在訊息泡泡下方） */}
            {msg.card && !msg.cardSettled && (
              <div className="w-full max-w-[85%]">
                <ConfirmCard
                  card={msg.card}
                  onResult={(r) => handleCardResult(msg.card!.id, r)}
                  onCancel={(id) => handleCardCancel(id)}
                  onExpired={(id) => handleCardExpired(id)}
                />
              </div>
            )}
            {msg.card && msg.cardSettled && (
              <div className="w-full max-w-[85%] mt-1">
                <div className="text-xs text-gray-500 italic px-3 py-1">
                  {msg.cardSettled === 'confirmed' && '✅ 已確認執行'}
                  {msg.cardSettled === 'cancelled' && '🚫 已取消'}
                  {msg.cardSettled === 'expired' && '⏰ 已過期（未執行）'}
                </div>
              </div>
            )}

            {/* Footer chips */}
            <div className={`flex items-center gap-2 mt-1 px-2 text-xs text-gray-400 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {msg.agent && msg.role === 'assistant' && !msg.isError && (
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded">{msg.agent}</span>
              )}
              {msg.timestamp && (
                <span>{new Date(msg.timestamp).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })}</span>
              )}
              {msg.role === 'assistant' && !msg.isError && (
                <button
                  onClick={() => copyToClipboard(msg.content)}
                  className="opacity-0 group-hover:opacity-100 hover:text-blue-600 transition"
                  title="複製"
                >
                  📋 複製
                </button>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-gray-500 text-sm pl-2">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span>{loadingHint}</span>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex gap-2 items-end">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
          placeholder="輸入您的問題…  (Shift + Enter 換行)"
          rows={1}
          className="flex-1 px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none max-h-32"
        />
        {messages.some(m => m.role === 'assistant' && !m.isError) && !loading && (
          <button
            onClick={regenerate}
            className="px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition"
            title="重新生成上一個回答"
          >
            🔄
          </button>
        )}
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          送出
        </button>
      </div>
    </div>
  )
}
