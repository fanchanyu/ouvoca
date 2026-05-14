// 格式化工具：數字、貨幣、日期、相對時間

export const fmtNumber = (n: number | null | undefined, opts: { fractionDigits?: number } = {}) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-TW', {
    minimumFractionDigits: opts.fractionDigits ?? 0,
    maximumFractionDigits: opts.fractionDigits ?? 0,
  })
}

export const fmtCurrency = (n: number | null | undefined, currency = 'TWD') => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-TW', { style: 'currency', currency, maximumFractionDigits: 0 })
}

export const fmtPercent = (n: number | null | undefined, fractionDigits = 1) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return `${(n * 100).toFixed(fractionDigits)}%`
}

export const fmtDate = (d: string | Date | null | undefined) => {
  if (!d) return '—'
  const date = typeof d === 'string' ? new Date(d) : d
  return date.toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export const fmtDateTime = (d: string | Date | null | undefined) => {
  if (!d) return '—'
  const date = typeof d === 'string' ? new Date(d) : d
  return date.toLocaleString('zh-TW', { hour12: false })
}

export const fmtRelative = (d: string | Date | null | undefined) => {
  if (!d) return '—'
  const date = typeof d === 'string' ? new Date(d) : d
  const diff = Date.now() - date.getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${sec} 秒前`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} 分鐘前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小時前`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} 天前`
  return fmtDate(date)
}
