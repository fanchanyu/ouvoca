// Loading skeleton 元件 — 取代「載入中...」純文字

export function Skeleton({ className = '', width, height }: {
  className?: string; width?: string; height?: string
}) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height: height || '1rem' }}
    />
  )
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height="0.75rem" width={i === lines - 1 ? '60%' : '100%'} />
      ))}
    </div>
  )
}

/** 給統計卡片用的骨架 */
export function SkeletonStatCard() {
  return (
    <div className="bg-white rounded-card shadow-card border border-ink-100 p-6">
      <Skeleton width="40%" height="0.875rem" />
      <div className="mt-3">
        <Skeleton width="60%" height="2.5rem" />
      </div>
      <div className="mt-2">
        <Skeleton width="30%" height="0.75rem" />
      </div>
    </div>
  )
}

/** 給表格列用的骨架 */
export function SkeletonRow({ cols = 4 }: { cols?: number }) {
  return (
    <tr className="border-t border-ink-100">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-3">
          <Skeleton height="0.875rem" />
        </td>
      ))}
    </tr>
  )
}
