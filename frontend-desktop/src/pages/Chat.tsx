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
  /** v3.41 P4：訊息 id（給 pin / feedback 用） */
  id?: string
  /** v3.41 P4：是否被 pin（釘住） */
  pinned?: boolean
  /** v3.41 P7：使用者回饋（1 = 👍 / -1 = 👎） */
  feedback?: 1 | -1
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

/**
 * v3.37 D1-2/D1-3：從 tool_calls 找帶有檔案 (pdf_base64 / base64) 的回傳，
 * 自動觸發瀏覽器下載（解決小白「點連結 401 / 看到 base64 沒反應」）。
 *
 * 偵測規則：
 *   - tool_calls[i].result JSON 解析後若有 raw.pdf_base64 或 raw.base64
 *     → 組 Blob → 觸發 a.download
 *
 * 副作用：每次 chat 回應後最多下載 1 個檔（最新的）。
 */
function triggerAutoDownload(tool_calls?: Array<{ tool: string; result: string | unknown }>) {
  if (!tool_calls || tool_calls.length === 0) return
  for (let i = tool_calls.length - 1; i >= 0; i--) {
    const r = tool_calls[i].result
    try {
      const parsed = typeof r === 'string' ? JSON.parse(r) : r
      if (!parsed || typeof parsed !== 'object') continue
      const raw = (parsed as { raw?: Record<string, unknown> }).raw
      if (!raw) continue

      let b64: string | undefined
      let filename: string | undefined
      let mimeType: string = 'application/octet-stream'

      if (typeof raw.pdf_base64 === 'string') {
        b64 = raw.pdf_base64
        mimeType = 'application/pdf'
        // 用 download_url 倒推檔名
        const url = typeof raw.download_url === 'string' ? raw.download_url : ''
        filename = url.split('/').pop() || `document-${Date.now()}.pdf`
      } else if (typeof raw.base64 === 'string') {
        b64 = raw.base64
        const fmt = (raw.fmt as string) || 'xlsx'
        const entity = (raw.entity as string) || 'export'
        mimeType = fmt === 'csv'
          ? 'text/csv;charset=utf-8'
          : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = `${entity}-${new Date().toISOString().slice(0, 10)}.${fmt}`
      }

      if (!b64 || !filename) continue

      try {
        const byteChars = atob(b64)
        const byteNums = new Uint8Array(byteChars.length)
        for (let j = 0; j < byteChars.length; j++) byteNums[j] = byteChars.charCodeAt(j)
        const blob = new Blob([byteNums], { type: mimeType })
        const objectUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objectUrl
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        // 等 1 秒釋放 — 給瀏覽器時間真的下完
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
        return  // 只下載最新一個
      } catch (e) {
        console.warn('[Chat] 自動下載失敗', e)
      }
    } catch { /* skip */ }
  }
}

const HISTORY_KEY = 'ouvoca_chat_history'
const MAX_HISTORY = 200

const SUGGESTIONS = [
  '哪些零件低於安全庫存？',
  '今天工廠運營狀況如何？',
  '我們有哪些客戶？',
  '最近進行中的工單',
  '列出所有供應商',
  '本月有逾期的應收帳款嗎？',
]

