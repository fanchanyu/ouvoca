/**
 * OnboardingWizard — 第一次登入引導（v3.10 Track D）。
 *
 * 顯示時機：Dashboard 載入時若 onboarding/status 顯示沒任何資料 → 自動彈出
 * 流程：
 *   1. 歡迎 → 介紹 5 大功能
 *   2. 一鍵載入 demo 資料（5 客戶 / 3 供應商 / 10 料件）
 *   3. 試對話：建議幾個 Chat 範例
 *   4. 完成
 */
import { useState } from 'react'
import { apiSeedDemo, type OnboardingStatus } from '../lib/api'

interface Props {
  initialStatus: OnboardingStatus | null
  onClose: () => void
  onCompleted?: () => void
}

const STEPS = [
  { key: 'welcome', title: '歡迎' },
  { key: 'demo',    title: '載入示範資料' },
  { key: 'chat',    title: '試對話' },
  { key: 'done',    title: '完成' },
] as const

const SUGGESTED_QUERIES = [
  '今天工廠狀況？',
  '哪些料件低於安全庫存？',
  '幫我新增料件 M6 螺絲 安全庫存 500',
  '跟示範供應商長江下 100 個 M6 螺絲，交期 2026-06-30',
  '最近的採購單',
  '把鼎新客戶搬過來（需先設外部 DB 連接）',
]

