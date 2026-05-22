/**
 * Accounting — 會計頁（Sprint L v3.18）
 *
 * 3 個 tab：
 *  📊 傳票 (Journal Entries) — 列表 / 建立簡單借貸傳票 / post 過帳
 *  💵 應收帳款 (AR) — 列表 + status 篩選 + aging 顯示
 *  📚 科目表 (Chart of Accounts) — 列表 / 簡單新增（admin）
 *
 * 為什麼這頁重要：
 *  - 沒這頁，「符合 ERP 完整需求」就站不住
 *  - 台灣 SMB 製造業最痛點是「帳沒對」「應收沒追」
 *  - 配合 v3.16 Auto CrmEvent 自動 log 業務動作，未來可自動帶生傳票
 */
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiListJournals, apiCreateJournal, apiPostJournal,
  apiListAccounts, apiCreateAccount,
  apiListAR, apiListCustomers,
  type JournalEntry, type Account, type AccountsReceivable,
  type Customer, type JournalLineInput,
  ApiError,
} from '../lib/api'
import EmptyState from '../components/EmptyState'

type Tab = 'journals' | 'ar' | 'accounts'

export default function Accounting() {
  const [tab, setTab] = useState<Tab>('journals')

  return (
    <div>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold">📒 會計管理</h1>
          <p className="text-sm text-gray-500 mt-1">
            傳票記錄、應收帳款追蹤、科目表管理
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {[
          { key: 'journals' as Tab, label: '📊 傳票' },
          { key: 'ar' as Tab,       label: '💵 應收帳款' },
          { key: 'accounts' as Tab, label: '📚 科目表' },
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

      {tab === 'journals' && <JournalsTab />}
      {tab === 'ar' && <ARTab />}
      {tab === 'accounts' && <AccountsTab />}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 1. 傳票 Tab
// ────────────────────────────────────────────────────────────
function JournalsTab() {
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  // 新傳票表單（簡化版：1 借 1 貸）
  const [draft, setDraft] = useState({
    description: '',
    debit_account_id: '',
    credit_account_id: '',
    amount: 0,
  })

  async function load() {
    setLoading(true); setErr(null)
    try {
      const [j, a] = await Promise.all([
        apiListJournals().catch(() => []),
        apiListAccounts().catch(() => []),
      ])
      setEntries(j); setAccounts(a)
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [])

  async function createEntry() {
    if (!draft.description.trim() || !draft.debit_account_id || !draft.credit_account_id || draft.amount <= 0) {
      setErr('摘要 + 借方科目 + 貸方科目 + 金額 都必填')
      return
    }
    if (draft.debit_account_id === draft.credit_account_id) {
      setErr('借方和貸方不能是同一個科目')
      return
    }
    setErr(null); setMsg(null)
    setSubmitting(true)
    try {
      const lines: JournalLineInput[] = [
        { account_id: draft.debit_account_id, debit: draft.amount, credit: 0 },
        { account_id: draft.credit_account_id, debit: 0, credit: draft.amount },
      ]
      const e = await apiCreateJournal({
        description: draft.description, lines,
        entry_date: new Date().toISOString(),  // backend NOT NULL
      })
      setMsg(`✅ 傳票 ${e.entry_no} 已建立（草稿狀態）`)
      setDraft({ description: '', debit_account_id: '', credit_account_id: '', amount: 0 })
      setCreating(false)
      await load()
    } catch (e: unknown) { setErr(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '建立失敗') }
    finally { setSubmitting(false) }
  }

  async function postEntry(entry: JournalEntry) {
    if (!confirm(`過帳傳票 ${entry.entry_no}？\n\n過帳後不可修改。`)) return
    setErr(null)
    try {
      await apiPostJournal(entry.id)
      setMsg(`✅ ${entry.entry_no} 已過帳`)
      await load()
    } catch (e: unknown) { setErr(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '過帳失敗') }
  }

  // (accountLabel helper removed — not yet used in render; JournalLine UI to be added next sprint)

  return (
    <div>
      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
      {msg && <div className="bg-green-50 text-green-700 px-3 py-2 rounded mb-3 text-sm">{msg}</div>}

      <div className="flex justify-between items-center mb-4">
        <div className="text-sm text-gray-600">
          📊 共 {entries.length} 筆傳票
        </div>
        <button onClick={() => setCreating(c => !c)} disabled={accounts.length < 2}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
          {creating ? '取消' : '➕ 新增傳票'}
        </button>
      </div>

      {accounts.length < 2 && (
        <div className="bg-amber-50 text-amber-800 px-3 py-2 rounded mb-3 text-sm">
          ⚠️ 至少需要 2 個會計科目才能建傳票。先到「📚 科目表」tab 建科目。
        </div>
      )}

      {creating && (
        <form onSubmit={(e) => { e.preventDefault(); createEntry() }} className="bg-white rounded-xl shadow p-4 mb-4">
          <h3 className="font-semibold text-sm mb-3">新增傳票（簡化版：1 借 1 貸）</h3>
          <div className="grid md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs text-gray-600 mb-1">摘要*</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="例：5/15 收到客戶 A 貨款"
                value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">借方科目*</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm" value={draft.debit_account_id}
                onChange={(e) => setDraft({ ...draft, debit_account_id: e.target.value })}>
                <option value="">選借方</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.code} {a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">貸方科目*</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm" value={draft.credit_account_id}
                onChange={(e) => setDraft({ ...draft, credit_account_id: e.target.value })}>
                <option value="">選貸方</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.code} {a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">金額* (NT$)</label>
              <input type="number" className="w-full border rounded px-2 py-1.5 text-sm" min="0.01" step="0.01"
                value={draft.amount || ''} onChange={(e) => setDraft({ ...draft, amount: Number(e.target.value) })} />
            </div>
            <div className="flex items-end">
              <button type="submit" disabled={submitting}
                className="w-full px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
                {submitting ? '送出中…' : '✓ 建立傳票'}
              </button>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            💡 多行借貸的複合傳票請用 AI 對話：<Link to="/chat" className="text-blue-600 underline">💬 AI 助手</Link>
          </p>
        </form>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12">載入中…</div>
      ) : entries.length === 0 ? (
        <div className="bg-white rounded-xl shadow">
          <EmptyState
            icon="📊"
            title="還沒有任何傳票"
            subtitle="傳票記錄公司每一筆會計動作（收款 / 付款 / 進貨 / 出貨成本）。配合 AI 對話可以自動生傳票。"
            primaryAction={{ label: '➕ 建第一筆傳票', onClick: () => setCreating(true) }}
            secondaryAction={{ label: '💬 用 AI 自動生', to: '/chat' }}
          />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">傳票號</th>
                <th className="text-left p-3">日期</th>
                <th className="text-left p-3">摘要</th>
                <th className="text-left p-3">狀態</th>
                <th className="text-right p-3 w-32">操作</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr key={e.id} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-mono text-xs">{e.entry_no}</td>
                  <td className="p-3 text-xs">{new Date(e.entry_date).toLocaleDateString('zh-TW')}</td>
                  <td className="p-3">{e.description || '—'}</td>
                  <td className="p-3">
                    <StatusBadge status={e.status} />
                  </td>
                  <td className="p-3 text-right">
                    {e.status === 'draft' && (
                      <button onClick={() => postEntry(e)}
                        className="px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 rounded">
                        ✓ 過帳
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 2. AR 應收帳款 Tab
// ────────────────────────────────────────────────────────────
function ARTab() {
  const [ars, setArs] = useState<AccountsReceivable[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [filter, setFilter] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  async function load() {
    setLoading(true); setErr(null)
    try {
      const [a, c] = await Promise.all([
        apiListAR().catch(() => []),
        apiListCustomers().catch(() => []),
      ])
      setArs(a); setCustomers(c)
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [])

  const customerName = (id: string) => customers.find(c => c.id === id)?.name || id.slice(0, 8)

  const filtered = useMemo(() => {
    if (!filter) return ars
    return ars.filter(ar => ar.status === filter)
  }, [ars, filter])

  const totalOpen = ars.filter(a => a.status !== 'paid').reduce((s, a) => s + (a.amount - a.paid_amount), 0)
  const totalOverdue = ars.filter(a => a.status === 'overdue').reduce((s, a) => s + (a.amount - a.paid_amount), 0)

  if (loading) return <div className="text-center text-gray-400 py-12">載入中…</div>

  return (
    <div>
      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <div className="bg-white rounded-xl shadow p-4 border-l-4 border-blue-500">
          <div className="text-xs text-gray-500">未收款總額</div>
          <div className="text-2xl font-bold mt-1">NT$ {totalOpen.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</div>
        </div>
        <div className="bg-white rounded-xl shadow p-4 border-l-4 border-red-500">
          <div className="text-xs text-gray-500">逾期未收</div>
          <div className="text-2xl font-bold mt-1 text-red-600">NT$ {totalOverdue.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</div>
        </div>
        <div className="bg-white rounded-xl shadow p-4 border-l-4 border-gray-300">
          <div className="text-xs text-gray-500">應收筆數</div>
          <div className="text-2xl font-bold mt-1">{ars.length}</div>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <select value={filter} onChange={(e) => setFilter(e.target.value)}
          className="border rounded px-2 py-1.5 text-sm">
          <option value="">全部狀態</option>
          <option value="open">未收</option>
          <option value="partial">部分收</option>
          <option value="paid">已收清</option>
          <option value="overdue">逾期</option>
        </select>
        <Link to="/chat" className="text-xs text-blue-600 hover:underline">
          💬 用 AI 開發票 / 標記收款
        </Link>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl shadow">
          <EmptyState
            icon="💵"
            title={filter ? `沒有 ${filter} 狀態的應收` : '還沒有任何應收帳款'}
            subtitle="應收帳款會在出貨開發票時自動產生。也可用 AI 對話手動建：「客戶 X 5/15 開發票 NT$ 50000」"
            primaryAction={{ label: '💬 去 AI 助手', to: '/chat' }}
            secondaryAction={{ label: '⚙️ 載入示範資料', to: '/settings' }}
            compact
          />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">發票號</th>
                <th className="text-left p-3">客戶</th>
                <th className="text-left p-3">開立日</th>
                <th className="text-left p-3">到期日</th>
                <th className="text-right p-3">金額</th>
                <th className="text-right p-3">已收</th>
                <th className="text-right p-3">未收</th>
                <th className="text-right p-3">帳齡</th>
                <th className="text-left p-3">狀態</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(ar => {
                const unpaid = ar.amount - ar.paid_amount
                return (
                  <tr key={ar.id} className={`border-t hover:bg-gray-50 ${ar.status === 'overdue' ? 'bg-red-50/40' : ''}`}>
                    <td className="p-3 font-mono text-xs">{ar.invoice_no}</td>
                    <td className="p-3">{customerName(ar.customer_id)}</td>
                    <td className="p-3 text-xs">{new Date(ar.invoice_date).toLocaleDateString('zh-TW')}</td>
                    <td className="p-3 text-xs">{new Date(ar.due_date).toLocaleDateString('zh-TW')}</td>
                    <td className="p-3 text-right font-mono">{ar.amount.toLocaleString('zh-TW')}</td>
                    <td className="p-3 text-right font-mono text-emerald-700">{ar.paid_amount.toLocaleString('zh-TW')}</td>
                    <td className={`p-3 text-right font-mono ${unpaid > 0 ? 'font-bold' : ''}`}>{unpaid.toLocaleString('zh-TW')}</td>
                    <td className="p-3 text-right text-xs">
                      <span className={ar.aging_days > 30 ? 'text-red-600 font-medium' : 'text-gray-500'}>
                        {ar.aging_days} 天
                      </span>
                    </td>
                    <td className="p-3"><StatusBadge status={ar.status} /></td>
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

// ────────────────────────────────────────────────────────────
// 3. Accounts 科目表 Tab
// ────────────────────────────────────────────────────────────
function AccountsTab() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState({ code: '', name: '', account_type: 'asset', is_debit_normal: true })
  const [err, setErr] = useState<string | null>(null)

  async function load() {
    setLoading(true); setErr(null)
    try { setAccounts(await apiListAccounts()) }
    catch (e: unknown) { setErr(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '載入失敗') }
    finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [])

  async function createAccount() {
    if (!draft.code.trim() || !draft.name.trim()) { setErr('代碼 + 名稱必填'); return }
    setErr(null)
    try {
      await apiCreateAccount(draft)
      setDraft({ code: '', name: '', account_type: 'asset', is_debit_normal: true })
      setCreating(false)
      await load()
    } catch (e: unknown) { setErr(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '新增失敗') }
  }

  const grouped = useMemo(() => {
    const g: Record<string, Account[]> = {}
    for (const a of accounts) (g[a.account_type] || (g[a.account_type] = [])).push(a)
    return g
  }, [accounts])

  const TYPE_LABELS: Record<string, string> = {
    asset: '🏦 資產', liability: '📉 負債', equity: '🧱 權益',
    revenue: '💰 收入', expense: '💸 費用', other: '📌 其他',
  }

  if (loading) return <div className="text-center text-gray-400 py-12">載入中…</div>

  return (
    <div>
      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}

      <div className="flex justify-end mb-4">
        <button onClick={() => setCreating(c => !c)}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
          {creating ? '取消' : '➕ 新增科目'}
        </button>
      </div>

      {creating && (
        <div className="bg-white rounded-xl shadow p-4 mb-4 grid md:grid-cols-5 gap-3">
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="代碼* 例 1101"
            value={draft.code} onChange={(e) => setDraft({ ...draft, code: e.target.value })} />
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="名稱* 例 現金"
            value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          <select className="border rounded px-2 py-1.5 text-sm" value={draft.account_type}
            onChange={(e) => setDraft({ ...draft, account_type: e.target.value, is_debit_normal: e.target.value === 'asset' || e.target.value === 'expense' })}>
            <option value="asset">資產</option><option value="liability">負債</option>
            <option value="equity">權益</option><option value="revenue">收入</option>
            <option value="expense">費用</option>
          </select>
          <label className="flex items-center gap-1 text-xs">
            <input type="checkbox" checked={draft.is_debit_normal}
              onChange={(e) => setDraft({ ...draft, is_debit_normal: e.target.checked })} />
            借方正常
          </label>
          <button onClick={createAccount}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
            ✓ 儲存
          </button>
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="bg-white rounded-xl shadow">
          <EmptyState
            icon="📚"
            title="科目表是空的"
            subtitle="會計科目是傳票的基礎。建議至少先建這 6 個：現金/應收/應付/銷貨收入/銷貨成本/管銷費用。可以載入示範資料一鍵帶入。"
            primaryAction={{ label: '➕ 新增第一個科目', onClick: () => setCreating(true) }}
            secondaryAction={{ label: '⚙️ 載入示範資料', to: '/settings' }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(grouped).map(([type, list]) => (
            <div key={type} className="bg-white rounded-xl shadow p-4">
              <h3 className="font-semibold text-sm mb-2">{TYPE_LABELS[type] || type}（{list.length}）</h3>
              <div className="space-y-1 text-sm">
                {list.map(a => (
                  <div key={a.id} className="flex items-center justify-between border-b border-gray-50 py-1 last:border-0">
                    <span className="font-mono text-xs text-gray-500 w-16">{a.code}</span>
                    <span className="flex-1 ml-2">{a.name}</span>
                    {!a.is_active && <span className="text-xs text-gray-400">已停用</span>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// Status badge (shared)
// ────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const m: Record<string, string> = {
    draft:   'bg-gray-100 text-gray-700',
    posted:  'bg-emerald-100 text-emerald-800',
    void:    'bg-red-100 text-red-700',
    open:    'bg-blue-100 text-blue-800',
    partial: 'bg-amber-100 text-amber-800',
    paid:    'bg-emerald-100 text-emerald-800',
    overdue: 'bg-red-100 text-red-700',
  }
  const labels: Record<string, string> = {
    draft: '草稿', posted: '已過帳', void: '作廢',
    open: '未收', partial: '部分收', paid: '已收清', overdue: '逾期',
  }
  return <span className={`px-2 py-1 rounded-full text-xs ${m[status] || 'bg-gray-100'}`}>
    {labels[status] || status}
  </span>
}
