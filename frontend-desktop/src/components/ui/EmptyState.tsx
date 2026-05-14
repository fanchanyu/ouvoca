import { ReactNode } from 'react'

interface EmptyStateProps {
  icon?: ReactNode | string
  title: string
  description?: string
  action?: ReactNode
  variant?: 'default' | 'compact'
}

export function EmptyState({
  icon = '📭', title, description, action, variant = 'default',
}: EmptyStateProps) {
  return (
    <div className={[
      'flex flex-col items-center justify-center text-center animate-fade-in',
      variant === 'compact' ? 'py-6' : 'py-12',
    ].join(' ')}>
      <div className={[
        'flex items-center justify-center rounded-full bg-ink-100',
        variant === 'compact' ? 'w-12 h-12 text-2xl' : 'w-20 h-20 text-4xl',
      ].join(' ')}>
        {typeof icon === 'string' ? <span>{icon}</span> : icon}
      </div>
      <h3 className={[
        'text-ink-700 mt-4',
        variant === 'compact' ? 'text-body font-medium' : 'text-h3',
      ].join(' ')}>{title}</h3>
      {description && (
        <p className="text-body-sm text-ink-500 mt-2 max-w-md">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
