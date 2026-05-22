/**
 * Dashboard — 商業級老闆儀表板（i18n + 美術精緻化）
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  apiListParts, apiListWOs, apiListPOs, apiBelowSafety, apiListSOs, apiHealth,
  apiListPendingApprovals,
  apiOnboardingStatus, type OnboardingStatus,  // v3.37 D0-3：接 wizard
} from '../lib/api'
import {
  Card, CardHeader, Skeleton, SkeletonStatCard, EmptyState,
  ErrorState, Badge, StatusBadge, Button, useToast,
} from '../components/ui'
import { fmtNumber, fmtCurrency } from '../utils/format'
import { useTranslation } from '../i18n'
import OnboardingWizard from '../components/OnboardingWizard'  // v3.37 D0-3 死碼救活

interface DashboardData {
  partsCount: number
  woCount: number
  woInProgress: number
  poCount: number
  soCount: number
  soTotalRevenue: number
  lowStock: Array<{ part_no: string; name: string; qty_available: number; safety_stock: number; shortage: number }>
  recentWO: Array<{ id: string; wo_no: string; status: string; completed_qty: number; ordered_qty: number }>
}

interface HealthInfo { llmReady: boolean; llmProvider: string }

export default function Dashboard() {
  const navigate = useNavigate()
  const toast = useToast()
  const { t, lang } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<DashboardData | null>(null)
  const [health, setHealth] = useState<HealthInfo | null>(null)
  // v3.37 D0-3：第一次安裝（DB 空）自動跳出引導
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardDismissed, setWizardDismissed] = useState<boolean>(
    () => localStorage.getItem('ouvoca_wizard_dismissed') === '1'
  )

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [parts, wos, pos, sos, low, h] = await Promise.all([
        apiListParts(), apiListWOs(), apiListPOs(), apiListSOs(),
        apiBelowSafety(), apiHealth().catch(() => null),
      ])
      setData({
        partsCount: parts.length, woCount: wos.length,
        woInProgress: wos.filter(w => w.status === 'released' || w.status === 'in_progress').length,
        poCount: pos.length, soCount: sos.length,
        soTotalRevenue: sos.reduce((s, o) => s + (o.total_amount || 0), 0),
        lowStock: low.slice(0, 5),
        recentWO: wos.slice(0, 5).map(w => ({
          id: w.id, wo_no: w.wo_no, status: w.status,
          completed_qty: w.completed_qty, ordered_qty: w.ordered_qty,
        })),
      })
      setHealth(h ? { llmReady: !!h.llm_provider && h.status === 'ok', llmProvider: h.llm_provider } : null)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('login.backendOffline'))
    } finally { setLoading(false) }
  }, [t])

  useEffect(() => { load() }, [load])

  // v3.37 D0-3 / v3.43 P0-3：載入時檢查是否首次登入
  //
  // 修補：install.bat 會自動 seed → DB 不會空 → 舊條件「empty=true」永遠不成立 → wizard 死碼
  // 改用 localStorage `ouvoca_first_seen` 旗號：使用者每個瀏覽器只看一次
  // 若想再看，可手動清 localStorage 或開無痕模式
  useEffect(() => {
    if (wizardDismissed) return
    const firstSeen = localStorage.getItem('ouvoca_first_seen')
    apiOnboardingStatus().then(s => {
      setOnboardingStatus(s)
      // 首次（localStorage 沒紀錄）→ 跳；或 DB 完全空（極少情況）→ 也跳
      const dbEmpty = s.total_customers === 0 && s.total_suppliers === 0 && s.total_parts === 0
      if (!firstSeen || dbEmpty) {
        setWizardOpen(true)
        try { localStorage.setItem('ouvoca_first_seen', new Date().toISOString()) } catch { /* ignore */ }
      }
    }).catch(() => { /* 無權限就略過 */ })
  }, [wizardDismissed])

  const closeWizard = useCallback(() => {
    setWizardOpen(false)
    try { localStorage.setItem('ouvoca_wizard_dismissed', '1') } catch { /* ignore */ }
    setWizardDismissed(true)
  }, [])

  if (error) {
    return <Card><ErrorState message={error} onRetry={() => { toast.info(t('common.refresh')); load() }} /></Card>
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* v3.37 D0-3：第一次安裝的引導 wizard（DB 空時自動彈，user 可手動 dismiss） */}
      {wizardOpen && (
        <OnboardingWizard
          initialStatus={onboardingStatus}
          onClose={closeWizard}
          onCompleted={() => { load() }}
        />
      )}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <p className="text-body-sm text-ink-500">{getGreeting(t)} 👋</p>
          {/* v3.42 R8：手機上字小一級 */}
          <h1 className="text-2xl sm:text-h1 text-ink-900 mt-1 tracking-tight">{t('dashboard.title')}</h1>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <Badge tone={health?.llmReady ? 'success' : 'warning'} dot>
            {health?.llmReady ? `${t('dashboard.aiReady')} · ${health.llmProvider}` : t('dashboard.aiOffline')}
          </Badge>
          <Button variant="secondary" size="sm" onClick={load} icon={<span>↻</span>}>
            {t('common.refresh')}
          </Button>
        </div>
      </header>

      <AISummary loading={loading} data={data} t={t} />

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
        </div>
      ) : data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title={t('dashboard.totalRevenue')}
            value={fmtCurrency(data.soTotalRevenue)}
            sub={t('dashboard.soCount', { count: data.soCount })}
            tone="brand" icon="💰" onClick={() => navigate('/sales')}
          />
          <StatCard
            title={t('dashboard.inProgressWO')}
            value={fmtNumber(data.woInProgress)}
            sub={t('dashboard.woTotal', { count: data.woCount })}
            tone="success" icon="🏭" onClick={() => navigate('/production')}
          />
          <StatCard
            title={t('dashboard.purchaseOrders')}
            value={fmtNumber(data.poCount)}
            sub={t('dashboard.recent30Days')}
            tone="info" icon="🛒" onClick={() => navigate('/purchase')}
          />
          <StatCard
            title={t('dashboard.inventoryAlert')}
            value={fmtNumber(data.lowStock.length)}
            sub={data.lowStock.length > 0 ? t('dashboard.needAction') : t('dashboard.allNormal')}
            tone={data.lowStock.length > 0 ? 'danger' : 'neutral'}
            icon="⚠️" onClick={() => navigate('/inventory')}
          />
        </div>
      )}

      {/* v3.23 待辦中心 — 對標鼎新 / SAP Cockpit */}
      <TodoCenter data={data} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentWorkOrders loading={loading} data={data} navigate={navigate} t={t} />
        <LowStockAlert loading={loading} data={data} navigate={navigate} toast={toast} t={t} />
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// v3.23 TodoCenter — 個人化待辦中心（4 actionable widgets）
// ────────────────────────────────────────────────────────────
function TodoCenter({ data }: { data: DashboardData | null }) {
  const navigate = useNavigate()
  const [pendingApprovals, setPendingApprovals] = useState<number>(0)
  const [draftPOs, setDraftPOs] = useState<number>(0)
  const [draftWOs, setDraftWOs] = useState<number>(0)

  useEffect(() => {
    (async () => {
      try {
        const [approvals, pos, wos] = await Promise.all([
          apiListPendingApprovals().catch(() => []),
          apiListPOs().catch(() => []),
          apiListWOs().catch(() => []),
        ])
        setPendingApprovals(approvals.length)
        setDraftPOs(pos.filter(p => p.status === 'draft').length)
        setDraftWOs(wos.filter(w => w.status === 'draft').length)
      } catch { /* ignore */ }
    })()
  }, [])

  const lowStockCount = data?.lowStock.length || 0
  const total = pendingApprovals + lowStockCount + draftPOs + draftWOs

  return (
    <Card padding="lg" className="bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 text-white flex items-center justify-center text-xl">
          📋
        </div>
        <div className="flex-1">
          <p className="text-caption text-amber-700 font-semibold uppercase tracking-wide">📋 今日待辦中心</p>
          {total === 0 ? (
            <p className="text-body-lg text-ink-800 mt-1">✅ 沒有待處理事項，做得好！</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
              <TodoItem
                count={pendingApprovals} label="待我審"
                color="bg-red-100 text-red-800 border-red-200"
                onClick={() => navigate('/approvals')} hidden={pendingApprovals === 0}
              />
              <TodoItem
                count={lowStockCount} label="缺貨警示"
                color="bg-amber-100 text-amber-800 border-amber-200"
                onClick={() => navigate('/inventory')} hidden={lowStockCount === 0}
              />
              <TodoItem
                count={draftPOs} label="草稿 PO 待核准"
                color="bg-blue-100 text-blue-800 border-blue-200"
                onClick={() => navigate('/purchase')} hidden={draftPOs === 0}
              />
              <TodoItem
                count={draftWOs} label="草稿 WO 待釋放"
                color="bg-purple-100 text-purple-800 border-purple-200"
                onClick={() => navigate('/production')} hidden={draftWOs === 0}
              />
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

function TodoItem({ count, label, color, onClick, hidden }: {
  count: number; label: string; color: string; onClick: () => void; hidden: boolean
}) {
  if (hidden) return null
  return (
    <button onClick={onClick}
      className={`text-left px-3 py-2 border rounded-lg hover:shadow transition-all ${color}`}>
      <div className="text-2xl font-bold">{count}</div>
      <div className="text-xs">{label} →</div>
    </button>
  )
}

type TFn = (path: string, vars?: Record<string, string | number>) => string

function AISummary({ loading, data, t }: { loading: boolean; data: DashboardData | null; t: TFn }) {
  const summary = data ? buildSummary(data, t) : ''
  return (
    <Card padding="lg" className="bg-gradient-to-r from-brand-50 via-brand-50/60 to-transparent border-brand-100">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center text-xl shadow-lg shadow-brand-500/20">
          🤖
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-caption text-brand-700 font-semibold uppercase tracking-wide">
            {t('dashboard.aiSummary')}
          </p>
          {loading ? (
            <div className="mt-2 space-y-2">
              <Skeleton height="0.875rem" width="90%" />
              <Skeleton height="0.875rem" width="75%" />
            </div>
          ) : (
            <p className="text-body-lg text-ink-800 mt-1 leading-relaxed">{summary}</p>
          )}
        </div>
      </div>
    </Card>
  )
}

function buildSummary(d: DashboardData, t: TFn): string {
  const parts: string[] = []
  if (d.lowStock.length > 0) {
    parts.push(t('dashboard.summaryLowStock', { count: d.lowStock.length, name: d.lowStock[0].name }))
  } else {
    parts.push(t('dashboard.summaryStockOK'))
  }
  if (d.woInProgress > 0) parts.push(t('dashboard.summaryWOActive', { count: d.woInProgress }))
  if (d.soTotalRevenue > 0) parts.push(t('dashboard.summaryRevenue', { amount: fmtCurrency(d.soTotalRevenue) }))
  if (parts.length === 1 && d.partsCount === 0) {
    return t('dashboard.summaryNoData')
  }
  return parts.join(' ')
}

function StatCard({ title, value, sub, tone, icon, onClick }: {
  title: string; value: string; sub: string
  tone: 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  icon: string; onClick?: () => void
}) {
  const toneRing: Record<string, string> = {
    brand:   'border-l-brand-500 hover:border-brand-300',
    success: 'border-l-success-500 hover:border-success-300',
    warning: 'border-l-warning-500 hover:border-warning-300',
    danger:  'border-l-danger-500 hover:border-danger-300',
    info:    'border-l-brand-400 hover:border-brand-300',
    neutral: 'border-l-ink-400 hover:border-ink-300',
  }
  return (
    <Card interactive={!!onClick} padding="lg" onClick={onClick}
      className={`border-l-4 ${toneRing[tone]} group`}>
      <div className="flex items-start justify-between">
        <p className="text-body-sm text-ink-500 font-medium">{title}</p>
        <span className="text-2xl group-hover:scale-110 transition-transform" aria-hidden>{icon}</span>
      </div>
      <p className="text-display mt-2 text-ink-900 nowrap-cjk tabular-nums">{value}</p>
      <p className="text-caption text-ink-500 mt-1">{sub}</p>
    </Card>
  )
}

function RecentWorkOrders({ loading, data, navigate, t }: {
  loading: boolean; data: DashboardData | null
  navigate: ReturnType<typeof useNavigate>; t: TFn
}) {
  return (
    <Card>
      <CardHeader
        title={t('dashboard.recentWO')}
        action={<Button variant="ghost" size="sm" onClick={() => navigate('/production')}>{t('common.viewAll')} →</Button>}
      />
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 py-2">
              <Skeleton width="35%" height="1rem" />
              <Skeleton width="20%" height="1.5rem" />
              <div className="flex-1"><Skeleton width="100%" height="0.5rem" /></div>
              <Skeleton width="3rem" height="1rem" />
            </div>
          ))}
        </div>
      ) : !data || data.recentWO.length === 0 ? (
        <EmptyState
          icon="🏭" variant="compact"
          title={t('dashboard.emptyWO')}
          description={t('dashboard.emptyWOHint')}
          action={<Button onClick={() => navigate('/production')}>{t('dashboard.createWO')}</Button>}
        />
      ) : (
        <ul className="space-y-1 -mx-2">
          {data.recentWO.map(w => {
            const pct = w.ordered_qty > 0 ? Math.round((w.completed_qty / w.ordered_qty) * 100) : 0
            const barTone = pct >= 90 ? 'bg-gradient-to-r from-success-500 to-success-600'
              : pct >= 30 ? 'bg-gradient-to-r from-brand-500 to-brand-600' : 'bg-ink-300'
            return (
              <li key={w.id}
                className="flex items-center gap-4 px-2 py-2 rounded-lg hover:bg-ink-50 transition-colors cursor-pointer"
                onClick={() => navigate('/production')}>
                <span className="font-mono text-body-sm text-ink-600 min-w-[8.5rem] truncate">{w.wo_no}</span>
                <StatusBadge status={w.status} />
                <div className="flex-1 h-2 bg-ink-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${barTone}`} style={{ width: `${pct}%` }} />
                </div>
                <span className="text-body-sm font-medium text-ink-700 w-10 text-right tabular-nums">{pct}%</span>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

function LowStockAlert({ loading, data, navigate, toast, t }: {
  loading: boolean; data: DashboardData | null
  navigate: ReturnType<typeof useNavigate>
  toast: ReturnType<typeof useToast>; t: TFn
}) {
  return (
    <Card>
      <CardHeader
        title={t('dashboard.lowStockAlert')}
        subtitle={t('dashboard.lowStockSubtitle')}
        action={
          data && data.lowStock.length > 0
            ? <Badge tone="danger" dot>{data.lowStock.length}</Badge>
            : undefined
        }
      />
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 py-2">
              <Skeleton width="35%" /><Skeleton width="40%" />
              <div className="flex-1" /><Skeleton width="3rem" />
            </div>
          ))}
        </div>
      ) : !data || data.lowStock.length === 0 ? (
        <EmptyState icon="✅" variant="compact"
          title={t('dashboard.stockNormal')} description={t('dashboard.stockNormalHint')} />
      ) : (
        <ul className="-mx-2 space-y-1">
          {data.lowStock.map(l => (
            <li key={l.part_no}
              className="flex items-center justify-between px-2 py-2.5 rounded-lg hover:bg-danger-50 transition-colors cursor-pointer"
              onClick={() => {
                toast.warning(`${l.part_no}`, {
                  description: `${l.qty_available} / ${l.safety_stock}`,
                })
              }}>
              <div className="flex-1 min-w-0">
                <p className="font-mono text-body-sm font-semibold text-ink-800 truncate">{l.part_no}</p>
                <p className="text-caption text-ink-500 truncate">{l.name}</p>
              </div>
              <div className="text-right">
                <p className="text-body font-semibold text-danger-700 tabular-nums">{fmtNumber(l.qty_available)}</p>
                <p className="text-caption text-ink-500">/ {t('dashboard.safety')} {fmtNumber(l.safety_stock)}</p>
              </div>
            </li>
          ))}
          <li className="pt-3">
            <Button variant="secondary" size="sm" onClick={() => navigate('/inventory')} className="w-full">
              {t('dashboard.viewFullInventory')}
            </Button>
          </li>
        </ul>
      )}
    </Card>
  )
}

function getGreeting(t: TFn): string {
  const h = new Date().getHours()
  if (h < 11) return t('dashboard.greeting.morning')
  if (h < 14) return t('dashboard.greeting.noon')
  if (h < 18) return t('dashboard.greeting.afternoon')
  return t('dashboard.greeting.evening')
}
