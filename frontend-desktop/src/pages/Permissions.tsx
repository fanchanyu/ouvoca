/**
 * 權限管理頁 — 角色清單 + 權限勾選編輯
 *
 * UX 重點：
 * - 角色卡片網格（icon + 中文名 + 權限數）
 * - 點擊 → 抽屜（drawer）展開權限勾選介面
 * - 權限依模組分組（折疊）
 * - 系統角色（is_system）只能「複製」、不能直接改
 */
import { useEffect, useState } from 'react'
import {
  apiListRoles, apiListPermissions, apiGetRole, apiCloneRole, apiUpdateRolePermissions,
  type RoleV2, type PermissionDef,
} from '../lib/api'
import {
  Card, CardHeader, Skeleton, EmptyState, ErrorState, Badge, Button, useToast,
} from '../components/ui'

const SCOPE_LABELS: Record<string, string> = {
  all: '全域', tenant: '本廠', department: '本部門', team: '本團隊',
  own: '只看自己', assigned: '指派的',
}
const SCOPE_OPTIONS = ['all', 'tenant', 'department', 'team', 'own', 'assigned']

const MODULE_LABELS: Record<string, string> = {
  inventory: '📦 庫存', purchase: '🛒 採購', production: '🏭 生產', sales: '💰 銷售',
  quality: '🔬 品質', accounting: '💳 會計', warehouse: '📍 倉儲', crm: '👥 CRM',
  mps_mrp: '📊 MPS/MRP', organization: '🏛️ 組織',
  system: '⚙️ 系統', ai: '🤖 AI', mesh: '🌐 多廠',
}

