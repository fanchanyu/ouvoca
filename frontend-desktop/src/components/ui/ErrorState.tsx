interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  compact?: boolean
}

export function ErrorState({
  title = '載入失敗', message, onRetry, compact,
}: ErrorStateProps) {
  return (
    <div className={[
      'flex flex-col items-center justify-center text-center animate-fade-in',
      compact ? 'py-6' : 'py-12',
    ].join(' ')}>
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-danger-50 text-3xl">
        ⚠️
      </div>
      <h3 className="text-h3 text-danger-700 mt-4">{title}</h3>
      <p className="text-body-sm text-ink-600 mt-2 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 px-4 py-2 bg-danger-600 hover:bg-danger-700 text-white rounded-input font-medium transition-colors focus-ring"
        >
          重試
        </button>
      )}
    </div>
  )
}
