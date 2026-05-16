/**
 * Settings — 系統設定頁（Sprint F + Sprint E v3.13）
 *
 * 3 區塊：
 *  1. Demo Data — 載入 / 清除 內建示範資料（透過既有 /api/onboarding endpoints）
 *  2. File Upload — 上傳業務文件（報價單 / 發票 / 合約），LLM 後續可 parse
 *  3. System Info — 版本、授權軌
 *
 * 設計：
 *  - 危險操作（clear demo / delete attachment）需 confirm()
 *  - 操作後自動 refresh 狀態（不需手動 reload 頁面）
 */
import { useEffect, useRef, useState } from 'react'
import {
  apiOnboardingStatus, apiSeedDemo, apiClearDemo, type OnboardingStatus,
  apiUploadAttachment, apiListAttachments, apiDeleteAttachment,
  downloadAttachmentUrl, type Attachment,
  apiLlmStatus, apiLlmTest, apiLlmConfigure, type LlmStatus,
} from '../lib/api'

const CATEGORIES: { value: string; label: string }[] = [
  { value: 'quote',    label: '📋 客戶報價單' },
  { value: 'po',       label: '🛒 供應商報價 / 採購單' },
  { value: 'invoice',  label: '💵 發票' },
  { value: 'spec',     label: '📐 規格書 / 圖紙' },
  { value: 'contract', label: '📜 合約' },
  { value: 'general',  label: '📎 一般附件' },
]

export default function Settings() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">⚙️ 系統設定</h1>
        <p className="text-sm text-gray-500 mt-1">
          管理示範資料、上傳業務文件、查看系統資訊
        </p>
      </div>

      <AiSettingsSection />
      <DemoDataSection />
      <FileUploadSection />
      <SystemInfoSection />
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 0. AI 助手設定（Sprint H v3.14）
// ────────────────────────────────────────────────────────────

const PROVIDERS: { value: 'deepseek' | 'openai' | 'anthropic' | 'ollama'; label: string; desc: string; signup: string }[] = [
  { value: 'deepseek',  label: '🇨🇳 DeepSeek（推薦）', desc: '最便宜、有免費額度；中英文能力強', signup: 'https://platform.deepseek.com/sign_up' },
  { value: 'openai',    label: '🇺🇸 OpenAI (GPT-4o)',  desc: '老牌、最穩、最貴',                signup: 'https://platform.openai.com/signup' },
  { value: 'anthropic', label: '🇺🇸 Anthropic Claude', desc: '推理 / 寫文章 / Code 能力強',     signup: 'https://console.anthropic.com/' },
  { value: 'ollama',    label: '🏠 Ollama（離線）',    desc: '本機跑、零成本、需自備 GPU',       signup: 'https://ollama.com/download' },
]

