import { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
  children?: ReactNode
}

const variantMap: Record<Variant, string> = {
  primary:   'bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800',
  secondary: 'bg-white border border-ink-300 text-ink-700 hover:bg-ink-50',
  ghost:     'text-ink-600 hover:bg-ink-100',
  danger:    'bg-danger-600 text-white hover:bg-danger-700',
}

const sizeMap: Record<Size, string> = {
  // 確保最小觸控目標 44×44px（給手機/老人友善）
  sm: 'h-9 px-3 text-body-sm gap-1.5',
  md: 'h-11 px-4 text-body gap-2',
  lg: 'h-12 px-6 text-body-lg gap-2.5',
}

export function Button({
  variant = 'primary', size = 'md',
  loading, disabled, icon, children, className = '', ...rest
}: ButtonProps) {
  return (
    <button
      className={[
        'inline-flex items-center justify-center rounded-input font-medium',
        'transition-colors focus-ring',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantMap[variant], sizeMap[size], className,
      ].join(' ')}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
          <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </svg>
      )}
      {!loading && icon}
      {children}
    </button>
  )
}
