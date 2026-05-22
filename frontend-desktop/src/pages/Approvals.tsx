/**
 * 審批工作流（v3.22 — 對標鼎新 / SAP B1）
 *
 * 3 個 tab：
 *  1. ✅ 待我審 — pending 列表 + [批准] [拒絕]
 *  2. 🗂 歷史 — status filter 後檢視 approved/rejected
 *  3. ⚙️ 規則設定 — 列出規則 + 新增規則 form
 *
 * 設計重點：
 *  - 規則命中後 backend 自動建單，這頁只負責「決策」與「設規則」
 *  - 拒絕強制 prompt 原因（後端也擋 — 雙重保險）
 *  - 多階審：第一階 approve 後仍 pending，UI 直接顯示 current_stage/total_stages
 */
import { useEffect, useMemo, useState } from 'react'
import {
  apiListPendingApprovals, apiListApprovalHistory,
  apiApprove, apiReject,
  apiListRules, apiCreateRule, apiDeleteRule,
  type ApprovalRequest, type ApprovalRule,
  ApiError,
} from '../lib/api'

type Tab = 'pending' | 'history' | 'rules'

const TRIGGER_LABEL: Record<string, string> = {
  po: '🛒 採購單',
  so: '💰 銷售單',
  payment: '💳 付款',
}

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-700 border-amber-200',
  approved: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-100 text-red-700 border-red-200',
  cancelled: 'bg-gray-100 text-gray-600 border-gray-200',
}

const STATUS_LABEL: Record<string, string> = {
  pending: '待審',
  approved: '已批准',
  rejected: '已拒絕',
  cancelled: '已取消',
}

