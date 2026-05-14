import { ReactNode, HTMLAttributes } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  /** 是否帶 hover 動效（適合可點擊的卡片） */
  interactive?: boolean
  /** padding 預設 large；緊湊型可選 sm */
  padding?: 'sm' | 'md' | 'lg'
}

export function Card({
  children, interactive, padding = 'lg', className = '', ...rest
}: CardProps) {
  const padMap = { sm: 'p-4', md: 'p-5', lg: 'p-6' }
  return (
    <div
      className={[
        'bg-white rounded-card shadow-card border border-ink-100',
        padMap[padding],
        interactive && 'cursor-pointer hover:shadow-card-hover hover:border-brand-200 transition-all',
        className,
      ].filter(Boolean).join(' ')}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }: {
  title: string; subtitle?: string; action?: ReactNode
}) {
  return (
    <div className="flex justify-between items-start mb-4">
      <div>
        <h3 className="text-h3 text-ink-900">{title}</h3>
        {subtitle && <p className="text-body-sm text-ink-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
