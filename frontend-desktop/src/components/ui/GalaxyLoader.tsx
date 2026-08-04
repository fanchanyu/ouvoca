/** GalaxyLoader — 載入動畫（樣式取自 uiverse-io/galaxy，MIT）。 */
export default function GalaxyLoader({ label }: { label?: string }) {
  return (
    <div className="inline-flex items-center gap-2 text-sm text-gray-500">
      <span className="galaxy-loader" />
      {label ? <span>{label}</span> : null}
    </div>
  )
}
