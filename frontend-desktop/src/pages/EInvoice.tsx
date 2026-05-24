/**
 * EInvoice — 電子發票頁（Sprint M v3.19，schema 對齊版）
 *
 * 對齊 backend app/api/tax_tw.py EInvoiceCreateRequest:
 *   invoice_no / seller_tax_id / seller_name / buyer_* / items[]
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiIssueEInvoice, apiCancelEInvoice, apiGetEInvoice, apiValidateTaxId,
  apiListTaxIdCountries,
  type EInvoiceLineItem,
} from '../lib/api'
import { useAuthStore } from '../store/auth'
import PrintableDocument, { DocHeader, DocFooter } from '../components/PrintableDocument'

const BLANK_ITEM = (): EInvoiceLineItem => ({ description: '', qty: 1, unit_price: 0 })

export default function EInvoicePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">🧾 電子發票</h1>
        <p className="text-sm text-gray-500 mt-1">
          台灣財政部 e-invoice 開立 / 查詢 / 作廢
        </p>
      </div>

      <IssueSection />
      <LookupSection />
      <CancelSection />
    </div>
  )
}

function IssueSection() {
  // Default 自家公司資訊（之後可從 settings 帶入）
  const [seller, setSeller] = useState({ tax_id: '04595257', name: '示範公司股份有限公司' })  // 04595257 = 已知有效統編
  const [buyer, setBuyer] = useState({ tax_id: '', name: '', country: 'TW' })  // v3.20: 加 country
  const [invoiceNo, setInvoiceNo] = useState(() => `AA-${Date.now().toString().slice(-8)}`)
  const [items, setItems] = useState<EInvoiceLineItem[]>([BLANK_ITEM()])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [issued, setIssued] = useState<{ invoice_no: string; tracking_no?: string } | null>(null)
  const [printSnapshot, setPrintSnapshot] = useState<{
    invoice_no: string; seller_name: string; seller_tax_id: string
    buyer_name: string; buyer_tax_id: string
    sales_amount: number; tax: number; total: number
    items: EInvoiceLineItem[]
  } | null>(null)
  const [taxIdValid, setTaxIdValid] = useState<{ valid: boolean; message?: string } | null>(null)
  const [countries, setCountries] = useState<Array<{ code: string; name: string }>>([
    { code: 'TW', name: '🇹🇼 台灣' }, { code: 'GENERIC', name: '🌐 不驗證' },
  ])

  useEffect(() => {
    // 載入支援的國家清單
    apiListTaxIdCountries().then(r => setCountries(r.countries)).catch(() => {/* 用 fallback */})
  }, [])

  const total = items.reduce((s, it) => s + (it.qty * it.unit_price), 0)
  const taxIncluded = Math.round(total)            // 含稅總額
  const salesAmount = Math.round(taxIncluded / 1.05) // 未稅
  const tax = taxIncluded - salesAmount

  async function validateTaxId() {
    if (!buyer.tax_id.trim()) {
      setTaxIdValid({ valid: false, message: '請輸入統編' }); return
    }
    try {
      const r = await apiValidateTaxId(buyer.tax_id, buyer.country)
      setTaxIdValid({ valid: r.valid, message: r.message })
    } catch (e: unknown) {
      setTaxIdValid({ valid: false, message: e instanceof Error ? e.message : '查詢失敗' })
    }
  }

  function addItem() { setItems([...items, BLANK_ITEM()]) }
  function removeItem(i: number) { setItems(items.filter((_, idx) => idx !== i)) }
  function updateItem(i: number, patch: Partial<EInvoiceLineItem>) {
    setItems(items.map((it, idx) => idx === i ? { ...it, ...patch } : it))
  }

  async function issue() {
    if (!seller.tax_id || !seller.name) { setErr('我方統編 + 公司名必填'); return }
    if (!invoiceNo) { setErr('發票號必填'); return }
    const validItems = items.filter(it => it.description && it.qty > 0 && it.unit_price > 0)
    if (validItems.length === 0) { setErr('至少一個項目（含品名/數量/單價）'); return }

    setBusy(true); setErr(null); setIssued(null)
    try {
      const result = await apiIssueEInvoice({
        invoice_no: invoiceNo,
        seller_tax_id: seller.tax_id, seller_name: seller.name,
        buyer_tax_id: buyer.tax_id || undefined,
        buyer_name: buyer.name || undefined,
        items: validItems,
      })
      if (!result.success) {
        setErr(`開立失敗：${result.errors?.join(', ') || '未知錯誤'}`)
        setBusy(false); return
      }
      setIssued({ invoice_no: invoiceNo, tracking_no: result.tracking_no })
      // v3.22: 留 snapshot 用於列印（後端不存 issued 細節，前端自留）
      setPrintSnapshot({
        invoice_no: invoiceNo,
        seller_name: seller.name, seller_tax_id: seller.tax_id,
        buyer_name: buyer.name, buyer_tax_id: buyer.tax_id,
        sales_amount: salesAmount, tax, total: taxIncluded,
        items: items.filter(it => it.description && it.qty > 0),
      })
      // 重置：留 seller，更新發票號，清項目
      setInvoiceNo(`AA-${Date.now().toString().slice(-8)}`)
      setBuyer({ tax_id: '', name: '', country: buyer.country })
      setItems([BLANK_ITEM()])
      setTaxIdValid(null)
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '開立失敗') }
    finally { setBusy(false) }
  }

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-4">📝 開立電子發票</h2>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
      {issued && (
        <div className="bg-emerald-50 border border-emerald-200 rounded p-3 mb-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="font-semibold text-emerald-900">✅ 發票 {issued.invoice_no} 已開立</div>
              {issued.tracking_no && <div className="text-xs mt-1">tracking_no: <span className="font-mono">{issued.tracking_no}</span></div>}
            </div>
            {printSnapshot && (
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    // v3.50: 呼叫後端 PDF 端點，含完整品項明細（取代摘要式 HTML）
                    const token = useAuthStore.getState().token
                    const payload = {
                      invoice_no: printSnapshot.invoice_no,
                      invoice_date: new Date().toISOString().slice(0, 10),
                      seller_tax_id: printSnapshot.seller_tax_id,
                      seller_name: printSnapshot.seller_name,
                      buyer_tax_id: printSnapshot.buyer_tax_id,
                      buyer_name: printSnapshot.buyer_name,
                      items: printSnapshot.items.map(it => ({
                        description: it.description,
                        qty: it.qty,
                        unit_price: it.unit_price,
                        amount: it.qty * it.unit_price,
                      })),
                      total: printSnapshot.sales_amount,
                      tax: printSnapshot.tax,
                      grand_total: printSnapshot.total,
                      tracking_no: issued.tracking_no || '',
                    }
                    const res = await fetch('/api/print/einvoice', {
                      method: 'POST',
                      headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify(payload),
                    })
                    if (!res.ok) { alert('PDF 產生失敗，請稍候再試'); return }
                    const blob = await res.blob()
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `einvoice_${printSnapshot.invoice_no}.pdf`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                  title="下載完整明細 PDF（推薦）"
                >📥 下載 PDF 發票</button>
                <button
                  onClick={() => {
                    // 開啟瀏覽器列印視窗（HTML 摘要版）
                    setPrintSnapshot({ ...printSnapshot })  // re-trigger
                  }}
                  className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700"
                  title="瀏覽器列印（HTML）"
                >🖨 瀏覽器列印</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 列印發票（剛開立 / 重印） */}
      {printSnapshot && issued && (
        <PrintableDocument
          title={`電子發票 ${printSnapshot.invoice_no}`}
          onClose={() => setPrintSnapshot(null)}
        >
          <DocHeader docType="統一發票 e-Invoice" docNo={printSnapshot.invoice_no}
            date={new Date().toLocaleDateString('zh-TW')}
            companyName={printSnapshot.seller_name || '示範公司股份有限公司'} />
          <table className="w-full text-sm mb-4">
            <tbody>
              <tr><td className="text-gray-600 py-1 w-32">賣方統編</td><td className="font-mono">{printSnapshot.seller_tax_id}</td></tr>
              <tr><td className="text-gray-600 py-1">買方</td><td>{printSnapshot.buyer_name || '個人 / 無'}</td></tr>
              {printSnapshot.buyer_tax_id && (
                <tr><td className="text-gray-600 py-1">買方統編</td><td className="font-mono">{printSnapshot.buyer_tax_id}</td></tr>
              )}
            </tbody>
          </table>

          <table className="w-full text-sm mb-4 border-t border-gray-300">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">品名</th>
                <th className="text-right p-2 w-20">數量</th>
                <th className="text-right p-2 w-24">單價</th>
                <th className="text-right p-2 w-24">小計</th>
              </tr>
            </thead>
            <tbody>
              {printSnapshot.items.map((it, i) => (
                <tr key={i} className="border-b border-gray-100">
                  <td className="p-2">{it.description}</td>
                  <td className="p-2 text-right">{it.qty}</td>
                  <td className="p-2 text-right">{it.unit_price.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
                  <td className="p-2 text-right">{(it.qty * it.unit_price).toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-400">
                <td colSpan={3} className="p-2 text-right text-gray-600">未稅 / Sales Amount</td>
                <td className="p-2 text-right font-mono">{printSnapshot.sales_amount.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
              </tr>
              <tr>
                <td colSpan={3} className="p-2 text-right text-gray-600">稅 5% / Tax</td>
                <td className="p-2 text-right font-mono">{printSnapshot.tax.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
              </tr>
              <tr className="border-t">
                <td colSpan={3} className="p-2 text-right font-bold">總計 / Total</td>
                <td className="p-2 text-right font-bold text-lg">NT$ {printSnapshot.total.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
              </tr>
            </tfoot>
          </table>
          <DocFooter note="本發票經財政部 MIG 規範開立。如有問題請洽國稅局或開立公司。" />
        </PrintableDocument>
      )}

      <div className="space-y-4">
        {/* 我方 */}
        <fieldset className="border rounded p-3">
          <legend className="text-xs font-medium px-1 text-gray-600">🏢 我方（開立方）</legend>
          <div className="grid md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">統一編號*</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm font-mono" maxLength={8}
                value={seller.tax_id} onChange={(e) => setSeller({ ...seller, tax_id: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs text-gray-600 mb-1">公司名稱*</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm"
                value={seller.name} onChange={(e) => setSeller({ ...seller, name: e.target.value })} />
            </div>
          </div>
        </fieldset>

        {/* 買方 — v3.20 支援多國統編 */}
        <fieldset className="border rounded p-3">
          <legend className="text-xs font-medium px-1 text-gray-600">👤 買方</legend>
          <div className="grid md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">統編國別</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm"
                value={buyer.country}
                onChange={(e) => { setBuyer({ ...buyer, country: e.target.value }); setTaxIdValid(null) }}>
                {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs text-gray-600 mb-1">買方統編（公司必填，個人留空）</label>
              <div className="flex gap-2">
                <input className="flex-1 border rounded px-2 py-1.5 text-sm font-mono"
                  placeholder={buyer.country === 'TW' ? '8 位數字' : buyer.country === 'US' ? 'XX-XXXXXXX' : '依國別格式'}
                  value={buyer.tax_id}
                  onChange={(e) => { setBuyer({ ...buyer, tax_id: e.target.value }); setTaxIdValid(null) }} />
                <button onClick={validateTaxId} disabled={!buyer.tax_id}
                  className="px-2 py-1 border border-blue-500 text-blue-600 rounded text-xs hover:bg-blue-50 disabled:opacity-50">
                  驗
                </button>
              </div>
              {taxIdValid && (
                <p className={`text-xs mt-1 ${taxIdValid.valid ? 'text-emerald-600' : 'text-red-600'}`}>
                  {taxIdValid.valid ? `✓ ${taxIdValid.message || '有效'}` : `❌ ${taxIdValid.message || '無效'}`}
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">買方名稱</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm"
                placeholder="個人寫姓名 / 公司寫公司名"
                value={buyer.name} onChange={(e) => setBuyer({ ...buyer, name: e.target.value })} />
            </div>
          </div>
        </fieldset>

        {/* 發票號 + 項目 */}
        <fieldset className="border rounded p-3">
          <legend className="text-xs font-medium px-1 text-gray-600">📄 發票內容</legend>
          <div className="mb-3">
            <label className="block text-xs text-gray-600 mb-1">發票號*</label>
            <input className="w-full md:w-1/3 border rounded px-2 py-1.5 text-sm font-mono"
              value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
            <span className="text-xs text-gray-500 ml-2">已自動產一個，可改</span>
          </div>

          <label className="block text-xs text-gray-600 mb-1">項目（最少 1 行）*</label>
          {items.map((it, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 mb-2">
              <input className="col-span-6 border rounded px-2 py-1.5 text-sm" placeholder="品名 / 描述"
                value={it.description} onChange={(e) => updateItem(i, { description: e.target.value })} />
              <input type="number" className="col-span-2 border rounded px-2 py-1.5 text-sm" placeholder="數量" min="0.01" step="0.01"
                value={it.qty || ''} onChange={(e) => updateItem(i, { qty: Number(e.target.value) })} />
              <input type="number" className="col-span-3 border rounded px-2 py-1.5 text-sm" placeholder="單價 (含稅)" min="0.01" step="0.01"
                value={it.unit_price || ''} onChange={(e) => updateItem(i, { unit_price: Number(e.target.value) })} />
              <button onClick={() => removeItem(i)} disabled={items.length === 1}
                className="col-span-1 text-red-500 hover:bg-red-50 rounded disabled:opacity-30">✕</button>
            </div>
          ))}
          <button onClick={addItem} className="text-xs text-blue-600 hover:underline">+ 加項目</button>
        </fieldset>

        {/* 金額預覽 */}
        <div className="bg-gray-50 rounded p-3 grid grid-cols-3 gap-2 text-sm">
          <div>未稅 NT$ <strong>{salesAmount.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</strong></div>
          <div>稅 (5%) NT$ <strong>{tax.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</strong></div>
          <div>含稅合計 NT$ <strong className="text-blue-700">{taxIncluded.toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</strong></div>
        </div>

        <button onClick={issue} disabled={busy}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50">
          {busy ? '開立中…' : '🧾 開立發票'}
        </button>

        <p className="text-xs text-gray-500">
          💡 大量批次開請走 <Link to="/chat" className="text-blue-600 underline">AI 助手</Link>。
        </p>
      </div>
    </section>
  )
}

function LookupSection() {
  const [no, setNo] = useState('')
  const [inv, setInv] = useState<Record<string, unknown> | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function lookup() {
    if (!no.trim()) return
    setErr(null); setInv(null)
    try {
      const r = await apiGetEInvoice(no.trim())
      if (r.success && r.invoice) setInv(r.invoice)
      else setErr(r.errors?.join(', ') || '查無發票')
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '查無發票') }
  }

  return (
    <section className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-semibold mb-4">🔍 查詢發票</h2>
      <div className="flex gap-2">
        <input className="flex-1 border rounded px-2 py-1.5 text-sm font-mono"
          placeholder="輸入發票號（例：AA-12345678）"
          value={no} onChange={(e) => setNo(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && lookup()} />
        <button onClick={lookup}
          className="px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">查詢</button>
      </div>
      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mt-3 text-sm">{err}</div>}
      {inv && (
        <div className="bg-gray-50 rounded p-4 mt-3 text-sm">
          <div className="text-xs text-gray-500 mb-2">MIG 標準格式（財政部規範）:</div>
          <pre className="text-xs overflow-x-auto bg-white rounded p-2 border">{JSON.stringify(inv, null, 2)}</pre>
        </div>
      )}
    </section>
  )
}

function CancelSection() {
  const [no, setNo] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function cancel() {
    if (!no.trim() || !reason.trim()) { setErr('發票號 + 作廢原因必填'); return }
    if (!confirm(`⚠️ 確定作廢發票 ${no}？\n\n不可復原。原因會留稽核。`)) return
    setBusy(true); setErr(null); setMsg(null)
    try {
      const r = await apiCancelEInvoice(no.trim(), reason.trim())
      if (!r.success) { setErr(`作廢失敗：${r.errors?.join(', ') || ''}`); setBusy(false); return }
      setMsg(`✅ ${no} 已作廢`)
      setNo(''); setReason('')
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '作廢失敗') }
    finally { setBusy(false) }
  }

  return (
    <section className="bg-white rounded-xl shadow p-6 border-l-4 border-red-300">
      <h2 className="text-lg font-semibold mb-1 text-red-700">🚫 作廢發票</h2>
      <p className="text-sm text-gray-500 mb-4">⚠️ 不可復原。原因依稅法留稽核紀錄。</p>

      {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
      {msg && <div className="bg-green-50 text-green-700 px-3 py-2 rounded mb-3 text-sm">{msg}</div>}

      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">發票號*</label>
          <input className="w-full border rounded px-2 py-1.5 text-sm font-mono"
            value={no} onChange={(e) => setNo(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">作廢原因*</label>
          <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="例：金額有誤 / 客戶退單"
            value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
      <button onClick={cancel} disabled={busy}
        className="mt-3 px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50">
        {busy ? '作廢中…' : '🚫 確定作廢'}
      </button>
    </section>
  )
}