// v3.37 D1-1：第一次開啟 Chat 時，AI 主動講話而不是讓使用者盯著空白
const FIRST_TIME_GREETING = `👋 **您好！我是 Ouvoca AI 助手。**

我可以用講的幫您：

- 📦 **庫存**：「哪些料件快沒了？」
- 🤝 **客戶**：「新增客戶 ABC 公司」
- 📄 **單據**：「印報價單 QUO-001」「匯出客戶清單 Excel」
- 🏢 **設定**：「公司叫長江精密」「改密碼」
- 🔔 **主動提醒**：「今天有什麼要注意的？」

**第一次使用嗎？** 試試下面任一個按鈕，或直接打字告訴我您想做什麼。`

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
  // v3.38 N8：AbortController — 讓使用者可以「取消」LLM 等待
  const abortRef = useRef<AbortController | null>(null)
  // v3.41 P3：短答模式 — 給 LLM hint「請 1-2 句」
  const [briefMode, setBriefMode] = useState<boolean>(
    () => localStorage.getItem('ouvoca_chat_brief') === '1'
  )
  // v3.41 P4：是否顯示「已釘訊息」面板
  const [showPinned, setShowPinned] = useState(false)

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
    const userMsgId = 'um-' + Math.random().toString(36).slice(2, 10)
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: text, timestamp: Date.now() }])
    setInput('')
    setLoading(true)
    // v3.38 N8：建立可取消的請求
    const controller = new AbortController()
    abortRef.current = controller
    try {
      // v3.41 P3：短答模式 — 在訊息前綴加 hint 給 LLM
      const textToSend = briefMode
        ? `[請用 1-2 句精簡回答，不要 markdown 表格] ${text}`
        : text
      const data = await apiChat(textToSend, sessionId, controller.signal)
      const card = extractCard(data.tool_calls)
      // v3.37 D1-2/D1-3：自動觸發 PDF / Excel 下載 — 小白不必點連結
      triggerAutoDownload(data.tool_calls)
      const assistantId = 'am-' + Math.random().toString(36).slice(2, 10)
      setMessages(prev => [...prev, {
        id: assistantId,
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
      // v3.38 N8：使用者按取消時不算錯誤
      const isAbort = e instanceof Error && (e.name === 'AbortError' || /abort/i.test(e.message))
      const msg = isAbort ? '🚫 已取消' : (e instanceof Error ? e.message : '連線錯誤')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: isAbort ? msg : `❌ ${msg}`,
        timestamp: Date.now(),
        isError: !isAbort,
      }])
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }, [input, loading, sessionId, briefMode])

  // v3.38 N8：取消當前 LLM 請求
  const cancelCurrent = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
  }, [])

  // v3.41 P3：toggle 短答模式
  const toggleBrief = useCallback(() => {
    setBriefMode(v => {
      const next = !v
      try { localStorage.setItem('ouvoca_chat_brief', next ? '1' : '0') } catch { /* ignore */ }
      return next
    })
  }, [])

  // v3.41 P4：toggle pin
  const togglePin = useCallback((msgId: string) => {
    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, pinned: !m.pinned } : m
    ))
  }, [])

  // v3.41 P7：thumbs up / down — 寫到後端 + 本地 state
  const submitFeedback = useCallback(async (msgId: string, score: 1 | -1) => {
    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, feedback: score } : m
    ))
    try {
      const { api } = await import('../lib/api')
      await api.post('/chat/feedback', {
        message_id: msgId,
        session_id: sessionId,
        score,
      })
    } catch (e) {
      console.warn('[Chat] feedback submit failed', e)
    }
  }, [sessionId])

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
    // v3.38 N5：手機版 viewport 高度修正（iOS Safari 動態 toolbar）
    <div className="flex flex-col h-[calc(100vh-80px)] sm:h-[calc(100vh-80px)] min-h-[400px]">
      {/* Header — 手機上字小一級 */}
      <div className="flex items-center justify-between mb-2 sm:mb-4 flex-wrap gap-2">
        <h1 className="text-lg sm:text-2xl font-bold">AI 助手</h1>
        <div className="flex items-center gap-2 text-sm flex-wrap">
          {/* v3.41 P3：短答模式 */}
          <button
            onClick={toggleBrief}
            className={`px-3 py-1 rounded transition text-xs ${
              briefMode
                ? 'bg-amber-100 text-amber-800 border border-amber-300'
                : 'text-gray-500 hover:bg-gray-100 border border-transparent'
            }`}
            title={briefMode ? '已啟用短答（1-2 句）' : '啟用短答模式（給老闆看的簡答）'}
          >
            {briefMode ? '⚡ 短答 ON' : '⚡ 短答'}
          </button>
          {/* v3.41 P4：已釘訊息 */}
          {messages.some(m => m.pinned) && (
            <button
              onClick={() => setShowPinned(v => !v)}
              className={`px-3 py-1 rounded transition text-xs border ${
                showPinned ? 'bg-yellow-100 text-yellow-800 border-yellow-300' : 'text-gray-600 hover:bg-yellow-50 border-yellow-200'
              }`}
              title="顯示 / 隱藏已釘訊息"
            >
              📌 已釘 ({messages.filter(m => m.pinned).length})
            </button>
          )}
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

      {/* v3.41 P4：已釘訊息面板（toggle） */}
      {showPinned && messages.some(m => m.pinned) && (
        <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-xl">
          <div className="text-xs text-yellow-800 font-medium mb-2">📌 已釘訊息：</div>
          <div className="space-y-2">
            {messages.filter(m => m.pinned).map(m => (
              <div key={`pin-${m.id}`} className="text-sm bg-white rounded p-2 border border-yellow-100">
                <div className="text-xs text-gray-400 mb-1">
                  {m.role === 'user' ? '👤 我' : '🤖 AI'} ·{' '}
                  {m.timestamp && new Date(m.timestamp).toLocaleString('zh-TW', { hour: '2-digit', minute: '2-digit', month: '2-digit', day: '2-digit' })}
                </div>
                <div className="whitespace-pre-wrap line-clamp-3">{m.content}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 bg-white rounded-xl shadow p-4 overflow-y-auto mb-4">
        {messages.length === 0 && (
          <div className="text-gray-700 max-w-3xl mx-auto mt-8">
            {/* v3.37 D1-1：AI 主動歡迎 — 不讓小白盯空白 */}
            <div className="inline-block bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl px-5 py-4 shadow-sm">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {FIRST_TIME_GREETING}
                </ReactMarkdown>
              </div>
            </div>
            <div className="mt-6">
              <div className="text-xs text-gray-500 mb-2 font-medium">💡 試試這些範例：</div>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="px-3 py-1.5 bg-white hover:bg-blue-50 text-sm rounded-full border border-blue-200 text-blue-700 transition shadow-sm"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`group mb-4 ${msg.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}
          >
            <div
              className={`inline-block max-w-[92%] sm:max-w-[85%] rounded-2xl px-4 py-3 ${
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
              <div className="w-full max-w-[92%] sm:max-w-[85%]">
                <AiSetupGuide reason={msg.setupGuide.reason} detectedIntent={msg.setupGuide.intent} />
              </div>
            )}

            {/* v3.1: ConfirmCard 內嵌（在訊息泡泡下方） */}
            {msg.card && !msg.cardSettled && (
              <div className="w-full max-w-[92%] sm:max-w-[85%]">
                <ConfirmCard
                  card={msg.card}
                  onResult={(r) => handleCardResult(msg.card!.id, r)}
                  onCancel={(id) => handleCardCancel(id)}
                  onExpired={(id) => handleCardExpired(id)}
                />
              </div>
            )}
            {msg.card && msg.cardSettled && (
              <div className="w-full max-w-[92%] sm:max-w-[85%] mt-1">
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
                <>
                  <button
                    onClick={() => copyToClipboard(msg.content)}
                    className="opacity-0 group-hover:opacity-100 hover:text-blue-600 transition"
                    title="複製"
                  >
                    📋 複製
                  </button>
                  {/* v3.41 P4：pin */}
                  {msg.id && (
                    <button
                      onClick={() => togglePin(msg.id!)}
                      className={`${msg.pinned ? 'text-yellow-600' : 'opacity-0 group-hover:opacity-100 hover:text-yellow-600'} transition`}
                      title={msg.pinned ? '取消釘住' : '釘住此回答'}
                    >
                      {msg.pinned ? '📌 已釘' : '📌 釘'}
                    </button>
                  )}
                  {/* v3.41 P7：thumbs */}
                  {msg.id && msg.feedback !== 1 && (
                    <button
                      onClick={() => submitFeedback(msg.id!, 1)}
                      className="opacity-0 group-hover:opacity-100 hover:text-green-600 transition"
                      title="這個答案有幫助"
                    >
                      👍
                    </button>
                  )}
                  {msg.id && msg.feedback === 1 && (
                    <span className="text-green-600">👍 已讚</span>
                  )}
                  {msg.id && msg.feedback !== -1 && (
                    <button
                      onClick={() => submitFeedback(msg.id!, -1)}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-600 transition"
                      title="這個答案有錯"
                    >
                      👎
                    </button>
                  )}
                  {msg.id && msg.feedback === -1 && (
                    <span className="text-red-600">👎 已回報</span>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 text-gray-500 text-sm pl-2">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span className="flex-1">{loadingHint}</span>
            {/* v3.38 N8：取消按鈕 — 老闆等不下去可以中斷 */}
            <button
              onClick={cancelCurrent}
              className="px-3 py-1 bg-red-50 hover:bg-red-100 text-red-700 text-xs rounded-full border border-red-200 transition"
              title="取消這次 AI 請求"
            >
              ⏹ 取消
            </button>
          </div>
        )}
      </div>

      {/* Input bar — v3.38 N5 手機友善：間距變小、按鈕變方形 icon-only on mobile */}
      <div className="flex gap-1.5 sm:gap-2 items-end">
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
          placeholder="輸入您的問題…"
          rows={1}
          className="flex-1 px-3 sm:px-4 py-2.5 sm:py-3 text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none max-h-32"
        />
        {messages.some(m => m.role === 'assistant' && !m.isError) && !loading && (
          <button
            onClick={regenerate}
            className="px-3 sm:px-4 py-2.5 sm:py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition"
            title="重新生成上一個回答"
          >
            🔄
          </button>
        )}
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          className="px-4 sm:px-6 py-2.5 sm:py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition whitespace-nowrap"
        >
          送出
        </button>
      </div>
    </div>
  )
}
