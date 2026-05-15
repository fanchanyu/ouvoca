import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { apiChat } from '../lib/api'

interface Msg {
  role: 'user' | 'assistant' | 'system'
  content: string
  agent?: string
  timestamp?: number
  isError?: boolean
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
  const [sessionId] = useState(() => 'sess-' + Math.random().toString(36).slice(2))
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 自動捲到底
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

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
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply || '(無回應)',
        agent: data.agent,
        timestamp: Date.now(),
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
            <span>AI 思考中…</span>
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
