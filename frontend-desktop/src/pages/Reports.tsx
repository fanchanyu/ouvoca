/**
 * Reports — 報表頁（Sprint M v3.19）
 *
 * 4 個區塊：
 *  📊 KPI 儀表板（DSO / 庫存週轉 / 毛利率） — 即時計算
 *  💵 應收帳款 aging（Excel 下載）
 *  📦 月度庫存報表（Excel 下載）
 *  🧾 台灣 401 稅務報表（HTML / 列印 → PDF）
 *
 * 為什麼這頁重要：
 *  - 老闆王董要的「今天狀況」前端入口
 *  - 出貨後要看 AR 老闆才知道誰欠錢
 *  - 月底 / 季底要交 401 / 403 國稅局報表
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiAnalyticsDSO, apiAnalyticsInventoryTurn, apiAnalyticsGrossMargin,
  reportUrlAR, reportUrlInventoryMonthly, reportUrlTax401,
} from '../lib/api'

export default function Reports() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">📈 報表中心</h1>
        <p className="text-sm text-gray-500 mt-1">
          KPI 即時儀表板 + Excel 下載 + 台灣稅務報表
        </p>
      </div>

      <KPISection />
      <ARAgingSection />
      <InventoryMonthlySection />
      <Tax401Section />
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 1. KPI 即時儀表板
// ────────────────────────────────────────────────────────────
function KPISection() {
  const [dso, setDso] = useState<import('../lib/api').KpiResult | null>(null)
  const [turn, setTurn] = useState<import('../lib/api').KpiResult | null>(null)
  const [margin, setMargin] = useState<import('../lib/api').KpiResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      try {
        const [d, t, m] = await Promise.all([
          apiAnalyticsDSO().catch(() => null),
          apiAnalyticsInventoryTurn().catch(() => null),
          apiAnalyticsGrossMargin().catch(() => null),
        ])
        setDso(d); setTurn(t); setMargin(m)
      } catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
      finally { setLoading(false) }
    })()
  }, [])

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">📊 KPI 即時儀表板</h2>
      <p className="text-sm text-gray-500 mb-4">老闆問「今天狀況」的 3 個關鍵數字</p>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard
          icon="💵" title="DSO 應收帳款天數"
          value={dso ? `${dso.value.toFixed(0)} 天` : (loading ? '…' : 'N/A')}
          sub={dso?.interpretation || '—'}
          hint="客戶平均要多久才付錢；< 30 天健康"
          color="blue"
        />
        <KpiCard
          icon="📦" title="庫存週轉率"
          value={turn ? `${turn.value.toFixed(1)} 次/年` : (loading ? '…' : 'N/A')}
          sub={turn?.interpretation || '—'}
          hint="一年週轉幾次；> 6 健康"
          color="emerald"
        />
        <KpiCard
          icon="📈" title="毛利率"
          value={margin ? `${margin.value.toFixed(1)} %` : (loading ? '…' : 'N/A')}
          sub={margin?.interpretation || '—'}
          hint="製造業 > 25% 算健康"
          color="amber"
        />
      </div>

      <p className="text-xs text-gray-500 mt-4">
        💡 數字看不懂？問 <Link to="/chat" className="text-blue-600 underline">AI 助手</Link>：「我們的 DSO 為什麼這麼高？」
      </p>
    </section>
  )
}

function KpiCard({ icon, title, value, sub, hint, color }: {
  icon: string; title: string; value: string; sub: string; hint: string; color: string
}) {
  const borderColor: Record<string, string> = {
    blue: 'border-blue-500', emerald: 'border-emerald-500', amber: 'border-amber-500',
  }
  return (
    <div className={`bg-gray-50 rounded-lg p-4 border-l-4 ${borderColor[color]}`}>
      <div className="text-xs text-gray-500">{icon} {title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      <div className="text-xs text-gray-600 mt-1">{sub}</div>
      <div className="text-xs text-gray-400 mt-2 italic">{hint}</div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 2. AR Aging Excel
// ────────────────────────────────────────────────────────────
function ARAgingSection() {
  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">💵 應收帳款 aging 報表</h2>
      <p className="text-sm text-gray-500 mb-4">下載 Excel — 含未收清單、帳齡分組（0-30 / 31-60 / 61-90 / 90+ 天）</p>

      <div className="flex gap-2">
        <a href={reportUrlAR(false)} download
          className="px-4 py-2 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700">
          📥 下載全部 AR (.xlsx)
        </a>
        <a href={reportUrlAR(true)} download
          className="px-4 py-2 border border-red-500 text-red-600 rounded text-sm hover:bg-red-50">
          ⚠️ 只下載逾期 AR
        </a>
      </div>
    </section>
  )
}

// ────────────────────────────────────────────────────────────
// 3. Inventory Monthly
// ────────────────────────────────────────────────────────────
function InventoryMonthlySection() {
  const now = new Date()
  const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const [period, setPeriod] = useState(defaultMonth)

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">📦 月度庫存報表</h2>
      <p className="text-sm text-gray-500 mb-4">下載 Excel — 每個料件的月初 / 月底 / 進 / 出 / 結存</p>

      <div className="flex gap-2 items-center">
        <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)}
          className="border rounded px-3 py-2 text-sm" />
        <a href={reportUrlInventoryMonthly(period)} download
          className="px-4 py-2 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700">
          📥 下載 {period} 月報 (.xlsx)
        </a>
      </div>
    </section>
  )
}

// ────────────────────────────────────────────────────────────
// 4. Tax 401 報表 (台灣國稅局營業稅)
// ────────────────────────────────────────────────────────────
function Tax401Section() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [periodNo, setPeriodNo] = useState(Math.ceil((now.getMonth() + 1) / 2))  // 雙月制 1-6
  const [companyName, setCompanyName] = useState('')

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">🧾 台灣營業稅 401 報表</h2>
      <p className="text-sm text-gray-500 mb-4">
        雙月申報（1-6 期）。產 HTML → 用瀏覽器「列印 → 另存 PDF」交國稅局。
      </p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
        <div>
          <label className="block text-xs text-gray-600 mb-1">年度</label>
          <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))}
            min="2020" max="2099" className="w-full border rounded px-2 py-1.5 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">期別</label>
          <select value={periodNo} onChange={(e) => setPeriodNo(Number(e.target.value))}
            className="w-full border rounded px-2 py-1.5 text-sm">
            {[1, 2, 3, 4, 5, 6].map(n => (
              <option key={n} value={n}>第 {n} 期（{n * 2 - 1}-{n * 2} 月）</option>
            ))}
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="block text-xs text-gray-600 mb-1">公司名稱（選填）</label>
          <input type="text" value={companyName} onChange={(e) => setCompanyName(e.target.value)}
            placeholder="顯示在報表表頭" className="w-full border rounded px-2 py-1.5 text-sm" />
        </div>
      </div>

      <a href={reportUrlTax401(year, periodNo, companyName)} target="_blank" rel="noopener noreferrer"
        className="inline-block px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
        📄 開 {year} 年第 {periodNo} 期報表
      </a>
      <p className="text-xs text-gray-500 mt-3">
        💡 完成後按瀏覽器 <kbd className="bg-gray-100 px-1 rounded text-xs">Ctrl+P</kbd> 印出 → 選「另存為 PDF」即可交檔。
      </p>
    </section>
  )
}
