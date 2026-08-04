import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiListPOs, apiListSuppliers, apiUpdateSupplier, apiDeleteSupplier,
  apiCancelPO, apiCreateSupplier, apiCreatePO,
  apiApprovePO, apiReceivePO, apiGetPO,
  apiListParts, type Part,
  apiListRFQs, apiCreateRFQ, apiSendRFQ, apiReceiveQuote, apiCompareRFQ, apiAwardRFQ,
  type RFQInfo,
  type PurchaseOrder, type Supplier,
  ApiError,
} from '../lib/api'
import EntityRowActions from '../components/EntityRowActions'
import EntityFormModal, { type FieldDef } from '../components/EntityFormModal'
import PrintableDocument, { DocHeader, DocFooter } from '../components/PrintableDocument'
import ProcessChain, { deriveP2PSteps } from '../components/ProcessChain'
import NotesEditor from '../components/NotesEditor'
import { useAuthStore } from '../store/auth'

// v3.50: 用後端 reportlab 端點下載完整明細 PDF（取代摘要式 HTML 列印）
async function downloadPoPdf(poId: string, poNo: string) {
  const token = useAuthStore.getState().token
  const res = await fetch(`/api/print/po/${poId}.pdf`, {
    headers: { 'Authorization': `Bearer ${token}` },
  })
  if (!res.ok) { alert('PDF 產生失敗'); return }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `PO_${poNo || poId}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

const SUPPLIER_FIELDS: FieldDef[] = [
  { name: 'name', label: '名稱', type: 'text', required: true },
  {
    name: 'tier', label: '等級', type: 'select',
    options: [
      { value: 'T1', label: 'T1 (策略)' },
      { value: 'T2', label: 'T2 (主力)' },
      { value: 'T3', label: 'T3 (一般)' },
    ],
  },
  { name: 'contact_person', label: '聯絡人', type: 'text' },
  { name: 'contact_phone', label: '電話', type: 'text' },
  { name: 'payment_terms', label: '付款條件', type: 'text' },
  { name: 'is_approved', label: '已核准', type: 'checkbox' },
  { name: 'is_active', label: '啟用', type: 'checkbox' },
]

export default function Purchase() {
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [parts, setParts] = useState<Part[]>([])   // v3.64 RFQ 選料用
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [tab, setTab] = useState<'orders' | 'suppliers' | 'rfq'>('orders')
  const [editingSup, setEditingSup] = useState<Supplier | null>(null)
  const [printPO, setPrintPO] = useState<PurchaseOrder | null>(null)
  const [chainPO, setChainPO] = useState<PurchaseOrder | null>(null)
  const [notesPO, setNotesPO] = useState<PurchaseOrder | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [p, s, pr] = await Promise.all([
        apiListPOs(filterStatus || undefined), apiListSuppliers(), apiListParts(),
      ])
      setPos(p); setSuppliers(s); setParts(pr)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [filterStatus])

  // v3.53: SSE auto-refresh so other users' actions update this screen live
  useEffect(() => {
    const token = useAuthStore.getState().token
    const url = token
      ? `/api/events/stream?access_token=${encodeURIComponent(token)}`
      : '/api/events/stream'
    const es = new EventSource(url)
    const refetch = () => { void load() }
    const events = [
      'po.created', 'po.approved', 'po.received', 'po.cancelled',
      'supplier.updated', 'supplier.deleted',
    ]
    for (const name of events) es.addEventListener(name, refetch)
    return () => {
      for (const name of events) es.removeEventListener(name, refetch)
      es.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cancelPO = async (po: PurchaseOrder) => {
    const reason = prompt(`取消採購單 ${po.po_no}\n\n請輸入取消原因：`)
    if (reason === null) return
    await apiCancelPO(po.id, reason)
    await load()
  }

  // v3.18：核准草稿單
  const approvePO = async (po: PurchaseOrder) => {
    if (!confirm(`核准採購單 ${po.po_no}？`)) return
    try { await apiApprovePO(po.id); await load() }
    catch (e: unknown) { alert(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '核准失敗') }
  }

  // v3.18：進貨（一次全收）
  const receivePOFull = async (po: PurchaseOrder) => {
    if (!confirm(`進貨：${po.po_no} 全部訂購量都收到？\n\n部分收貨請用 AI 對話。`)) return
    try {
      const detail = await apiGetPO(po.id)
      const items = detail.items || []
      if (items.length === 0) { alert('此採購單沒有項目'); return }
      const receipts = items
        .filter(it => (it.ordered_qty - (it.received_qty || 0)) > 0)
        .map(it => ({ item_id: it.id, received_qty: it.ordered_qty - (it.received_qty || 0) }))
      if (receipts.length === 0) { alert('所有項目已收齊'); return }
      await apiReceivePO(po.id, receipts)
      await load()
      alert(`✅ 進貨完成：${receipts.length} 項`)
    } catch (e: unknown) { alert(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '進貨失敗') }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">採購管理</h1>
        <div className="flex gap-3 items-center">
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setTab('orders')}
              className={`px-3 py-1.5 text-sm rounded ${tab === 'orders' ? 'bg-white shadow' : 'text-gray-500'}`}
            >📋 採購單</button>
            <button
              onClick={() => setTab('suppliers')}
              className={`px-3 py-1.5 text-sm rounded ${tab === 'suppliers' ? 'bg-white shadow' : 'text-gray-500'}`}
            >🏭 供應商</button>
            <button
              onClick={() => setTab('rfq')}
              className={`px-3 py-1.5 text-sm rounded ${tab === 'rfq' ? 'bg-white shadow' : 'text-gray-500'}`}
            >📨 RFQ 詢價</button>
          </div>
          {tab === 'orders' && (
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
              <option value="">全部狀態</option>
              <option value="draft">草稿</option>
              <option value="approved">已核准</option>
              <option value="sent">已發送</option>
              <option value="received">已收貨</option>
              <option value="partial_received">部分收貨</option>
              <option value="cancelled">已取消</option>
            </select>
          )}
        </div>
      </div>

      {/* v3.17: Quick create bar (Sprint K) */}
      <PurchaseQuickCreateBar suppliers={suppliers} onAfterCreate={load} />

      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat title="供應商總數" value={suppliers.length} />
        <Stat title="採購單總數" value={pos.length} />
        <Stat title="總金額 (TWD)" value={pos.reduce((sum, p) => sum + p.total_amount, 0).toLocaleString('zh-TW', { maximumFractionDigits: 0 })} />
      </div>

      {tab === 'rfq' ? (
        <RfqSection parts={parts} suppliers={suppliers} onAfterChange={load} />
      ) : tab === 'orders' ? (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">採購單號</th>
                <th className="text-left p-3">供應商</th>
                <th className="text-left p-3">狀態</th>
                <th className="text-right p-3">金額</th>
                <th className="text-left p-3">下單日期</th>
                <th className="text-right p-3 w-32">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">載入中…</td></tr>
              ) : pos.length === 0 ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無採購單資料</td></tr>
              ) : (
                pos.map(po => (
                  <tr key={po.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{po.po_no}</td>
                    <td className="p-3">{po.supplier?.name || po.supplier_id}</td>
                    <td className="p-3"><StatusBadge status={po.status} /></td>
                    <td className="p-3 text-right">{po.total_amount.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
                    <td className="p-3">{new Date(po.order_date).toLocaleDateString('zh-TW')}</td>
                    <td className="p-3 text-right">
                      <div className="flex gap-1 justify-end">
                        <button onClick={() => setChainPO(po)}
                          className="px-2 py-1 text-xs text-purple-700 hover:bg-purple-50 rounded"
                          title="看流程鏈狀態">📊</button>
                        <button onClick={() => setNotesPO(po)}
                          className="px-2 py-1 text-xs text-amber-700 hover:bg-amber-50 rounded"
                          title="編輯備註">📝</button>
                        <button onClick={() => downloadPoPdf(po.id, po.po_no)}
                          className="px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 rounded"
                          title="下載完整明細 PDF（含品項）">📥 PDF</button>
                        <button onClick={() => setPrintPO(po)}
                          className="px-2 py-1 text-xs text-gray-700 hover:bg-gray-100 rounded"
                          title="瀏覽器列印（HTML 摘要）">🖨</button>
                        {po.status === 'draft' && (
                          <button onClick={() => approvePO(po)}
                            className="px-2 py-1 text-xs text-blue-700 hover:bg-blue-50 rounded"
                            title="核准採購單">✓ 核准</button>
                        )}
                        {['approved', 'sent', 'partial_received'].includes(po.status) && (
                          <button onClick={() => receivePOFull(po)}
                            className="px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-50 rounded"
                            title="全部收貨">🚚 進貨</button>
                        )}
                        {!['received', 'cancelled'].includes(po.status) && (
                          <button onClick={() => cancelPO(po)}
                            className="px-2 py-1 text-xs text-red-700 hover:bg-red-50 rounded"
                            title="取消採購單">🚫</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">編號</th>
                <th className="text-left p-3">名稱</th>
                <th className="text-left p-3">等級</th>
                <th className="text-center p-3">已核准</th>
                <th className="text-center p-3">狀態</th>
                <th className="text-right p-3 w-32">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">載入中…</td></tr>
              ) : suppliers.length === 0 ? (
                <tr><td colSpan={6} className="p-4 text-center text-gray-400">尚無供應商資料</td></tr>
              ) : (
                suppliers.map(s => (
                  <tr key={s.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{s.code}</td>
                    <td className="p-3">{s.name}</td>
                    <td className="p-3">{s.tier}</td>
                    <td className="p-3 text-center">{s.is_approved ? '✅' : '—'}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${s.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100'}`}>
                        {s.is_active ? '啟用' : '停用'}
                      </span>
                    </td>
                    <td className="p-3">
                      <EntityRowActions
                        entityLabel="供應商"
                        entityName={`${s.code} ${s.name}`}
                        onEdit={() => setEditingSup(s)}
                        onDelete={() => apiDeleteSupplier(s.id)}
                        onAfterDelete={load}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {editingSup && (
        <EntityFormModal
          title={`編輯供應商 ${editingSup.code}`}
          fields={SUPPLIER_FIELDS}
          initial={editingSup as unknown as Record<string, unknown>}
          onSubmit={(patch) => apiUpdateSupplier(editingSup.id, patch as Partial<Supplier>)}
          onClose={() => setEditingSup(null)}
          onSuccess={() => { setEditingSup(null); load() }}
        />
      )}

      {/* v3.22: 備註編輯 */}
      {notesPO && (
        <NotesEditor entityType="po" entityId={notesPO.id} entityLabel={notesPO.po_no}
          initialRemark={(notesPO as PurchaseOrder & { remark?: string }).remark || null}
          onClose={() => setNotesPO(null)} onSaved={load} />
      )}

      {/* v3.22: 流程鏈視覺化 */}
      {chainPO && (
        <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
          onClick={() => setChainPO(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full my-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-3 border-b">
              <h2 className="font-semibold">📊 採購流程鏈 — {chainPO.po_no}</h2>
              <button onClick={() => setChainPO(null)} className="px-2 py-1 text-gray-500 hover:bg-gray-100 rounded text-sm">✕</button>
            </div>
            <div className="p-6">
              <ProcessChain
                title="P2P (Procure to Pay)"
                steps={deriveP2PSteps(chainPO.status, new Date(chainPO.order_date).toLocaleDateString('zh-TW'))}
              />
              <div className="mt-4 text-xs text-gray-500">
                💡 點 PO 列表的「🚚 進貨」按鈕推進進貨步驟。
              </div>
            </div>
          </div>
        </div>
      )}

      {/* v3.21: 列印 PO PDF */}
      {printPO && (
        <PrintableDocument title={`採購單 ${printPO.po_no}`} onClose={() => setPrintPO(null)}>
          <DocHeader docType="採購單 Purchase Order" docNo={printPO.po_no}
            date={new Date(printPO.order_date).toLocaleDateString('zh-TW')} />
          <table className="w-full text-sm mb-4">
            <tbody>
              <tr><td className="text-gray-600 py-1 w-32">供應商</td><td>{printPO.supplier?.name || printPO.supplier_id}</td></tr>
              <tr><td className="text-gray-600 py-1">狀態</td><td><StatusBadge status={printPO.status} /></td></tr>
              <tr><td className="text-gray-600 py-1">金額（含稅）</td><td className="font-bold text-lg">NT$ {printPO.total_amount.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td></tr>
              <tr><td className="text-gray-600 py-1">下單日期</td><td>{new Date(printPO.order_date).toLocaleDateString('zh-TW')}</td></tr>
            </tbody>
          </table>
          <div className="text-xs text-gray-500 italic mb-4">
            ※ 完整品項明細請至 Ouvoca 系統查詢，或開啟對話請 AI 列出。
          </div>
          <DocFooter note="請確認規格、數量、價格後簽回。" />
        </PrintableDocument>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────
// v3.64 RFQ 詢價比價
// ────────────────────────────────────────────────────────────
function RfqSection({ parts, suppliers, onAfterChange }: {
  parts: Part[]; suppliers: Supplier[]; onAfterChange: () => void
}) {
  const [rfqs, setRfqs] = useState<RFQInfo[]>([])
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  // 建立表單
  const [partId, setPartId] = useState('')
  const [qty, setQty] = useState(100)
  const [showCreate, setShowCreate] = useState(false)
  // 比價
  const [compare, setCompare] = useState<Awaited<ReturnType<typeof apiCompareRFQ>> | null>(null)
  // 報價表單
  const [quoteFor, setQuoteFor] = useState<string | null>(null)
  const [quoteSup, setQuoteSup] = useState('')
  const [quotePrice, setQuotePrice] = useState(0)
  const [quoteItem, setQuoteItem] = useState<{ part_id: string; qty: number } | null>(null)  // 健檢 #18

  async function load() {
    try { setRfqs(await apiListRFQs()) } catch { setRfqs([]) }
  }
  useEffect(() => { void load() }, [])

  async function create() {
    if (!partId) { setErr('請選擇料件'); return }
    setBusy('create'); setErr(null); setMsg(null)
    try {
      await apiCreateRFQ({ items: [{ part_id: partId, qty }] })
      setMsg('✅ RFQ 已建立')
      setShowCreate(false); setPartId(''); await load()
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '建立失敗')
    } finally { setBusy(null) }
  }

  async function send(id: string) {
    setBusy(id); setErr(null)
    try { await apiSendRFQ(id); setMsg('已送出詢價'); await load() }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '送出失敗') }
    finally { setBusy(null) }
  }

  async function compareRfq(id: string) {
    setBusy(id); setErr(null); setMsg(null)
    try { setCompare(await apiCompareRFQ(id)) }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '比價失敗') }
    finally { setBusy(null) }
  }

  async function submitQuote(rfqId: string) {
    if (!quoteSup) { setErr('請選擇供應商'); return }
    if (!quoteItem) { setErr('此詢價單沒有可報價的項目'); return }
    setBusy('quote')
    try {
      await apiReceiveQuote(rfqId, {
        supplier_id: quoteSup,
        items: [{ part_id: quoteItem.part_id, qty: quoteItem.qty, unit_price: quotePrice }],
      })
      setMsg('✅ 報價已登錄'); setQuoteFor(null); setQuoteItem(null); await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '登錄失敗') }
    finally { setBusy(null) }
  }

  async function award(rfqId: string, quoteId: string) {
    if (!window.confirm('決標後將自動轉採購單，確定？')) return
    setBusy('award')
    try {
      const r = await apiAwardRFQ(rfqId, quoteId)
      setMsg(`✅ 已決標並轉成 ${r.po_no}`)
      setCompare(null); await load(); onAfterChange()  // 健檢 #18：決標後刷新 PO 清單
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '決標失敗') }
    finally { setBusy(null) }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          {showCreate ? '取消' : '＋ 建立詢價單'}
        </button>
      </div>

      {showCreate && (
        <div className="galaxy-scan-card p-4 flex flex-wrap items-end gap-3">
          <label className="flex flex-col text-sm">
            <span className="text-gray-500 mb-1">料件</span>
            <select value={partId} onChange={e => setPartId(e.target.value)} className="input min-w-[200px]">
              <option value="">選擇料件…</option>
              {parts.map(p => <option key={p.id} value={p.id}>{p.part_no} {p.name}</option>)}
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="text-gray-500 mb-1">數量</span>
            <input type="number" value={qty} min={1} onChange={e => setQty(+e.target.value)} className="input w-32" />
          </label>
          <button onClick={() => void create()} disabled={busy === 'create'}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
            建立
          </button>
        </div>
      )}

      {msg && <div className="text-green-700 text-sm">{msg}</div>}
      {err && <div className="text-red-600 text-sm">{err}</div>}

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">詢價單號</th>
              <th className="text-left p-3">狀態</th>
              <th className="text-right p-3">報價數</th>
              <th className="text-right p-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {rfqs.length === 0 ? (
              <tr><td colSpan={4} className="p-4 text-center text-gray-400">尚無詢價單</td></tr>
            ) : rfqs.map(r => (
              <tr key={r.id} className="border-t">
                <td className="p-3 font-mono">{r.rfq_no}</td>
                <td className="p-3">{r.status}</td>
                <td className="p-3 text-right">{r.quote_count}</td>
                <td className="p-3 text-right space-x-2">
                  {r.status === 'draft' && (
                    <button onClick={() => void send(r.id)} disabled={busy !== null}
                      className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-500 disabled:opacity-40">送出</button>
                  )}
                  {r.status === 'sent' && (
                    <>
                      <button onClick={() => {
                        setQuoteFor(r.id)
                        setQuoteItem(r.items[0] ?? null)
                        setQuotePrice(0)
                        setErr(null)
                      }} disabled={busy !== null}
                        className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-500 disabled:opacity-40">登錄報價</button>
                      <button onClick={() => void compareRfq(r.id)} disabled={busy !== null}
                        className="px-2 py-1 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-500 disabled:opacity-40">比價</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {quoteFor && (
        <div className="galaxy-scan-card p-4 flex flex-wrap items-end gap-3">
          <label className="flex flex-col text-sm">
            <span className="text-gray-500 mb-1">供應商</span>
            <select value={quoteSup} onChange={e => setQuoteSup(e.target.value)} className="input min-w-[180px]">
              <option value="">選擇供應商…</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="text-gray-500 mb-1">單價</span>
            <input type="number" value={quotePrice} min={0} onChange={e => setQuotePrice(+e.target.value)} className="input w-32" />
          </label>
          <button onClick={() => void submitQuote(quoteFor)} disabled={busy === 'quote'}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">登錄</button>
          <button onClick={() => setQuoteFor(null)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg">取消</button>
        </div>
      )}

      {compare && (
        <div className="bg-white rounded-xl shadow p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">比價結果：{compare.rfq_no}</h3>
            <button onClick={() => setCompare(null)} className="text-sm text-gray-400 hover:text-gray-600">✕ 關閉</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr><th className="text-left p-2">報價</th><th className="text-right p-2">金額</th><th className="text-right p-2">操作</th></tr>
            </thead>
            <tbody>
              {compare.quotes.map(q => (
                <tr key={q.quote_id} className="border-t">
                  <td className="p-2 font-mono text-xs">{q.supplier_id}</td>
                  <td className="p-2 text-right">{q.amount.toLocaleString('zh-TW')}</td>
                  <td className="p-2 text-right">
                    <button onClick={() => void award(compare.rfq_id, q.quote_id)}
                      disabled={busy === 'award'}
                      className="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-500 disabled:opacity-40">決標</button>
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

function Stat({ title, value }: { title: string; value: number | string }) {
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    approved: 'bg-blue-100 text-blue-800',
    sent: 'bg-purple-100 text-purple-800',
    received: 'bg-green-100 text-green-800',
    partial_received: 'bg-yellow-100 text-yellow-800',
    cancelled: 'bg-red-100 text-red-800',
  }
  return <span className={`px-2 py-1 rounded-full text-xs ${m[status] || 'bg-gray-100'}`}>{status}</span>
}

// ────────────────────────────────────────────────────────────
// Quick create bar — 新增供應商 + 快速建採購單（Sprint K v3.17）
// ────────────────────────────────────────────────────────────
function PurchaseQuickCreateBar({ suppliers, onAfterCreate }: {
  suppliers: Supplier[]
  onAfterCreate: () => void | Promise<void>
}) {
  const [mode, setMode] = useState<'closed' | 'supplier' | 'po'>('closed')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [parts, setParts] = useState<Part[]>([])
  const [sup, setSup] = useState({ code: '', name: '', tier: 'T2', lead_time_days: 7 })
  const [po, setPo] = useState({ supplier_id: '', part_id: '', ordered_qty: 1, unit_price: 0 })

  useEffect(() => {
    if (mode === 'po' && parts.length === 0) {
      void apiListParts().then(setParts).catch(() => setParts([]))
    }
  }, [mode])

  async function createSupplier() {
    if (!sup.code.trim() || !sup.name.trim()) { setErr('代碼 + 名稱必填'); return }
    setBusy(true); setErr(null)
    try {
      await apiCreateSupplier({ ...sup, is_approved: true })
      setSup({ code: '', name: '', tier: 'T2', lead_time_days: 7 })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '新增失敗') }
    finally { setBusy(false) }
  }

  async function createPO() {
    if (!po.supplier_id || !po.part_id || po.ordered_qty <= 0) {
      setErr('供應商 + 料件 + 數量必填'); return
    }
    if (po.unit_price <= 0) {
      setErr('單價必須大於 0'); return
    }
    setBusy(true); setErr(null)
    try {
      await apiCreatePO({
        supplier_id: po.supplier_id,
        items: [{ part_id: po.part_id, ordered_qty: po.ordered_qty, unit_price: po.unit_price }],
      })
      setPo({ supplier_id: '', part_id: '', ordered_qty: 1, unit_price: 0 })
      setMode('closed')
      await onAfterCreate()
    } catch (e: unknown) { setErr(e instanceof ApiError ? e.friendly() : e instanceof Error ? e.message : '建單失敗') }
    finally { setBusy(false) }
  }

  return (
    <div className="bg-white rounded-xl shadow p-4 mb-6">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm font-medium text-gray-700 mr-2">新增：</span>
        <button onClick={() => setMode(mode === 'supplier' ? 'closed' : 'supplier')}
          className={`px-3 py-1.5 rounded text-sm ${mode === 'supplier' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}>
          ➕ 新增供應商
        </button>
        <button onClick={() => setMode(mode === 'po' ? 'closed' : 'po')}
          className={`px-3 py-1.5 rounded text-sm ${mode === 'po' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}>
          🛒 快速建採購單（1 項目）
        </button>
        <Link to="/chat" className="px-3 py-1.5 bg-purple-50 text-purple-700 hover:bg-purple-100 rounded text-sm">
          💬 用 AI 建多項目採購單
        </Link>
      </div>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mt-3 text-sm">{err}</div>}

      {mode === 'supplier' && (
        <form onSubmit={(e) => { e.preventDefault(); createSupplier() }} className="grid md:grid-cols-5 gap-2 mt-3 pt-3 border-t">
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="代碼* 例 SUP-001"
            value={sup.code} onChange={(e) => setSup({ ...sup, code: e.target.value })} />
          <input className="border rounded px-2 py-1.5 text-sm" placeholder="名稱*"
            value={sup.name} onChange={(e) => setSup({ ...sup, name: e.target.value })} />
          <select className="border rounded px-2 py-1.5 text-sm" value={sup.tier}
            onChange={(e) => setSup({ ...sup, tier: e.target.value })}>
            <option value="T1">T1 (策略)</option>
            <option value="T2">T2 (主力)</option>
            <option value="T3">T3 (一般)</option>
          </select>
          <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="交期天數" min="1"
            value={sup.lead_time_days} onChange={(e) => setSup({ ...sup, lead_time_days: Number(e.target.value) })} />
          <button type="submit" disabled={busy}
            className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {busy ? '儲存中…' : '✓ 儲存'}
          </button>
        </form>
      )}

      {mode === 'po' && (
        <form onSubmit={(e) => { e.preventDefault(); createPO() }} className="mt-3 pt-3 border-t">
          <div className="grid md:grid-cols-5 gap-2">
            <select className="border rounded px-2 py-1.5 text-sm" value={po.supplier_id}
              onChange={(e) => setPo({ ...po, supplier_id: e.target.value })}>
              <option value="">選供應商*</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select className="border rounded px-2 py-1.5 text-sm" value={po.part_id}
              onChange={(e) => setPo({ ...po, part_id: e.target.value })}>
              <option value="">選料件*</option>
              {parts.map(p => <option key={p.id} value={p.id}>{p.part_no} {p.name}</option>)}
            </select>
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="數量*" min="1"
              value={po.ordered_qty} onChange={(e) => setPo({ ...po, ordered_qty: Number(e.target.value) })} />
            <input type="number" className="border rounded px-2 py-1.5 text-sm" placeholder="單價"
              value={po.unit_price || ''} onChange={(e) => setPo({ ...po, unit_price: Number(e.target.value) })} />
            <button type="submit" disabled={busy}
              className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-50">
              {busy ? '建單中…' : '✓ 建單'}
            </button>
          </div>
          {parts.length === 0 && (
            <p className="text-xs text-gray-500 mt-2">
              💡 還沒有料件？先去 <Link to="/inventory" className="text-blue-600 underline">庫存頁</Link> 新增。
            </p>
          )}
        </form>
      )}
    </div>
  )
}
