import { ReactNode } from 'react'

type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info'
type Size = 'sm' | 'md'

interface BadgeProps {
  children: ReactNode
  tone?: Tone
  size?: Size
  dot?: boolean
}

const toneMap: Record<Tone, string> = {
  neutral: 'bg-ink-100 text-ink-700',
  brand:   'bg-brand-100 text-brand-700',
  success: 'bg-success-50 text-success-700',
  warning: 'bg-warning-50 text-warning-700',
  danger:  'bg-danger-50 text-danger-700',
  info:    'bg-brand-50 text-brand-700',
}

const sizeMap: Record<Size, string> = {
  sm: 'px-2 py-0.5 text-caption',
  md: 'px-2.5 py-1 text-body-sm',
}

const dotMap: Record<Tone, string> = {
  neutral: 'bg-ink-500',
  brand:   'bg-brand-500',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger:  'bg-danger-500',
  info:    'bg-brand-500',
}

export function Badge({ children, tone = 'neutral', size = 'sm', dot }: BadgeProps) {
  return (
    <span className={[
      'inline-flex items-center gap-1.5 rounded-full font-medium nowrap-cjk',
      toneMap[tone], sizeMap[size],
    ].join(' ')}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotMap[tone]}`} />}
      {children}
    </span>
  )
}

/** 統一的訂單/工單狀態 → tone + 中文標籤 */
export const STATUS_MAP: Record<string, { label: string; tone: Tone }> = {
  draft:             { label: '草稿',     tone: 'neutral' },
  pending:           { label: '待處理',   tone: 'neutral' },
  approved:          { label: '已核准',   tone: 'brand' },
  confirmed:         { label: '已確認',   tone: 'brand' },
  released:          { label: '已釋放',   tone: 'info' },
  in_progress:       { label: '進行中',   tone: 'success' },
  partial_received:  { label: '部分收貨', tone: 'warning' },
  received:          { label: '已收貨',   tone: 'success' },
  shipped:           { label: '已出貨',   tone: 'success' },
  completed:         { label: '已完成',   tone: 'success' },
  cancelled:         { label: '已取消',   tone: 'danger' },
  rejected:          { label: '退回',     tone: 'danger' },
}

export function StatusBadge({ status, dot = true }: { status: string; dot?: boolean }) {
  const cfg = STATUS_MAP[status] || { label: status, tone: 'neutral' as Tone }
  return <Badge tone={cfg.tone} dot={dot}>{cfg.label}</Badge>
}