export default function OnboardingWizard({ initialStatus, onClose, onCompleted }: Props) {
  const [step, setStep] = useState<number>(0)
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState<string | null>(null)
  const [seedError, setSeedError] = useState<string | null>(null)

  const handleSeed = async () => {
    setSeeding(true)
    setSeedError(null)
    try {
      const r = await apiSeedDemo()
      setSeedResult(r.message)
      setStep(2)
      onCompleted?.()
    } catch (e) {
      setSeedError(e instanceof Error ? e.message : '載入失敗')
    } finally {
      setSeeding(false)
    }
  }

  const handleSkip = () => {
    setStep(2)
  }

  return (
    <div className="fixed inset-0 z-50 bg-ink-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="bg-gradient-to-r from-brand-500 to-brand-700 px-6 py-4 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">🚀 LLM-ERP 快速上手 — {STEPS[step].title}</h2>
              <p className="text-xs text-white/80 mt-1">
                第 {step + 1} 步 / 共 {STEPS.length} 步
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-white/70 hover:text-white text-2xl leading-none"
              aria-label="關閉"
            >
              ×
            </button>
          </div>
          {/* Progress dots */}
          <div className="flex gap-1.5 mt-3">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-all ${
                  i <= step ? 'bg-white' : 'bg-white/30'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="p-6 min-h-[300px]">
          {step === 0 && (
            <div className="space-y-4">
              <p className="text-lg text-ink-800">
                歡迎使用 <strong>LLM-ERP</strong> — 給中小企業的對話式 ERP。
              </p>
              <ul className="space-y-2 text-ink-700">
                <li>💬 <strong>用講的就能下單 / 改單 / 查報表</strong>，員工 2 小時上手</li>
                <li>🛡 <strong>ConfirmCard 確認卡</strong>避免誤操作；90 秒內可 Undo</li>
                <li>🔌 <strong>連得到鼎新 / 正航 / Excel</strong>，舊系統不用砍</li>
                <li>📊 <strong>401 / 應收帳齡 / 庫存月報</strong>一鍵輸出</li>
                <li>🌐 <strong>多廠 MESH</strong>同步</li>
              </ul>
              <p className="text-sm text-ink-500 mt-4">
                第一步：載入示範資料（5 客戶 / 3 供應商 / 10 料件），讓你立刻試所有功能。
              </p>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              {!seedResult && (
                <>
                  <p className="text-ink-700">
                    將載入：
                  </p>
                  <ul className="grid grid-cols-3 gap-3 text-sm">
                    <li className="bg-brand-50 p-3 rounded-lg">
                      <div className="font-bold text-brand-700">5 個客戶</div>
                      <div className="text-xs text-ink-500 mt-1">A/B/C 等級各幾個</div>
                    </li>
                    <li className="bg-brand-50 p-3 rounded-lg">
                      <div className="font-bold text-brand-700">3 個供應商</div>
                      <div className="text-xs text-ink-500 mt-1">T1 / T2 等級</div>
                    </li>
                    <li className="bg-brand-50 p-3 rounded-lg">
                      <div className="font-bold text-brand-700">10 個料件</div>
                      <div className="text-xs text-ink-500 mt-1">含 2 個刻意低於安全庫存</div>
                    </li>
                  </ul>
                  <p className="text-xs text-ink-500">
                    所有 demo 資料用 <code className="bg-ink-100 px-1 rounded">DEMO-</code>
                    前綴，之後可以一鍵清空。
                  </p>
                  {initialStatus && initialStatus.has_demo_data && (
                    <div className="bg-amber-50 border border-amber-200 px-3 py-2 rounded text-sm text-amber-800">
                      ⚠️ 偵測到已有 DEMO 資料（{initialStatus.demo_customers} 客戶 /
                      {initialStatus.demo_suppliers} 供應商 / {initialStatus.demo_parts} 料件）
                      — 重複執行會跳過已存在
                    </div>
                  )}
                </>
              )}
              {seedResult && (
                <div className="bg-green-50 border border-green-200 p-4 rounded-lg">
                  <div className="font-bold text-green-800 mb-1">✅ 完成</div>
                  <div className="text-sm text-green-700">{seedResult}</div>
                </div>
              )}
              {seedError && (
                <div className="bg-red-50 border border-red-200 px-3 py-2 rounded text-sm text-red-800">
                  ❌ {seedError}
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3">
              <p className="text-ink-700">
                到 <strong>AI 助手</strong>頁面，試試這幾個句子：
              </p>
              <div className="grid grid-cols-1 gap-2">
                {SUGGESTED_QUERIES.map(q => (
                  <div
                    key={q}
                    className="bg-ink-50 px-3 py-2 rounded border border-ink-200 text-sm font-mono"
                  >
                    💬 {q}
                  </div>
                ))}
              </div>
              <p className="text-xs text-ink-500 mt-3">
                寫入操作（建單 / 改料）會跳出 ConfirmCard 確認卡，點確認才執行 — 安全。
              </p>
            </div>
          )}

          {step === 3 && (
            <div className="text-center space-y-4">
              <div className="text-5xl">🎉</div>
              <h3 className="text-xl font-bold text-ink-900">完成！</h3>
              <p className="text-ink-700">
                建議下一步：
              </p>
              <ul className="text-left space-y-1 text-sm text-ink-600 max-w-md mx-auto">
                <li>✅ 跟 IT 設一個 <strong>外部 DB 連接</strong>（鼎新 / 正航 / Excel）</li>
                <li>✅ 客製 <strong>角色與權限</strong> — 「我的權限」頁面</li>
                <li>✅ 設定 <strong>每日 Email 摘要</strong>（給老闆）</li>
                <li>✅ 試 <strong>401 / 庫存月報</strong>輸出</li>
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-ink-50 px-6 py-4 flex justify-between items-center border-t">
          <button
            onClick={onClose}
            className="text-sm text-ink-500 hover:text-ink-700"
          >
            略過引導
          </button>
          <div className="flex gap-2">
            {step > 0 && step < STEPS.length - 1 && (
              <button
                onClick={() => setStep(s => s - 1)}
                className="px-4 py-2 border border-ink-300 rounded-lg text-ink-700 hover:bg-ink-100 transition"
              >
                上一步
              </button>
            )}
            {step === 0 && (
              <button
                onClick={() => setStep(1)}
                className="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition font-medium"
              >
                開始 →
              </button>
            )}
            {step === 1 && !seedResult && (
              <>
                <button
                  onClick={handleSkip}
                  className="px-4 py-2 border border-ink-300 rounded-lg text-ink-700 hover:bg-ink-100 transition"
                >
                  跳過
                </button>
                <button
                  onClick={handleSeed}
                  disabled={seeding}
                  className="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition font-medium"
                >
                  {seeding ? '載入中…' : '✓ 載入示範資料'}
                </button>
              </>
            )}
            {step === 1 && seedResult && (
              <button
                onClick={() => setStep(2)}
                className="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition font-medium"
              >
                下一步 →
              </button>
            )}
            {step === 2 && (
              <button
                onClick={() => setStep(3)}
                className="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition font-medium"
              >
                下一步 →
              </button>
            )}
            {step === 3 && (
              <button
                onClick={onClose}
                className="px-5 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition font-medium"
              >
                ✓ 開始使用
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