function AiSettingsSection() {
  const [status, setStatus] = useState<LlmStatus | null>(null)
  const [provider, setProvider] = useState<'deepseek' | 'openai' | 'anthropic' | 'ollama'>('deepseek')
  const [apiKey, setApiKey] = useState('')
  const [verifySsl, setVerifySsl] = useState(true)
  const [showKey, setShowKey] = useState(false)
  const [busy, setBusy] = useState<'test' | 'save' | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; ms?: number } | null>(null)

  async function load() {
    try {
      const s = await apiLlmStatus()
      setStatus(s)
      setProvider(s.provider)
      setVerifySsl(s.verify_ssl)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '載入失敗')
    }
  }
  useEffect(() => { load() }, [])

  async function doTest() {
    if (!apiKey.trim() && provider !== 'ollama') {
      setErr('請先貼入 API Key')
      return
    }
    setBusy('test'); setErr(null); setMsg(null); setTestResult(null)
    try {
      const r = await apiLlmTest({ provider, api_key: apiKey || 'ollama-no-key-needed', verify_ssl: verifySsl })
      setTestResult({ success: r.success, message: r.message, ms: r.response_ms })
      if (!r.success && r.detail) setErr(r.detail)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '測試失敗')
    } finally { setBusy(null) }
  }

  async function doSave() {
    if (!apiKey.trim() && provider !== 'ollama') {
      setErr('請先貼入 API Key')
      return
    }
    setBusy('save'); setErr(null); setMsg(null)
    try {
      const r = await apiLlmConfigure({ provider, api_key: apiKey || 'ollama-no-key', verify_ssl: verifySsl })
      setMsg(r.message)
      setApiKey('')  // 清掉 input 避免被別人看到
      await load()
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '儲存失敗')
    } finally { setBusy(null) }
  }

  const currentProvider = PROVIDERS.find(p => p.value === provider)

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <div className="flex items-start justify-between mb-1">
        <h2 className="text-lg font-semibold">🤖 AI 助手設定</h2>
        {status && (
          status.configured ? (
            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700 font-medium">
              ✓ 已啟用（{status.provider}）
            </span>
          ) : (
            <span className="px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700 font-medium">
              ⚠️ 未設定
            </span>
          )
        )}
      </div>
      <p className="text-sm text-gray-500 mb-4">
        申請 LLM API Key 啟用對話式 CRUD（查 / 增 / 改 / 刪 用講的）。
        <strong className="ml-1">不設也能用所有非 AI 功能</strong>，但會少了 erpilot 最大的賣點。
      </p>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
      {msg && <div className="bg-green-50 text-green-700 px-3 py-2 rounded mb-3 text-sm">{msg}</div>}

      {status && (
        <div className="grid md:grid-cols-3 gap-3 mb-4 text-xs">
          <Stat label="當前 Provider" value={status.provider} />
          <Stat label="當前 Model" value={status.model || '—'} />
          <Stat label="上次測試"
            value={
              status.last_test_success === true ? '✅ 成功'
              : status.last_test_success === false ? `❌ ${status.last_test_error || '失敗'}`
              : '—'
            }
          />
        </div>
      )}

      <div className="space-y-3 mb-4">
        <div>
          <label className="block text-xs text-gray-600 mb-1">選 Provider</label>
          <select
            value={provider} onChange={(e) => setProvider(e.target.value as typeof provider)}
            className="w-full border rounded px-2 py-1.5 text-sm"
          >
            {PROVIDERS.map(p => (
              <option key={p.value} value={p.value}>{p.label} — {p.desc}</option>
            ))}
          </select>
          {currentProvider && (
            <p className="text-xs text-gray-500 mt-1">
              還沒帳號？
              <a href={currentProvider.signup} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline ml-1">
                去申請 →
              </a>
              {' '}（5 分鐘）
            </p>
          )}
        </div>

        {provider !== 'ollama' && (
          <div>
            <label className="block text-xs text-gray-600 mb-1">API Key</label>
            <div className="flex gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="flex-1 border rounded px-2 py-1.5 text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(v => !v)}
                className="px-2 py-1 text-xs border rounded hover:bg-gray-50"
              >
                {showKey ? '🙈 隱藏' : '👁 顯示'}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              貼入後 key 會即時生效（不需重啟）。寫入 <code className="bg-gray-100 px-1 rounded">backend/.env</code>。
            </p>
          </div>
        )}

        <div>
          <label className="flex items-center gap-2 text-xs text-gray-700">
            <input type="checkbox" checked={verifySsl} onChange={(e) => setVerifySsl(e.target.checked)} />
            驗證 SSL 證書
            <span className="text-gray-500">
              （Windows 連 DeepSeek 失敗時可關掉。Mac/Linux/production 請維持開啟）
            </span>
          </label>
        </div>
      </div>

      {testResult && (
        <div className={`px-3 py-2 rounded mb-3 text-sm ${testResult.success ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'}`}>
          {testResult.message}
          {testResult.ms != null && <span className="ml-2 text-xs opacity-75">({testResult.ms} ms)</span>}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={doTest} disabled={busy !== null}
          className="px-4 py-2 border border-blue-600 text-blue-600 rounded hover:bg-blue-50 disabled:opacity-50 text-sm"
        >
          {busy === 'test' ? '測試中…' : '🧪 測試連線（不儲存）'}
        </button>
        <button
          onClick={doSave} disabled={busy !== null}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {busy === 'save' ? '儲存中…' : '💾 儲存（即時生效）'}
        </button>
      </div>

      <div className="mt-4 text-xs text-gray-600 bg-blue-50 rounded p-3">
        📖 不知道怎麼申請？看完整教學：
        <a
          href="https://github.com/fanchanyu/erpilot/blob/main/docs/HOW_TO_GET_LLM_API_KEY_ZH.md"
          target="_blank" rel="noopener noreferrer"
          className="text-blue-600 underline ml-1"
        >
          docs/HOW_TO_GET_LLM_API_KEY_ZH.md
        </a>
        {' '}（含 3 個 provider 比較 + 圖文步驟）
      </div>
    </section>
  )
}

