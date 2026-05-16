/**
 * AskAiFloat — 右下角浮球：每頁的「AI 現場教練」（Sprint J v3.16）
 *
 * erpilot 原創 UX 哲學：
 *   傳統 ERP: 「每欄位掛 ? help bubble」「漂亮 onboarding tour」「FAQ 翻 5 層」
 *   erpilot: 「不知道怎麼用？問 AI 就會」← 把 AI 變成現場教練
 *
 * 設計：
 *  - 右下角浮 💡 球（脈衝動畫吸引注意）
 *  - 點開展開為迷你 chat：預設帶當前頁面 context
 *  - 範例 prompt 三鍵：「這頁怎麼做 X」「這個欄位是什麼意思」「我卡住了」
 *  - 送出 → 呼叫 chat API → 顯示回答
 *  - 沒 LLM key → 顯示 AiSetupGuide 引導申請
 *
 * 為什麼這比 onboarding tour / EmptyState 更 erpilot 風：
 *  - tour: 第一次看完就不會再幫你
 *  - help bubble: 預先寫死的文字，沒辦法回答你真正的問題
 *  - **AskAI**: 隨時都在、上下文相關、能回答任何問題、學的越多越聰明
 */
import { useEffect, useRef, useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { apiChat } from '../lib/api'
import AiSetupGuide from './AiSetupGuide'

interface Reply {
  q: string
  a: string
  setupRequired?: boolean
  ts: number
}

// 不同頁面的脈絡描述（送給 LLM 當 context 增強）
const PAGE_CONTEXT: Record<string, string> = {
  '/':              '使用者在儀表板首頁，可看 KPI 與快速 chat',
  '/chat':          '使用者在 AI 助手對話頁',
  '/inventory':     '使用者在庫存管理頁（料件、安全庫存、庫存交易）',
  '/purchase':      '使用者在採購管理頁（供應商、採購單、進貨）',
  '/production':    '使用者在生產管理頁（工單、釋放、進度）',
  '/sales':         '使用者在銷售管理頁（客戶、銷售單、出貨）',
  '/crm':           '使用者在 CRM 頁（Lead 漏斗、商機 Kanban、客戶 360）',
  '/quality':       '使用者在品質管理頁（檢驗、NC、CAPA，唯讀稽核記錄）',
  '/events':        '使用者在事件流頁（即時 SSE）',
  '/permissions':   '使用者在權限管理頁（角色、權限分派）',
  '/me/permissions': '使用者在我的權限頁',
  '/settings':      '使用者在系統設定頁（AI / Demo / 上傳 / 系統資訊）',
}

const SUGGESTIONS = [
  '這頁怎麼用？',
  '我卡住了，下一步該做什麼？',
  '這頁有哪些常用功能？',
]

export default function AskAiFloat() {
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [replies, setReplies] = useState<Reply[]>([])
  const [sessionId] = useState(() => 'ask-' + Math.random().toString(36).slice(2))
  const inputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // 切頁時關掉
  useEffect(() => { setOpen(false) }, [location.pathname])

  // 開啟時 focus
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100)
  }, [open])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [replies, loading])

  async function ask(text?: string) {
    const q = (text ?? input).trim()
    if (!q || loading) return
    setLoading(true)
    setInput('')
    try {
      // 把當前頁面 context 包進使用者訊息（讓 LLM 知道使用者在哪）
      const ctx = PAGE_CONTEXT[location.pathname] || `使用者在 ${location.pathname} 頁`
      const augmented = `[上下文：${ctx}]\n\n問題：${q}`
      const data = await apiChat(augmented, sessionId)
      setReplies(prev => [...prev, {
        q,
        a: data.reply || '(無回應)',
        setupRequired: data.setup_required,
        ts: Date.now(),
      }])
    } catch (e: unknown) {
      setReplies(prev => [...prev, {
        q,
        a: `❌ ${e instanceof Error ? e.message : '連線錯誤'}`,
        ts: Date.now(),
      }])
    } finally { setLoading(false) }
  }

  return (
    <>
      {/* 浮球 — 永遠在右下 */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center group"
          title="問 AI：在這頁怎麼做什麼？"
          aria-label="問 AI"
        >
          <span className="text-2xl">💡</span>
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
          <span className="absolute right-full mr-3 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
            問 AI 怎麼用這頁
          </span>
        </button>
      )}

      {/* 展開的迷你 chat */}
      {open && (
        <div className="fixed bottom-6 right-6 z-40 w-96 max-w-[calc(100vw-2rem)] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col animate-slide-up" style={{ maxHeight: 'calc(100vh - 6rem)' }}>
          {/* Header */}
          <div className="flex items-center justify-between p-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-t-2xl">
            <div className="flex items-center gap-2">
              <span className="text-xl">💡</span>
              <div>
                <div className="font-semibold text-sm">問 AI — 現場教練</div>
                <div className="text-xs opacity-75">針對你現在這頁回答</div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-white/80 hover:text-white p-1"
              aria-label="關閉"
            >✕</button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3" style={{ maxHeight: 'calc(100vh - 16rem)' }}>
            {replies.length === 0 && (
              <div className="text-center py-4">
                <div className="text-3xl mb-2">🎓</div>
                <div className="text-sm font-medium text-gray-700">我會在這頁陪你</div>
                <div className="text-xs text-gray-500 mt-1">
                  問我「怎麼用這頁」「這個欄位是什麼」「我卡住了」
                </div>
                <div className="flex flex-wrap gap-1.5 justify-center mt-3">
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      onClick={() => ask(s)}
                      disabled={loading}
                      className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 disabled:opacity-50 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {replies.map((r, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-end">
                  <div className="bg-blue-600 text-white text-sm rounded-2xl rounded-br-sm px-3 py-2 max-w-[85%]">
                    {r.q}
                  </div>
                </div>
                <div className="flex justify-start">
                  {r.setupRequired ? (
                    <div className="max-w-[95%]">
                      <AiSetupGuide reason="no_api_key" />
                    </div>
                  ) : (
                    <div className="bg-gray-100 text-gray-800 text-sm rounded-2xl rounded-bl-sm px-3 py-2 max-w-[85%] whitespace-pre-wrap break-words">
                      {r.a}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-500 text-sm rounded-2xl px-3 py-2 italic">
                  AI 思考中…
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-100">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && ask()}
                placeholder="問我「怎麼用這頁」…"
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                disabled={loading}
              />
              <button
                onClick={() => ask()}
                disabled={loading || !input.trim()}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                ➤
              </button>
            </div>
            <div className="text-xs text-gray-400 mt-1.5 text-center">
              💡 進階對話請去
              <Link to="/chat" className="text-blue-600 underline mx-1" onClick={() => setOpen(false)}>
                AI 助手
              </Link>
              頁
            </div>
          </div>
        </div>
      )}
    </>
  )
}
