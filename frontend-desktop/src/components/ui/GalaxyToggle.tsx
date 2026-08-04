/**
 * GalaxyToggle — 設定開關（樣式取自 uiverse-io/galaxy，MIT）。
 * 用法：<GalaxyToggle checked={x} onChange={setX} label="啟用 MFA" />
 */
interface Props {
  checked: boolean
  onChange: (v: boolean) => void
  label?: string
  disabled?: boolean
}

export default function GalaxyToggle({ checked, onChange, label, disabled }: Props) {
  return (
    <label className="inline-flex items-center gap-2 cursor-pointer select-none">
      <span className="galaxy-toggle">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="track" />
      </span>
      {label ? <span className="text-sm text-gray-700">{label}</span> : null}
    </label>
  )
}
