/**
 * 我的權限頁 — 個人視角，自己看自己有什麼
 *
 * UX：
 * - 角色卡片（含到期日、是否代理）
 * - 個別授權清單（含原因、到期）
 * - 完整權限樹（依模組分組）
 */
import { useEffect, useState } from 'react'
import { apiMyEffective, type EffectivePermissions } from '../lib/api'
import { Card, CardHeader, Skeleton, EmptyState, ErrorState, Badge } from '../components/ui'
import { fmtDateTime } from '../utils/format'

const MODULE_LABELS: Record<string, string> = {
  inventory: '📦 庫存', purchase: '🛒 採購', production: '🏭 生產', sales: '💰 銷售',
  quality: '🔬 品質', accounting: '💳 會計', warehouse: '📍 倉儲', crm: '👥 CRM',
  mps_mrp: '📊 MPS/MRP', outsource: '🔗 外協', organization: '🏛️ 組織',
  system: '⚙️ 系統', ai: '🤖 AI', mesh: '🌐 多廠',
}

const SCOPE_LABELS: Record<string, string> = {
  all: '全域', tenant: '本廠', department: '本部門', team: '本團隊',
  own: '只看自己', assigned: '指派的',
}

export default function MyPermissions() {
  const [data, setData] = useState<EffectivePermissions | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true); setError(null)
    try { setData(await apiMyEffective()) }
    catch (e) { setError(e instanceof Error ? e.message : '載入失敗') }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  if (error) return <Card><ErrorState message={error} onRetry={load} /></Card>

  // 分組權限
  const grouped: Record<string, Array<{ code: string; scope: string }>> = {}
  data?.permissions.forEach(p => {
    const module = p.code === '*' ? 'all' : p.code.split('.')[0]
    if (!grouped[module]) grouped[module] = []
    grouped[module].push(p)
  })

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <header>
        <h1 className="text-h1 text-ink-900">我的權限</h1>
        <p className="text-body-sm text-ink-500 mt-1">查看當前帳號擁有的角色與權限</p>
      </header>

      {/* 角色清單 */}
      <Card>
        <CardHeader title="擁有角色" subtitle="決定可以做什麼的主要規則" />
        {loading ? (
          <div className="space-y-3">{[1, 2].map(i => <Skeleton key={i} height="3rem" />)}</div>
        ) : !data || data.roles.length === 0 ? (
          <EmptyState icon="🛡️" variant="compact" title="尚未指派角色" />
        ) : (
          <div className="space-y-3">
            {data.roles.map((r, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-3 bg-ink-50 rounded-lg">
                <div>
                  <p className="text-body font-medium text-ink-900">
                    {r.role_name || r.role_code || '系統角色'}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-1.5">
                    <Badge tone="info" size="sm">廠別 {r.tenant_id}</Badge>
                    {r.is_delegation && <Badge tone="warning" size="sm" dot>代理</Badge>}
                    {r.expires_at && (
                      <Badge tone="warning" size="sm">到期 {fmtDateTime(r.expires_at)}</Badge>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 個別授權 */}
      {data && data.overrides.length > 0 && (
        <Card>
          <CardHeader title="個別授權" subtitle="角色之外的特殊權限" />
          <div className="space-y-2">
            {data.overrides.map((o, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2.5 bg-warning-50 rounded-lg">
                <div>
                  <p className="font-mono text-body-sm text-ink-800">{o.code}</p>
                  <p className="text-caption text-ink-600 mt-0.5">{o.reason}</p>
                </div>
                <div className="text-right">
                  <Badge tone={o.type === 'grant' ? 'success' : 'danger'} size="sm">
                    {o.type === 'grant' ? '+授予' : '-撤銷'}
                  </Badge>
                  {o.expires_at && (
                    <p className="text-caption text-ink-500 mt-1">{fmtDateTime(o.expires_at)} 到期</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 完整權限樹 */}
      <Card>
        <CardHeader
          title="實際生效權限"
          subtitle={data ? `共 ${data.permissions.length} 條` : ''}
        />
        {loading ? (
          <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} height="2rem" />)}</div>
        ) : !data || data.permissions.length === 0 ? (
          <EmptyState icon="🔒" variant="compact" title="無權限" />
        ) : data.permissions[0]?.code === '*' ? (
          <div className="bg-brand-50 border border-brand-200 rounded-input p-4">
            <p className="text-h3 text-brand-800">⭐ 超級管理員（全部權限）</p>
            <p className="text-body-sm text-brand-700 mt-1">
              您是系統最高權限使用者，可執行任何操作。
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {Object.entries(grouped).map(([module, perms]) => (
              <details key={module} className="bg-ink-50 rounded-input border border-ink-100" open>
                <summary className="cursor-pointer px-4 py-3 flex items-center justify-between font-medium text-ink-800 hover:bg-ink-100 rounded-input">
                  <span>{MODULE_LABELS[module] || module}</span>
                  <Badge tone="brand" size="sm">{perms.length}</Badge>
                </summary>
                <div className="px-4 pb-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {perms.map(p => (
                    <div key={p.code} className="flex items-center justify-between bg-white rounded px-2 py-1.5">
                      <span className="font-mono text-caption text-ink-700 truncate">{p.code}</span>
                      <Badge tone="neutral" size="sm">{SCOPE_LABELS[p.scope] || p.scope}</Badge>
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
