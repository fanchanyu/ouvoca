/**
 * ProcessChain — 流程鏈視覺化（Sprint P v3.22）
 *
 * 對標 SAP B1 Process Flow Chart：
 *   讓使用者一眼看出「這張單據在流程鏈的哪一步、後面還會發生什麼」
 *
 * 用法：
 *   <ProcessChain steps={[
 *     { label: '建立',   status: 'done',    date: '5/15' },
 *     { label: '核准',   status: 'done',    date: '5/16' },
 *     { label: '進貨',   status: 'current', hint: 'NT$50K' },
 *     { label: '應付',   status: 'pending' },
 *     { label: '付款',   status: 'pending' },
 *   ]} />
 *
 * 視覺：水平 5 圓圈 + 連接線，狀態用顏色區分。
 */
export type StepStatus = 'done' | 'current' | 'pending' | 'skipped' | 'cancelled'

export interface ProcessStep {
  label: string
  status: StepStatus
  icon?: string
  date?: string
  hint?: string
  onClick?: () => void
}

interface Props {
  steps: ProcessStep[]
  title?: string
}

const STATUS_STYLE: Record<StepStatus, { circle: string; text: string; icon: string }> = {
  done:      { circle: 'bg-emerald-500 text-white border-emerald-600',  text: 'text-emerald-700',  icon: '✓' },
  current:   { circle: 'bg-blue-500 text-white border-blue-600 animate-pulse-soft', text: 'text-blue-700 font-semibold',     icon: '▶' },
  pending:   { circle: 'bg-gray-200 text-gray-400 border-gray-300',     text: 'text-gray-400',     icon: '○' },
  skipped:   { circle: 'bg-amber-100 text-amber-700 border-amber-300',  text: 'text-amber-600',    icon: '⏭' },
  cancelled: { circle: 'bg-red-100 text-red-700 border-red-300 line-through', text: 'text-red-600 line-through', icon: '✕' },
}

export default function ProcessChain({ steps, title }: Props) {
  if (steps.length === 0) return null

  return (
    <div className="bg-white rounded-lg p-4">
      {title && <h3 className="font-semibold text-sm mb-3 text-gray-700">{title}</h3>}
      <div className="flex items-start gap-1 overflow-x-auto pb-2">
        {steps.map((step, i) => {
          const style = STATUS_STYLE[step.status]
          const isLast = i === steps.length - 1
          return (
            <div key={i} className="flex items-start flex-shrink-0">
              {/* 圓圈 + label */}
              <button
                onClick={step.onClick}
                disabled={!step.onClick}
                className={[
                  'flex flex-col items-center gap-1 min-w-[80px]',
                  step.onClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default',
                ].join(' ')}
                title={step.hint || step.label}
              >
                <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center text-base ${style.circle}`}>
                  {step.icon || style.icon}
                </div>
                <div className={`text-xs ${style.text} text-center max-w-[100px] leading-tight`}>
                  {step.label}
                </div>
                {step.date && (
                  <div className="text-[10px] text-gray-400 font-mono">{step.date}</div>
                )}
                {step.hint && (
                  <div className={`text-[10px] ${style.text} text-center max-w-[100px] truncate`} title={step.hint}>
                    {step.hint}
                  </div>
                )}
              </button>

              {/* 連接線 */}
              {!isLast && (
                <div className="flex items-center h-10 px-1">
                  <div className={[
                    'w-8 h-0.5 transition-colors',
                    step.status === 'done' ? 'bg-emerald-400' :
                    step.status === 'current' ? 'bg-gradient-to-r from-blue-400 to-gray-300' :
                    'bg-gray-200',
                  ].join(' ')} />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────
// Status → Steps 推導 helper（依單據類型）
// ──────────────────────────────────────────────────────────

/** 採購流程 P2P：依 PO status 產生 5 步驟 */
export function deriveP2PSteps(poStatus: string, poDate?: string): ProcessStep[] {
  const isCancelled = poStatus === 'cancelled'
  const stage = {
    draft: 1, approved: 2, sent: 2, partial_received: 3, received: 4,
  }[poStatus] || 0

  const stepStatus = (s: number): StepStatus =>
    isCancelled ? 'cancelled' :
    s < stage ? 'done' :
    s === stage ? 'current' :
    'pending'

  return [
    { label: 'PO 建立',  icon: '📋', status: stage >= 1 ? (isCancelled ? 'cancelled' : 'done') : 'pending', date: poDate },
    { label: '已核准',   icon: '✓',  status: stepStatus(2) },
    { label: '進貨中',   icon: '🚚', status: stepStatus(3), hint: stage === 3 ? '部分收貨' : undefined },
    { label: '應付帳款', icon: '💳', status: stepStatus(4) },
    { label: '付款',     icon: '💰', status: stage > 4 ? 'done' : 'pending', hint: '待 AP module' },
  ]
}

/** 銷售流程 O2C：依 SO status 產生 5 步驟 */
export function deriveO2CSteps(soStatus: string, soDate?: string): ProcessStep[] {
  const isCancelled = soStatus === 'cancelled'
  const stage = {
    draft: 1, confirmed: 2, production: 2, ready_to_ship: 2, shipped: 3, delivered: 4, closed: 5,
  }[soStatus] || 0

  const stepStatus = (s: number): StepStatus =>
    isCancelled ? 'cancelled' :
    s < stage ? 'done' :
    s === stage ? 'current' :
    'pending'

  return [
    { label: 'SO 建立',  icon: '📝', status: stage >= 1 ? (isCancelled ? 'cancelled' : 'done') : 'pending', date: soDate },
    { label: '已確認',   icon: '✓',  status: stepStatus(2) },
    { label: '出貨',     icon: '📦', status: stepStatus(3) },
    { label: '應收帳款', icon: '💵', status: stepStatus(4) },
    { label: '收款',     icon: '💰', status: stage >= 5 ? 'done' : 'pending', hint: '待 AR 結清' },
  ]
}

/** 生產流程：依 WO status 產生 5 步驟 */
export function deriveWOSteps(woStatus: string, completedQty?: number, orderedQty?: number): ProcessStep[] {
  const isCancelled = woStatus === 'cancelled'
  const stage = {
    draft: 1, released: 2, in_progress: 3, completed: 4,
  }[woStatus] || 0

  const stepStatus = (s: number): StepStatus =>
    isCancelled ? 'cancelled' :
    s < stage ? 'done' :
    s === stage ? 'current' :
    'pending'

  return [
    { label: 'WO 建立',  icon: '🏭', status: stage >= 1 ? (isCancelled ? 'cancelled' : 'done') : 'pending' },
    { label: '釋放產線', icon: '▶',  status: stepStatus(2) },
    { label: '生產中',   icon: '⚙️', status: stepStatus(3),
      hint: completedQty != null && orderedQty != null ? `${completedQty}/${orderedQty}` : undefined },
    { label: '完工',     icon: '✓',  status: stepStatus(4) },
    { label: '入庫',     icon: '📦', status: stage > 4 ? 'done' : 'pending', hint: '自動進庫存交易' },
  ]
}
