/**
 * AiSetupGuide — Chat 頁無 key 時顯示的友善 3 步申請引導卡（Sprint H v3.14）
 *
 * 設計：
 *  - 不是冷冰冰的 error，而是 actionable card（學 Odoo empty state）
 *  - 推薦 DeepSeek（最便宜、有免費額度）
 *  - 直接給「複製連結」+「跳轉設定頁」雙路徑
 */
import { Link } from 'react-router-dom'

interface Props {
  reason?: 'no_api_key' | 'invalid_key' | 'quota_exceeded'
  detectedIntent?: string
}

export default function AiSetupGuide({ reason = 'no_api_key', detectedIntent }: Props) {
  const title = {
    no_api_key: '🤖 AI 助手還沒啟用',
    invalid_key: '⚠️ API Key 無效',
    quota_exceeded: '⚠️ API 額度用完',
  }[reason]

  const subtitle = {
    no_api_key: '申請只要 3 分鐘 + 完全免費試用額度。跟著下面 3 步驟做：',
    invalid_key: '請到設定頁更新 API Key（可能過期或被撤銷）：',
    quota_exceeded: '到 DeepSeek 後台儲值，或換另一個 provider：',
  }[reason]

  return (
    <div className="my-4 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-start gap-3 mb-4">
        <div className="text-2xl">{reason === 'no_api_key' ? '🤖' : '⚠️'}</div>
        <div className="flex-1">
          <h3 className="font-semibold text-blue-900">{title}</h3>
          <p className="text-sm text-blue-700 mt-0.5">{subtitle}</p>
          {detectedIntent && (
            <p className="text-xs text-blue-600 mt-1">
              💡 我偵測到你想做：<code className="bg-white/60 px-1 rounded">{detectedIntent}</code>
            </p>
          )}
        </div>
      </div>

      {reason === 'no_api_key' && (
        <ol className="space-y-3 text-sm">
          <Step n={1} title="申請 DeepSeek API Key（推薦，超便宜 + 免費額度）">
            <a
              href="https://platform.deepseek.com/sign_up"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-1 px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
            >
              🌐 去 DeepSeek 註冊 →
            </a>
            <p className="text-xs text-gray-600 mt-1.5">
              步驟：① 註冊（email 或手機）→ ② 進「API Keys」→ ③ 點「Create new API Key」→ ④ 複製 <code>sk-...</code> 開頭的字串
            </p>
          </Step>

          <Step n={2} title="貼進 Ouvoca 設定頁">
            <Link
              to="/settings"
              className="inline-flex items-center gap-1 mt-1 px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
            >
              ⚙️ 去設定頁 →
            </Link>
            <p className="text-xs text-gray-600 mt-1.5">
              在「🤖 AI 助手設定」區塊貼入 key、點「測試連線」確認 OK、再點「儲存」即時生效。
            </p>
          </Step>

          <Step n={3} title="回來這頁重打剛才那句話">
            <p className="text-xs text-gray-600 mt-1">
              不需要重新整理 / 不需要重啟服務 — 設定完直接重發剛才的訊息即可。
            </p>
          </Step>
        </ol>
      )}

      {(reason === 'invalid_key' || reason === 'quota_exceeded') && (
        <div className="mt-3">
          <Link
            to="/settings"
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700"
          >
            ⚙️ 去設定頁更新 Key →
          </Link>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-blue-200 text-xs text-blue-700">
        <strong>不想申請？</strong> 你還是可以用所有「不需要 AI 的功能」：
        <Link to="/inventory" className="underline mx-1">庫存</Link>·
        <Link to="/purchase" className="underline mx-1">採購</Link>·
        <Link to="/sales" className="underline mx-1">銷售</Link>·
        <Link to="/production" className="underline mx-1">生產</Link>·
        <Link to="/" className="underline mx-1">儀表板</Link>
        <br />
        — Ouvoca 沒 API key 也跑得起來，只是少了「對話式 CRUD」這個賣點。
      </div>

      <div className="mt-3 text-xs text-blue-600">
        📖 完整申請教學：
        <a
          href="https://github.com/fanchanyu/ouvoca/blob/main/docs/HOW_TO_GET_LLM_API_KEY_ZH.md"
          target="_blank" rel="noopener noreferrer"
          className="underline ml-1"
        >
          docs/HOW_TO_GET_LLM_API_KEY_ZH.md
        </a>
        {' '}（含 3 個 provider 比較表）
      </div>
    </div>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
        {n}
      </div>
      <div className="flex-1">
        <p className="font-medium text-gray-800">{title}</p>
        {children}
      </div>
    </li>
  )
}
