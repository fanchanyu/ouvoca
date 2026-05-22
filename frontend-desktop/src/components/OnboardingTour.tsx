/**
 * OnboardingTour — 第一次登入歡迎引導（Sprint I v3.15）
 *
 * 學 Notion / Linear：first-time user 跳出 4 步驟卡，把最重要的事介紹完，
 * 點「下次再說」會關掉並 localStorage 記住 → 永遠不再跳。
 *
 * 4 步驟：
 *  1. 歡迎 + Ouvoca 是什麼
 *  2. 載入示範資料（不想等帶我去 settings）
 *  3. 申請 LLM API Key 啟用 AI 對話（不想等帶我去 settings）
 *  4. 4 個快速試試（chat / 庫存 / 銷售 / 設定）
 *
 * 觸發條件：
 *  - localStorage 沒 ouvoca_onboarding_done flag
 *  - 在 Layout 內全頁顯示（modal）
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const LS_KEY = 'ouvoca_onboarding_done'

export default function OnboardingTour() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(0)

  useEffect(() => {
    const done = localStorage.getItem(LS_KEY)
    if (!done) {
      // 1 秒後彈出，避免和登入畫面動畫衝突
      const t = setTimeout(() => setOpen(true), 800)
      return () => clearTimeout(t)
    }
  }, [])

  function dismiss() {
    localStorage.setItem(LS_KEY, '1')
    setOpen(false)
  }

  function neverShow() {
    localStorage.setItem(LS_KEY, '1')
    setOpen(false)
  }

  if (!open) return null

  const steps = [
    {
      icon: '👋',
      title: '歡迎使用 Ouvoca',
      body: (
        <>
          <p>Ouvoca 是給 50-100 人小型製造業的<strong>對話式 ERP</strong>。</p>
          <p className="mt-2">不用學系統、不用受訓 — <strong>用講的就會用</strong>。</p>
          <p className="mt-2 text-sm text-gray-500">
            這個歡迎引導會帶你 4 步走完最重要的設定。隨時可以 [下次再說]。
          </p>
        </>
      ),
    },
    {
      icon: '📦',
      title: '第 1 件事：載入示範資料',
      body: (
        <>
          <p>系統已經幫你建好<strong>5 個客戶 / 3 個供應商 / 10 個料件</strong>的示範資料（DEMO- 前綴）。</p>
          <p className="mt-2">不喜歡可以隨時清掉、再載你自己的。</p>
          <Link
            to="/settings" onClick={dismiss}
            className="inline-block mt-3 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            ⚙️ 去設定頁管理示範資料 →
          </Link>
        </>
      ),
    },
    {
      icon: '🤖',
      title: '第 2 件事：啟用 AI 助手（選做）',
      body: (
        <>
          <p>沒申請 API Key 也能用所有 ERP 功能。</p>
          <p className="mt-2">但如果你想要<strong>用講的</strong>查/增/改/刪資料，需要花 5 分鐘申請：</p>
          <ul className="mt-2 ml-4 text-sm list-disc">
            <li>推薦 <strong>DeepSeek</strong>（最便宜、中文最強）</li>
            <li>註冊 → 拿 API Key → 貼到設定頁</li>
          </ul>
          <Link
            to="/settings" onClick={dismiss}
            className="inline-block mt-3 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            ⚙️ 去設定頁啟用 AI →
          </Link>
        </>
      ),
    },
    {
      icon: '🎯',
      title: '快速試試這 4 件事',
      body: (
        <>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <QuickLink to="/chat" icon="💬" label="AI 助手" desc="對 AI 講話" onClick={dismiss} />
            <QuickLink to="/inventory" icon="📦" label="庫存" desc="看料件 / 安全庫存" onClick={dismiss} />
            <QuickLink to="/sales" icon="💰" label="銷售" desc="客戶 / 訂單" onClick={dismiss} />
            <QuickLink to="/crm" icon="🤝" label="CRM" desc="Lead / 商機" onClick={dismiss} />
          </div>
          <p className="mt-3 text-sm text-gray-500">
            隨時可以從左側 sidebar 切換頁面。完成 ✅
          </p>
        </>
      ),
    },
  ]

  const cur = steps[step]
  const isLast = step === steps.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 animate-slide-up">
        <div className="flex items-start justify-between mb-3">
          <div className="text-4xl">{cur.icon}</div>
          <button
            onClick={neverShow}
            className="text-xs text-gray-400 hover:text-gray-600"
            title="不再顯示"
          >
            下次再說 ✕
          </button>
        </div>

        <h2 className="text-xl font-bold text-gray-800 mb-2">{cur.title}</h2>
        <div className="text-gray-600 text-sm">{cur.body}</div>

        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
          <div className="flex gap-1.5">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${i === step ? 'bg-blue-600 w-8' : 'bg-gray-300'} transition-all`}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {step > 0 && (
              <button
                onClick={() => setStep(s => s - 1)}
                className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
              >
                上一步
              </button>
            )}
            {isLast ? (
              <button
                onClick={dismiss}
                className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 font-medium"
              >
                ✅ 開始使用
              </button>
            ) : (
              <button
                onClick={() => setStep(s => s + 1)}
                className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 font-medium"
              >
                下一步 →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function QuickLink({ to, icon, label, desc, onClick }: {
  to: string; icon: string; label: string; desc: string; onClick: () => void
}) {
  return (
    <Link
      to={to} onClick={onClick}
      className="border border-gray-200 rounded-lg p-3 hover:border-blue-400 hover:bg-blue-50 transition-colors"
    >
      <div className="flex items-center gap-2">
        <span className="text-xl">{icon}</span>
        <div>
          <div className="font-medium text-sm text-gray-800">{label}</div>
          <div className="text-xs text-gray-500">{desc}</div>
        </div>
      </div>
    </Link>
  )
}