export default function Approvals() {
  const [tab, setTab] = useState<Tab>('pending')

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">✅ 審批工作流</h1>
          <p className="text-sm text-gray-500 mt-1">
            條件式自動觸發 — PO &gt; 10 萬要老闆審、SO 折扣 &gt; 5% 主管審、付款 &gt; 5 萬雙簽
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {[
          { key: 'pending' as Tab, label: '✅ 待我審' },
          { key: 'history' as Tab, label: '🗂 歷史' },
          { key: 'rules' as Tab,   label: '⚙️ 規則設定' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={[
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'pending' && <PendingList />}
      {tab === 'history' && <HistoryList />}
      {tab === 'rules' && <RulesPanel />}
    </div>
  )
}


// ──────────────────────────────────────────────────────────
// Tab 1：待我審
// ──────────────────────────────────────────────────────────
function PendingList() {
  const [reqs, setReqs] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [roleFilter, setRoleFilter] = useState<string>('')

  async function load() {
    setLoading(true)
    try {
      const data = await apiListPendingApprovals(roleFilter || undefined).catch(() => [])
      setReqs(data)
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [roleFilter])

  const approve = async (req: ApprovalRequest) => {
    const comment = window.prompt(`批准 ${req.trigger_summary}\n\n備註（可不填）：`, '')
    if (comment === null) return // user cancelled
    try {
      await apiApprove(req.id, comment)
      await load()
    } catch (e) {
      alert(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '批准失敗')
    }
  }

  const reject = async (req: ApprovalRequest) => {
    const comment = window.prompt(`拒絕 ${req.trigger_summary}\n\n請輸入拒絕原因（必填）：`, '')
    if (comment === null) return
    if (!comment.trim()) {
      alert('拒絕原因不可空白')
      return
    }
    try {
      await apiReject(req.id, comment)
      await load()
    } catch (e) {
      alert(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '拒絕失敗')
    }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-600">審核角色：</label>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="border border-gray-200 rounded px-2 py-1 text-sm"
        >
          <option value="">全部</option>
          <option value="boss">老闆 (boss)</option>
          <option value="manager">主管 (manager)</option>
          <option value="finance">會計 (finance)</option>
        </select>
        <button
          onClick={() => void load()}
          className="ml-auto px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-50"
        >
          🔄 重新整理
        </button>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm">載入中…</div>
      ) : reqs.length === 0 ? (
        <div className="border border-dashed border-gray-200 rounded p-12 text-center text-gray-400">
          ✨ 沒有待審項目
        </div>
      ) : (
        <div className="space-y-2">
          {reqs.map(req => (
            <div
              key={req.id}
              className="border border-gray-200 rounded p-4 bg-white hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                    <span>{TRIGGER_LABEL[req.trigger_type] ?? req.trigger_type}</span>
                    <span>·</span>
                    <span>審核角色 {req.approver_role}</span>
                    <span>·</span>
                    <span>{new Date(req.created_at).toLocaleString('zh-TW')}</span>
                    {req.total_stages > 1 && (
                      <>
                        <span>·</span>
                        <span className="text-blue-600 font-medium">
                          {req.current_stage}/{req.total_stages} 階
                        </span>
                      </>
                    )}
                  </div>
                  <div className="font-medium text-gray-900">{req.trigger_summary}</div>
                  {req.steps.length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      已通過 {req.steps.length} 階 · 最後一筆：
                      <span className="text-gray-700">
                        {req.steps[req.steps.length - 1].approver_username || '系統'}
                      </span>
                      {req.steps[req.steps.length - 1].comment ? `「${req.steps[req.steps.length - 1].comment}」` : ''}
                    </div>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => void approve(req)}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded"
                  >
                    ✓ 批准
                  </button>
                  <button
                    onClick={() => void reject(req)}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded"
                  >
                    ✗ 拒絕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


// ──────────────────────────────────────────────────────────
// Tab 2：歷史
// ──────────────────────────────────────────────────────────
function HistoryList() {
  const [reqs, setReqs] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [triggerFilter, setTriggerFilter] = useState<string>('')

  async function load() {
    setLoading(true)
    try {
      const data = await apiListApprovalHistory({
        status: statusFilter || undefined,
        trigger_type: triggerFilter || undefined,
        limit: 200,
      }).catch(() => [])
      setReqs(data)
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [statusFilter, triggerFilter])

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <label className="text-sm text-gray-600">狀態：</label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-200 rounded px-2 py-1 text-sm"
        >
          <option value="">全部</option>
          <option value="pending">待審</option>
          <option value="approved">已批准</option>
          <option value="rejected">已拒絕</option>
          <option value="cancelled">已取消</option>
        </select>

        <label className="text-sm text-gray-600 ml-2">類型：</label>
        <select
          value={triggerFilter}
          onChange={(e) => setTriggerFilter(e.target.value)}
          className="border border-gray-200 rounded px-2 py-1 text-sm"
        >
          <option value="">全部</option>
          <option value="po">採購單</option>
          <option value="so">銷售單</option>
          <option value="payment">付款</option>
        </select>

        <button
          onClick={() => void load()}
          className="ml-auto px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-50"
        >
          🔄 重新整理
        </button>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm">載入中…</div>
      ) : reqs.length === 0 ? (
        <div className="border border-dashed border-gray-200 rounded p-12 text-center text-gray-400">
          尚無紀錄
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left text-gray-600">
                <th className="px-3 py-2 font-medium">類型</th>
                <th className="px-3 py-2 font-medium">摘要</th>
                <th className="px-3 py-2 font-medium">階段</th>
                <th className="px-3 py-2 font-medium">狀態</th>
                <th className="px-3 py-2 font-medium">建立時間</th>
                <th className="px-3 py-2 font-medium">最後決議</th>
              </tr>
            </thead>
            <tbody>
              {reqs.map(req => {
                const last = req.steps[req.steps.length - 1]
                return (
                  <tr key={req.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-3 py-2">{TRIGGER_LABEL[req.trigger_type] ?? req.trigger_type}</td>
                    <td className="px-3 py-2 font-medium">{req.trigger_summary}</td>
                    <td className="px-3 py-2">{req.current_stage}/{req.total_stages}</td>
                    <td className="px-3 py-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs border ${STATUS_BADGE[req.status] ?? ''}`}>
                        {STATUS_LABEL[req.status] ?? req.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500 text-xs">
                      {new Date(req.created_at).toLocaleString('zh-TW')}
                    </td>
                    <td className="px-3 py-2 text-gray-600 text-xs">
                      {last
                        ? `${last.approver_username || '系統'}：${last.comment || '(無備註)'}`
                        : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}


// ──────────────────────────────────────────────────────────
// Tab 3：規則設定
// ──────────────────────────────────────────────────────────
function RulesPanel() {
  const [rules, setRules] = useState<ApprovalRule[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await apiListRules().catch(() => [])
      setRules(data)
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [])

  const removeRule = async (rule: ApprovalRule) => {
    if (!confirm(`刪除規則「${rule.name}」？`)) return
    try {
      await apiDeleteRule(rule.id)
      await load()
    } catch (e) {
      alert(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '刪除失敗')
    }
  }

  return (
    <div>
      <div className="flex items-center mb-4">
        <button
          onClick={() => setShowForm(true)}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
        >
          ➕ 新增規則
        </button>
        <button
          onClick={() => void load()}
          className="ml-auto px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-50"
        >
          🔄 重新整理
        </button>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm">載入中…</div>
      ) : rules.length === 0 ? (
        <div className="border border-dashed border-gray-200 rounded p-12 text-center text-gray-400">
          尚未設定規則 — 點「新增規則」開始設定
        </div>
      ) : (
        <div className="space-y-2">
          {rules.map(rule => (
            <div
              key={rule.id}
              className="border border-gray-200 rounded p-3 bg-white flex items-center gap-3"
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium">{rule.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  當 <span className="font-medium text-gray-700">{TRIGGER_LABEL[rule.trigger_type] ?? rule.trigger_type}</span>
                  {' '}的 <code className="text-gray-700">{rule.condition_field}</code>
                  {' '}<code className="text-gray-700">{rule.condition_op}</code>
                  {' '}<code className="text-gray-700">{rule.condition_value.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</code>
                  {' '}→ 通知 <span className="font-medium text-gray-700">{rule.approver_role}</span> 審
                  {' '}({rule.stages} 階)
                </div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded border ${rule.is_active ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-gray-50 text-gray-500 border-gray-200'}`}>
                {rule.is_active ? '啟用' : '停用'}
              </span>
              <button
                onClick={() => void removeRule(rule)}
                className="text-red-600 hover:bg-red-50 text-sm px-2 py-1 rounded"
              >
                刪除
              </button>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <NewRuleModal
          onClose={() => setShowForm(false)}
          onCreated={async () => { setShowForm(false); await load() }}
        />
      )}
    </div>
  )
}


function NewRuleModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => Promise<void> | void }) {
  const [name, setName] = useState('')
  const [triggerType, setTriggerType] = useState<'po' | 'so' | 'payment'>('po')
  const [conditionField, setConditionField] = useState<'amount' | 'discount_pct'>('amount')
  const [conditionOp, setConditionOp] = useState<'gt' | 'gte' | 'lt' | 'lte' | 'eq'>('gt')
  const [conditionValue, setConditionValue] = useState<number>(100000)
  const [approverRole, setApproverRole] = useState<string>('boss')
  const [stages, setStages] = useState<number>(1)
  const [busy, setBusy] = useState(false)

  // SO 通常用 discount_pct，PO/payment 通常用 amount — 提供合理預設
  const fieldOptions = useMemo(() => {
    if (triggerType === 'so') return [
      { value: 'amount', label: '訂單金額' },
      { value: 'discount_pct', label: '折扣 %' },
    ]
    return [{ value: 'amount', label: '金額' }]
  }, [triggerType])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { alert('規則名稱不可空'); return }
    setBusy(true)
    try {
      await apiCreateRule({
        name: name.trim(),
        trigger_type: triggerType,
        condition_field: conditionField,
        condition_op: conditionOp,
        condition_value: Number(conditionValue),
        approver_role: approverRole.trim(),
        stages,
        is_active: true,
      })
      await onCreated()
    } catch (err) {
      alert(err instanceof ApiError ? err.friendly() : err instanceof Error ? err.message : '新增失敗')
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-4">➕ 新增審批規則</h3>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">規則名稱</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
              placeholder="例：高額採購單"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">觸發類型</label>
              <select
                value={triggerType}
                onChange={(e) => {
                  const v = e.target.value as 'po' | 'so' | 'payment'
                  setTriggerType(v)
                  // 自動把 condition_field 對到合適預設
                  setConditionField(v === 'so' ? 'discount_pct' : 'amount')
                }}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
              >
                <option value="po">採購單 (po)</option>
                <option value="so">銷售單 (so)</option>
                <option value="payment">付款 (payment)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">條件欄位</label>
              <select
                value={conditionField}
                onChange={(e) => setConditionField(e.target.value as 'amount' | 'discount_pct')}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
              >
                {fieldOptions.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">比較</label>
              <select
                value={conditionOp}
                onChange={(e) => setConditionOp(e.target.value as 'gt' | 'gte' | 'lt' | 'lte' | 'eq')}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
              >
                <option value="gt">大於 (&gt;)</option>
                <option value="gte">大於等於 (&gt;=)</option>
                <option value="lt">小於 (&lt;)</option>
                <option value="lte">小於等於 (&lt;=)</option>
                <option value="eq">等於 (=)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">門檻值</label>
              <input
                type="number"
                value={conditionValue}
                onChange={(e) => setConditionValue(Number(e.target.value))}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">審核角色</label>
              <input
                value={approverRole}
                onChange={(e) => setApproverRole(e.target.value)}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
                placeholder="boss / manager / finance"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">階數</label>
              <input
                type="number"
                min={1}
                max={5}
                value={stages}
                onChange={(e) => setStages(Math.max(1, Math.min(5, Number(e.target.value) || 1)))}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              disabled={busy}
              className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded disabled:opacity-50"
            >
              {busy ? '送出中…' : '建立'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="px-3 py-2 border border-gray-200 text-sm rounded hover:bg-gray-50"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