// ────────────────────────────────────────────────────────────
// 1. Demo Data
// ────────────────────────────────────────────────────────────
function DemoDataSection() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [busy, setBusy] = useState<'seed' | 'clear' | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function load() {
    setErr(null)
    try { setStatus(await apiOnboardingStatus()) }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入狀態失敗') }
  }

  useEffect(() => { load() }, [])

  async function seed() {
    setBusy('seed'); setMsg(null); setErr(null)
    try {
      const r = await apiSeedDemo()
      setMsg(r.message)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
    finally { setBusy(null) }
  }

  async function clear() {
    if (!confirm('確定清除所有 DEMO- 前綴的示範資料？\n\n此動作不可復原。')) return
    setBusy('clear'); setMsg(null); setErr(null)
    try {
      const r = await apiClearDemo()
      setMsg(r.message)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '清除失敗') }
    finally { setBusy(null) }
  }

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">📦 示範資料</h2>
      <p className="text-sm text-gray-500 mb-4">
        系統內建一組示範資料（5 客戶 / 3 供應商 / 10 料件，以 <code className="bg-gray-100 px-1 rounded">DEMO-</code> 前綴）方便試用。試完可一鍵清除。
      </p>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
      {msg && <div className="bg-green-50 text-green-700 px-3 py-2 rounded mb-3 text-sm">{msg}</div>}

      {status && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
          <Stat label="客戶（DEMO / 總計）" value={`${status.demo_customers} / ${status.total_customers}`} />
          <Stat label="供應商" value={`${status.demo_suppliers} / ${status.total_suppliers}`} />
          <Stat label="料件" value={`${status.demo_parts} / ${status.total_parts}`} />
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={seed} disabled={busy !== null}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {busy === 'seed' ? '載入中…' : '➕ 載入示範資料'}
        </button>
        <button
          onClick={clear} disabled={busy !== null || (status?.demo_customers ?? 0) + (status?.demo_suppliers ?? 0) + (status?.demo_parts ?? 0) === 0}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 text-sm"
          title="清除所有 DEMO- 前綴資料"
        >
          {busy === 'clear' ? '清除中…' : '🗑 清除示範資料'}
        </button>
      </div>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold mt-0.5 font-mono">{value}</div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// 2. File Upload
// ────────────────────────────────────────────────────────────
function FileUploadSection() {
  const [files, setFiles] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [filterCat, setFilterCat] = useState<string>('')
  const [category, setCategory] = useState<string>('quote')
  const [description, setDescription] = useState<string>('')
  const [dragOver, setDragOver] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function load() {
    setLoading(true); setErr(null)
    try { setFiles(await apiListAttachments(filterCat || undefined)) }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [filterCat])

  async function doUpload(file: File) {
    if (!file) return
    setUploading(true); setErr(null); setMsg(null)
    try {
      const att = await apiUploadAttachment(file, category, description || undefined)
      setMsg(`✅ 上傳成功：${att.filename}（${(att.size_bytes / 1024).toFixed(1)} KB）`)
      setDescription('')
      await load()
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '上傳失敗')
    } finally {
      setUploading(false)
    }
  }

  async function remove(att: Attachment) {
    if (!confirm(`確定刪除「${att.filename}」？\n\n此動作不可復原。`)) return
    setErr(null)
    try {
      await apiDeleteAttachment(att.id)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '刪除失敗') }
  }

  function fmt(n: number): string {
    if (n < 1024) return `${n} B`
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
    return `${(n / 1024 / 1024).toFixed(1)} MB`
  }

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">📁 上傳業務文件</h2>
      <p className="text-sm text-gray-500 mb-4">
        上傳報價單 / 發票 / 合約 / 規格書 等檔案。後續可由 AI 助手解析成系統實體（如：報價單 → 銷售單）。
      </p>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
      {msg && <div className="bg-green-50 text-green-700 px-3 py-2 rounded mb-3 text-sm">{msg}</div>}

      {/* 上傳區 */}
      <div className="grid md:grid-cols-3 gap-3 mb-4">
        <div>
          <label className="block text-xs text-gray-600 mb-1">分類</label>
          <select
            value={category} onChange={(e) => setCategory(e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-sm"
          >
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="block text-xs text-gray-600 mb-1">說明（選填）</label>
          <input
            type="text" value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="例：示範客戶 A 5/15 報價 100 個 M6 螺絲"
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
        </div>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragOver(false)
          const f = e.dataTransfer.files[0]
          if (f) doUpload(f)
        }}
        onClick={() => inputRef.current?.click()}
        className={[
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50',
          uploading ? 'opacity-50 pointer-events-none' : '',
        ].join(' ')}
      >
        <input
          ref={inputRef} type="file"
          accept=".pdf,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.docx,.txt"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) doUpload(f) }}
          className="hidden"
        />
        <div className="text-4xl mb-2">{uploading ? '⏳' : '📤'}</div>
        <div className="text-sm font-medium text-gray-700">
          {uploading ? '上傳中…' : '點此選檔，或拖拉檔案到這裡'}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          支援：PDF / Excel / CSV / Word / 圖片，每檔上限 25 MB
        </div>
      </div>

      {/* 過濾 + 列表 */}
      <div className="flex items-center justify-between mt-6 mb-3">
        <h3 className="text-sm font-semibold text-gray-700">已上傳檔案</h3>
        <select
          value={filterCat} onChange={(e) => setFilterCat(e.target.value)}
          className="border rounded px-2 py-1 text-xs"
        >
          <option value="">全部分類</option>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">檔名</th>
              <th className="text-left p-2">分類</th>
              <th className="text-left p-2 hidden md:table-cell">說明</th>
              <th className="text-right p-2">大小</th>
              <th className="text-left p-2 hidden md:table-cell">上傳時間</th>
              <th className="text-center p-2">動作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="p-4 text-center text-gray-400">載入中…</td></tr>
            ) : files.length === 0 ? (
              <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無上傳檔案</td></tr>
            ) : (
              files.map(f => {
                const cat = CATEGORIES.find(c => c.value === f.category)
                return (
                  <tr key={f.id} className="border-t hover:bg-gray-50">
                    <td className="p-2 font-mono text-xs truncate max-w-[200px]" title={f.filename}>{f.filename}</td>
                    <td className="p-2 text-xs">{cat?.label || f.category}</td>
                    <td className="p-2 hidden md:table-cell text-xs text-gray-600 truncate max-w-[200px]" title={f.description || ''}>{f.description || '—'}</td>
                    <td className="p-2 text-right text-xs font-mono">{fmt(f.size_bytes)}</td>
                    <td className="p-2 hidden md:table-cell text-xs text-gray-500">
                      {new Date(f.uploaded_at).toLocaleString('zh-TW', { hour12: false })}
                    </td>
                    <td className="p-2 text-center">
                      <div className="flex gap-1 justify-center">
                        <a
                          href={downloadAttachmentUrl(f.id)} target="_blank" rel="noopener noreferrer"
                          className="px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 rounded"
                          title="下載"
                        >📥</a>
                        <button
                          onClick={() => remove(f)}
                          className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded"
                          title="刪除"
                        >🗑</button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ────────────────────────────────────────────────────────────
// 3. System Info
// ────────────────────────────────────────────────────────────
function SystemInfoSection() {
  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-1">ℹ️ 系統資訊</h2>
      <p className="text-sm text-gray-500 mb-4">關於 erpilot 此安裝</p>

      <div className="grid md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
        <InfoRow label="版本" value="v3.13" />
        <InfoRow label="作者" value={<a className="text-blue-600 hover:underline" href="https://github.com/fanchanyu" target="_blank" rel="noopener noreferrer">by Peter</a>} />
        <InfoRow label="授權" value="AGPL-3.0 / Small Business / Commercial" />
        <InfoRow label="文件" value={<a className="text-blue-600 hover:underline" href="https://github.com/fanchanyu/erpilot" target="_blank" rel="noopener noreferrer">GitHub Repo</a>} />
        <InfoRow label="小小企業免費門檻" value="≤ 20 concurrent users" />
        <InfoRow label="商業授權諮詢" value={<a className="text-blue-600 hover:underline" href="https://github.com/fanchanyu/erpilot/blob/main/LICENSE-COMMERCIAL.md" target="_blank" rel="noopener noreferrer">查看方案</a>} />
      </div>
    </section>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-gray-100 py-1.5">
      <span className="text-gray-600">{label}</span>
      <span className="font-medium text-gray-800">{value}</span>
    </div>
  )
}
