import { useState, useEffect, useRef } from 'react'
import { apiChat } from '../lib/api'

interface Msg { role: string; content: string; agent?: string }

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => 'sess-' + Math.random().toString(36).slice(2))
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      const data = await apiChat(text, sessionId)
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply || '(無回應)', agent: data.agent }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '連線錯誤'
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  const suggestions = [
    '列出庫存低於安全庫存的零件',
    '進行中的工單有哪些？',
    '本月有逾期的應收帳款嗎？',
    '列出進行中的不良品 (NC)',
  ]

  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      <h1 className="text-2xl font-bold mb-4">AI 助手</h1>
      <div ref={scrollRef} className="flex-1 bg-white rounded-xl shadow p-4 overflow-y-auto mb-4">
        {messages.length === 0 && (
          <div className="text-gray-400 text-center mt-20">
            <div className="mb-4">向 AI 助手詢問任何 ERP 相關問題</div>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestions.map(s => (
                <button key={s} onClick={() => setInput(s)} className="px-3 py-2 bg-gray-100 hover:bg-blue-50 text-xs rounded-full">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`mb-3 ${msg.role === 'user' ? 'text-right' : ''}`}>
            <div className={`inline-block px-4 py-2 rounded-xl max-w-[80%] whitespace-pre-wrap break-words ${
              msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'
            }`}>
              {msg.content}
            </div>
            {msg.agent && msg.role === 'assistant' && (
              <div className="text-xs text-gray-400 mt-1 ml-2">→ {msg.agent}</div>
            )}
          </div>
        ))}
        {loading && <div className="text-gray-400">🤔 思考中…</div>}
      </div>
      <div className="flex gap-2">
        <input
          type="text" value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="輸入您的問題…"
          className="flex-1 px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button onClick={send} disabled={loading} className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50">
          送出
        </button>
      </div>
    </div>
  )
}
