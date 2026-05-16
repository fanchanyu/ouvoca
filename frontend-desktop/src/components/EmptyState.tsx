/**
 * EmptyState — reusable 空狀態卡（Sprint I v3.15）
 *
 * 學 Odoo / Linear / Notion：空表格不要冰冷地寫「無資料」，
 * 給使用者 actionable 出路：「先載示範資料」OR「新增第一筆」。
 *
 * 用法：
 *   <EmptyState
 *     icon="📦"
 *     title="你還沒有任何料件"
 *     subtitle="先載入示範資料試試手感，或直接新增第一個料件"
 *     primaryAction={{ label: '➕ 新增第一個料件', onClick: () => setShowCreate(true) }}
 *     secondaryAction={{ label: '📦 載入示範資料', to: '/settings' }}
 *   />
 */
import { Link } from 'react-router-dom'

interface Action {
  label: string
  onClick?: () => void
  to?: string
}

interface Props {
  icon?: string
  title: string
  subtitle?: string
  primaryAction?: Action
  secondaryAction?: Action
  /** 若為 true 用較緊湊的版面（表格 row 內 colSpan） */
  compact?: boolean
}

export default function EmptyState({
  icon = '📭', title, subtitle, primaryAction, secondaryAction, compact,
}: Props) {
  return (
    <div className={[
      'flex flex-col items-center justify-center text-center',
      compact ? 'py-8 px-4' : 'py-16 px-6',
    ].join(' ')}>
      <div className={compact ? 'text-4xl mb-2' : 'text-6xl mb-3'}>{icon}</div>
      <h3 className={[
        'font-semibold text-gray-800',
        compact ? 'text-base' : 'text-lg',
      ].join(' ')}>{title}</h3>
      {subtitle && (
        <p className={[
          'text-gray-500 mt-1 max-w-md',
          compact ? 'text-xs' : 'text-sm',
        ].join(' ')}>{subtitle}</p>
      )}
      {(primaryAction || secondaryAction) && (
        <div className="flex gap-2 mt-4">
          {primaryAction && <ActionButton action={primaryAction} variant="primary" />}
          {secondaryAction && <ActionButton action={secondaryAction} variant="secondary" />}
        </div>
      )}
    </div>
  )
}

function ActionButton({ action, variant }: { action: Action; variant: 'primary' | 'secondary' }) {
  const cls = variant === 'primary'
    ? 'px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors font-medium'
    : 'px-4 py-2 border border-blue-300 text-blue-700 rounded-lg text-sm hover:bg-blue-50 transition-colors'

  if (action.to) {
    return <Link to={action.to} className={cls}>{action.label}</Link>
  }
  return <button type="button" onClick={action.onClick} className={cls}>{action.label}</button>
}