export default function Permissions() {
  const toast = useToast()
  const [roles, setRoles] = useState<RoleV2[]>([])
  const [permissions, setPermissions] = useState<PermissionDef[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedRole, setSelectedRole] = useState<RoleV2 | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [draftPerms, setDraftPerms] = useState<Record<string, string>>({})

  async function load() {
    setLoading(true); setError(null)
    try {
      const [r, p] = await Promise.all([apiListRoles(), apiListPermissions()])
      setRoles(r); setPermissions(p)
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function openRole(role: RoleV2) {
    try {
      const full = await apiGetRole(role.id)
      setSelectedRole(full)
      setEditMode(false)
      setDraftPerms(Object.fromEntries(full.permissions.map(p => [p.code, p.scope])))
    } catch (e) {
      toast.error('載入角色失敗', { description: e instanceof Error ? e.message : '' })
    }
  }

  async function handleClone() {
    if (!selectedRole) return
    const newCode = prompt('新角色代碼（英文，如 my_sales_rep）', selectedRole.code + '_copy')
    if (!newCode) return
    const newName = prompt('新角色中文名稱', selectedRole.name_zh + ' (複製)')
    if (!newName) return
    try {
      const cloned = await apiCloneRole(selectedRole.id, {
        new_code: newCode, new_name_zh: newName,
      })
      toast.success('已複製', { description: `${cloned.code}：${cloned.name_zh}` })
      await load()
      const full = await apiGetRole(cloned.id)
      setSelectedRole(full)
      setDraftPerms(Object.fromEntries(full.permissions.map(p => [p.code, p.scope])))
      setEditMode(true)
    } catch (e) {
      toast.error('複製失敗', { description: e instanceof Error ? e.message : '' })
    }
  }

  async function handleSave() {
    if (!selectedRole) return
    try {
      const perms = Object.entries(draftPerms).map(([code, scope]) => ({ code, scope }))
      await apiUpdateRolePermissions(selectedRole.id, perms)
      toast.success('已儲存', { description: `${selectedRole.name_zh} 權限已更新` })
      const updated = await apiGetRole(selectedRole.id)
      setSelectedRole(updated)
      setDraftPerms(Object.fromEntries(updated.permissions.map(p => [p.code, p.scope])))
      setEditMode(false)
      await load()
    } catch (e) {
      toast.error('儲存失敗', { description: e instanceof Error ? e.message : '' })
    }
  }

  function togglePerm(code: string) {
    setDraftPerms(prev => {
      const next = { ...prev }
      if (code in next) delete next[code]
      else next[code] = 'tenant'
      return next
    })
  }

  function setScope(code: string, scope: string) {
    setDraftPerms(prev => ({ ...prev, [code]: scope }))
  }

  if (error) return <Card><ErrorState message={error} onRetry={load} /></Card>

  // 將權限分組
  const groupedPerms: Record<string, PermissionDef[]> = {}
  permissions.forEach(p => {
    if (!groupedPerms[p.module]) groupedPerms[p.module] = []
    groupedPerms[p.module].push(p)
  })

  return (
    <div className="space-y-6 animate-fade-in">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-h1 text-ink-900">權限管理</h1>
          <p className="text-body-sm text-ink-500 mt-1">
            {roles.length} 個角色 · {permissions.length} 個權限定義
          </p>
        </div>
      </header>

      {/* 角色卡片網格 */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} padding="md">
              <Skeleton width="40%" height="1.5rem" />
              <Skeleton width="80%" height="1rem" className="mt-3" />
              <Skeleton width="30%" height="0.875rem" className="mt-2" />
            </Card>
          ))}
        </div>
      ) : roles.length === 0 ? (
        <EmptyState icon="🛡️" title="尚無角色" description="系統將自動建立 11 個預設角色。" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {roles.map(r => (
            <Card key={r.id} interactive padding="md" onClick={() => openRole(r)}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{r.icon || '🔑'}</span>
                  <div>
                    <p className="text-h3 text-ink-900 nowrap-cjk">{r.name_zh}</p>
                    <p className="font-mono text-caption text-ink-500">{r.code}</p>
                  </div>
                </div>
                {r.is_system && <Badge tone="info" size="sm">系統</Badge>}
              </div>
              <p className="text-body-sm text-ink-600 mt-3 line-clamp-2">
                {r.description || '無描述'}
              </p>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-ink-100">
                <Badge tone="neutral" dot>{r.permissions.length} 個權限</Badge>
                <span className="text-caption text-ink-400">優先級 {r.priority}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 抽屜 — 角色詳情 / 編輯 */}
      {selectedRole && (
        <>
          <div
            className="fixed inset-0 bg-ink-900/50 z-40 animate-fade-in"
            onClick={() => setSelectedRole(null)}
          />
          <aside className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-2xl bg-white shadow-pop overflow-y-auto animate-slide-up">
            {/* 抽屜頁首 */}
            <header className="sticky top-0 bg-white border-b border-ink-100 p-5 flex items-center justify-between gap-3 z-10">
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-3xl">{selectedRole.icon || '🔑'}</span>
                <div className="min-w-0">
                  <h2 className="text-h2 text-ink-900 truncate">{selectedRole.name_zh}</h2>
                  <p className="font-mono text-caption text-ink-500 truncate">{selectedRole.code}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {selectedRole.is_system && !editMode && (
                  <Button variant="secondary" size="sm" onClick={handleClone}>📋 複製</Button>
                )}
                {!selectedRole.is_system && !editMode && (
                  <Button variant="primary" size="sm" onClick={() => setEditMode(true)}>✏️ 編輯</Button>
                )}
                {editMode && (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => {
                      setEditMode(false)
                      setDraftPerms(Object.fromEntries(selectedRole.permissions.map(p => [p.code, p.scope])))
                    }}>取消</Button>
                    <Button variant="primary" size="sm" onClick={handleSave}>💾 儲存</Button>
                  </>
                )}
                <button
                  onClick={() => setSelectedRole(null)}
                  className="text-ink-400 hover:text-ink-700 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded focus-ring"
                  aria-label="關閉"
                >✕</button>
              </div>
            </header>

            <div className="p-5 space-y-5">
              {selectedRole.is_system && (
                <div className="bg-brand-50 border border-brand-200 rounded-input p-3 text-body-sm text-brand-800">
                  💡 這是系統內建角色，不能直接修改。請按「複製」建立客製版本後再編輯。
                </div>
              )}

              <p className="text-body text-ink-700">{selectedRole.description || '無描述'}</p>

              {/* 權限分組勾選 */}
              <div className="space-y-4">
                {Object.entries(groupedPerms).map(([module, perms]) => {
                  const selectedInModule = perms.filter(p => p.code in draftPerms).length
                  return (
                    <details key={module} className="bg-ink-50 rounded-input border border-ink-100" open={selectedInModule > 0}>
                      <summary className="cursor-pointer px-4 py-3 flex items-center justify-between font-medium text-ink-800 hover:bg-ink-100 rounded-input">
                        <span>{MODULE_LABELS[module] || module}</span>
                        <Badge tone={selectedInModule > 0 ? 'brand' : 'neutral'} size="sm">
                          {selectedInModule}/{perms.length}
                        </Badge>
                      </summary>
                      <div className="px-4 pb-3 space-y-2">
                        {perms.map(p => {
                          const checked = p.code in draftPerms
                          return (
                            <div key={p.code} className={[
                              'flex items-center gap-3 px-2 py-2 rounded transition-colors',
                              checked ? 'bg-brand-50' : 'hover:bg-white',
                            ].join(' ')}>
                              <input
                                type="checkbox" id={p.code}
                                checked={checked}
                                disabled={!editMode}
                                onChange={() => togglePerm(p.code)}
                                className="w-4 h-4 accent-brand-600"
                              />
                              <label htmlFor={p.code} className="flex-1 cursor-pointer min-w-0">
                                <p className="text-body-sm text-ink-800 truncate">{p.name_zh || p.code}</p>
                                <p className="font-mono text-caption text-ink-500 truncate">{p.code}</p>
                              </label>
                              {p.is_sensitive && <Badge tone="warning" size="sm">敏感</Badge>}
                              {checked && (
                                <select
                                  value={draftPerms[p.code]}
                                  disabled={!editMode}
                                  onChange={(e) => setScope(p.code, e.target.value)}
                                  className="text-caption border border-ink-200 rounded px-2 py-1 bg-white disabled:opacity-60"
                                >
                                  {SCOPE_OPTIONS.map(s => (
                                    <option key={s} value={s}>{SCOPE_LABELS[s]}</option>
                                  ))}
                                </select>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </details>
                  )
                })}
              </div>
            </div>
          </aside>
        </>
      )}
    </div>
  )
}
