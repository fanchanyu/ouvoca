/**
 * Lightweight typed API client for the LLM-ERP backend.
 * All requests inject the JWT from the Zustand auth store.
 */
import { useAuthStore } from '../store/auth'

const BASE = '/api'

class ApiError extends Error {
  status: number
  payload: unknown
  hint: string | null
  constructor(status: number, message: string, payload: unknown) {
    super(message)
    this.status = status
    this.payload = payload
    // v3.35：從 backend 取友善 hint（中文化錯誤訊息）
    this.hint = (payload as { hint?: string | null })?.hint || null
  }
  /** 友善訊息：優先用 backend hint，再 fallback 到 status code 中文對照 */
  friendly(): string {
    if (this.hint) return this.hint
    const map: Record<number, string> = {
      400: '請求格式有誤，請檢查輸入內容',
      401: '尚未登入或登入過期，請重新登入',
      403: '您沒有此功能的權限，請洽公司管理員 / 老闆',
      404: '找不到您要的資料',
      409: '資料衝突（可能重複或被他人修改）',
      422: '資料格式不正確',
      429: '操作太頻繁，請稍候再試',
      500: '系統忙線中，請稍候再試；若持續發生請洽 IT',
      503: '服務維護中',
      504: '回應逾時，請稍候再試',
    }
    return map[this.status] || this.message
  }
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const token = useAuthStore.getState().token
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })

  let payload: unknown = null
  try { payload = await resp.json() } catch { /* ignore */ }

  if (!resp.ok) {
    const msg = (payload as { detail?: string })?.detail || resp.statusText
    if (resp.status === 401) useAuthStore.getState().logout()
    throw new ApiError(resp.status, msg, payload)
  }
  return payload as T
}

export const api = {
  get:    <T>(path: string) => request<T>('GET', path),
  post:   <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put:    <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch:  <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del:    <T>(path: string) => request<T>('DELETE', path),
}

/** Upload a file via multipart/form-data. Returns the created Attachment record. */
async function uploadFile<T>(path: string, file: File, extra?: Record<string, string>): Promise<T> {
  const token = useAuthStore.getState().token
  const fd = new FormData()
  fd.append('file', file)
  if (extra) for (const [k, v] of Object.entries(extra)) fd.append(k, v)
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(BASE + path, { method: 'POST', headers, body: fd })
  let payload: unknown = null
  try { payload = await resp.json() } catch { /* ignore */ }
  if (!resp.ok) {
    const msg = (payload as { detail?: string })?.detail || resp.statusText
    if (resp.status === 401) useAuthStore.getState().logout()
    throw new ApiError(resp.status, msg, payload)
  }
  return payload as T
}

export { ApiError, uploadFile }

// ──────────────────────────────────────────────────────────
// Attachments / File upload (Sprint E v3.13)
// ──────────────────────────────────────────────────────────
export interface Attachment {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  category: string         // 'quote' | 'invoice' | 'po' | 'general'
  description: string | null
  uploaded_by: string | null
  uploaded_at: string
}
export const apiUploadAttachment = (file: File, category: string = 'general', description?: string) =>
  uploadFile<Attachment>('/files/upload', file, { category, ...(description ? { description } : {}) })
export const apiListAttachments  = (category?: string) =>
  api.get<Attachment[]>(`/files${category ? `?category=${encodeURIComponent(category)}` : ''}`)
export const apiDeleteAttachment = (id: string) =>
  api.del<{ deleted: boolean; id: string }>(`/files/${id}`)
export const downloadAttachmentUrl = (id: string) => `/api/files/${id}/download`

// ──────────────────────────────────────────────────────────
// LLM Status / Configuration (Sprint H v3.14)
// ──────────────────────────────────────────────────────────
export interface LlmStatus {
  configured: boolean
  provider: 'deepseek' | 'openai' | 'anthropic' | 'ollama'
  model: string
  base_url: string
  verify_ssl: boolean
  last_test_success: boolean | null
  last_test_error: string | null
  setup_url: string
}
export interface LlmTestRequest {
  provider: 'deepseek' | 'openai' | 'anthropic' | 'ollama'
  api_key: string
  base_url?: string
  verify_ssl?: boolean
}
export interface LlmTestResponse {
  success: boolean
  message: string
  detail?: string
  response_ms?: number
}
export interface LlmConfigureRequest {
  provider: 'deepseek' | 'openai' | 'anthropic' | 'ollama'
  api_key: string
  base_url?: string
  model?: string
  verify_ssl?: boolean
}
export const apiLlmStatus    = () => api.get<LlmStatus>('/llm/status')
export const apiLlmTest      = (body: LlmTestRequest) => api.post<LlmTestResponse>('/llm/test', body)
export const apiLlmConfigure = (body: LlmConfigureRequest) =>
  api.post<{ saved: boolean; requires_restart: boolean; message: string }>('/llm/configure', body)

// ──────────────────────────────────────────────────────────
// CRM (Sprint I v3.15) — Lead / Opportunity / Activity
// ──────────────────────────────────────────────────────────
export interface Lead {
  id: string
  company_name: string
  contact_person: string | null
  status: string                  // 'new' | 'contacted' | 'qualified' | 'lost' | 'converted'
  converted_to_customer_id: string | null
  created_at: string
}
export interface Opportunity {
  id: string
  customer_id: string
  name: string
  stage: string                   // 'prospect' | 'proposal' | 'negotiation' | 'won' | 'lost'
  amount: number
  probability: number
  status: string                  // 'open' | 'closed'
}
export interface CrmEvent {
  id: string
  customer_id: string
  event_type: string              // 'call' | 'email' | 'meeting' | 'note' | 'task'
  subject: string
  description: string | null
  created_at: string
}

export const apiListLeads     = (status?: string) =>
  api.get<Lead[]>(`/crm/leads${status ? `?status=${status}` : ''}`)
export const apiCreateLead    = (data: { company_name: string; contact_person?: string; contact_email?: string; contact_phone?: string; source?: string }) =>
  api.post<Lead>('/crm/leads', data)
export const apiConvertLead   = (lead_id: string, customer: { code: string; name: string }) =>
  api.post<Customer>(`/crm/leads/${lead_id}/convert`, { customer })

export const apiListOpps      = (stage?: string) =>
  api.get<Opportunity[]>(`/crm/opportunities${stage ? `?stage=${stage}` : ''}`)
export const apiCreateOpp     = (data: { customer_id: string; name: string; stage?: string; amount?: number; probability?: number; expected_close_date?: string }) =>
  api.post<Opportunity>('/crm/opportunities', data)
export const apiUpdateOppStage = (opp_id: string, stage: string) =>
  api.post<Opportunity>(`/crm/opportunities/${opp_id}/stage`, { stage })

export const apiListCrmEvents = (customer_id?: string, limit = 50) =>
  api.get<CrmEvent[]>(`/crm/events?${customer_id ? `customer_id=${customer_id}&` : ''}limit=${limit}`)
export const apiCreateCrmEvent = (data: { customer_id: string; event_type: string; subject: string; description?: string }) =>
  api.post<CrmEvent>('/crm/events', data)

// ──────────────────────────────────────────────────────────
// Create helpers for primary entities (Sprint K v3.17)
// 補上 Sales/Purchase/Production 主實體建單能力（小白不必靠 AI 也能建）
// ──────────────────────────────────────────────────────────
export interface Product {
  id: string; product_no: string; name: string; bom_version?: string
  is_active: boolean
}

// Sales
export const apiCreateCustomer = (data: { code: string; name: string; grade?: string; contact_person?: string; contact_phone?: string; payment_terms?: string; credit_limit?: number }) =>
  api.post<Customer>('/sales/customers', data)

export interface SalesOrderItemInput {
  product_id: string
  ordered_qty: number
  unit_price: number
}
export const apiCreateSO = (data: { customer_id: string; items: SalesOrderItemInput[]; due_date?: string; notes?: string }) =>
  api.post<SalesOrder>('/sales/orders', data)

// Purchase
export const apiCreateSupplier = (data: { code: string; name: string; tier?: string; lead_time_days?: number; is_approved?: boolean }) =>
  api.post<Supplier>('/purchase/suppliers', data)

export interface PurchaseOrderItemInput {
  part_id: string
  ordered_qty: number
  unit_price: number   // backend uses unit_price (not unit_cost) for PO line items
}
export const apiCreatePO = (data: { supplier_id: string; items: PurchaseOrderItemInput[]; expected_date?: string }) =>
  api.post<PurchaseOrder>('/purchase/orders', data)

// Production
export const apiListProducts = () => api.get<Product[]>('/production/products')
export const apiCreateProduct = (data: { product_no: string; name: string }) =>
  api.post<Product>('/production/products', data)
export const apiCreateWO = (data: { product_id: string; ordered_qty: number; priority?: number; due_date?: string; so_id?: string }) =>
  api.post<ProductionOrder>('/production/work-orders', data)

// ──────────────────────────────────────────────────────────
// 進貨 / 出貨 / 票據 / 會計 (Sprint L v3.18)
// ──────────────────────────────────────────────────────────

// 取得 PO 含 line items（後端應該回 items 陣列）
export interface POItem {
  id: string; po_id: string; line_no: number
  part_id: string; ordered_qty: number; received_qty: number
  unit_price: number; line_total: number
}
export interface PurchaseOrderDetail extends PurchaseOrder {
  items?: POItem[]
}
export const apiGetPO = (po_id: string) => api.get<PurchaseOrderDetail>(`/purchase/orders/${po_id}`)

// 進貨 (Goods Receipt)
export const apiReceivePO = (po_id: string, receipts: Array<{ item_id: string; received_qty: number }>) =>
  api.post<PurchaseOrder>(`/purchase/orders/${po_id}/receive`, { receipts })

// 出貨 (Shipping)
export const apiShipSO = (so_id: string) =>
  api.post<SalesOrder>(`/sales/orders/${so_id}/ship`)

export const apiConfirmSO = (so_id: string) =>
  api.post<SalesOrder>(`/sales/orders/${so_id}/confirm`)

// PO approve（草稿 → 已核准）
export const apiApprovePO = (po_id: string) =>
  api.post<PurchaseOrder>(`/purchase/orders/${po_id}/approve`)

// ─── 會計 ────────────────────────────────────────────
export interface Account {
  id: string; code: string; name: string; account_type: string
  is_debit_normal: boolean; is_active: boolean
}
export interface JournalLine {
  id: string; account_id: string; line_no: number
  debit: number; credit: number; description?: string | null
}
export interface JournalEntry {
  id: string; entry_no: string; entry_date: string
  period?: string | null; status: string
  description?: string | null
  lines?: JournalLine[]
}
export interface JournalLineInput {
  account_id: string; debit: number; credit: number; description?: string
}

export const apiListAccounts = () => api.get<Account[]>('/accounting/accounts')
export const apiCreateAccount = (data: { code: string; name: string; account_type: string; is_debit_normal?: boolean }) =>
  api.post<Account>('/accounting/accounts', data)

export const apiListJournals = (limit = 100) =>
  api.get<JournalEntry[]>(`/accounting/journals?limit=${limit}`)
export const apiCreateJournal = (data: { description: string; lines: JournalLineInput[]; entry_date?: string; period?: string; source_type?: string }) =>
  api.post<JournalEntry>('/accounting/journals', data)
export const apiPostJournal = (entry_id: string) =>
  api.post<JournalEntry>(`/accounting/journals/${entry_id}/post`)

// ─── 應收帳款 (AR) ───────────────────────────────────
export interface AccountsReceivable {
  id: string; customer_id: string
  invoice_no: string; invoice_date: string; due_date: string
  amount: number; paid_amount: number
  status: string  // 'open' | 'partial' | 'paid' | 'overdue'
  aging_days: number
}
export const apiListAR = () => api.get<AccountsReceivable[]>('/accounting/receivables')
export const apiCreateAR = (data: { customer_id: string; invoice_no: string; invoice_date: string; due_date: string; amount: number }) =>
  api.post<AccountsReceivable>('/accounting/receivables', data)

// ─── 電子發票 e-invoice（台灣合規）─────────────────────
// 對齊 backend app/api/tax_tw.py EInvoiceCreateRequest schema
export interface EInvoiceLineItem {
  description: string
  qty: number
  unit_price: number
}
export interface EInvoiceIssueRequest {
  invoice_no: string         // 例 AA-12345678
  seller_tax_id: string      // 我方統編
  seller_name: string        // 我方公司名
  buyer_tax_id?: string
  buyer_name?: string
  items: EInvoiceLineItem[]
}
export interface EInvoice {
  invoice_no: string
  invoice_date?: string; invoice_time?: string
  seller_tax_id: string; seller_name: string
  buyer_tax_id?: string; buyer_name?: string
  sales_amount: number; tax: number; total: number
  status: string
}
// Backend 回 {success, tracking_no, errors, mig_payload}
export const apiIssueEInvoice = (data: EInvoiceIssueRequest) =>
  api.post<{ success: boolean; tracking_no?: string; errors?: string[]; mig_payload?: Record<string, unknown> }>('/tax/tw/einvoice/issue', data)
// Cancel 用 query param ?reason=...
export const apiCancelEInvoice = (invoice_no: string, reason: string) =>
  api.post<{ success: boolean; errors?: string[] }>(`/tax/tw/einvoice/cancel/${invoice_no}?reason=${encodeURIComponent(reason)}`)
// Query 回 {success, invoice: {...MIG dict}}
export const apiGetEInvoice = (invoice_no: string) =>
  api.get<{ success: boolean; invoice?: Record<string, unknown>; errors?: string[] }>(`/tax/tw/einvoice/${invoice_no}`)
// v3.20: 多國統編驗證
export interface TaxIdValidationResult {
  tax_id: string
  country: string             // 'TW' / 'CN' / 'US' / 'JP' / 'EU-DE' / 'GENERIC' / ...
  valid: boolean
  message: string
  formatted: string
  supported_countries?: Array<{ code: string; name: string }>
}
export const apiValidateTaxId = (tax_id: string, country = 'TW') =>
  api.get<TaxIdValidationResult>(`/tax/tw/validate-tax-id/${encodeURIComponent(tax_id)}?country=${country}`)

export const apiListTaxIdCountries = () =>
  api.get<{ countries: Array<{ code: string; name: string }> }>('/tax/tw/validate-tax-id-countries')

// ─── WO release / complete（Production 補齊操作鏈）─────
export const apiReleaseWOById = (wo_id: string) =>
  api.post<ProductionOrder>(`/production/work-orders/${wo_id}/release`)
export const apiCompleteWO = (wo_id: string, data: { completed_qty: number; rejected_qty?: number }) =>
  api.post<ProductionOrder>(`/production/work-orders/${wo_id}/complete`, data)

// ─── 庫存交易（inbound/outbound 記錄）───────────────────
export interface InventoryTransaction {
  id: string; part_id: string; transaction_type: string
  qty: number; reference_type?: string | null; reference_id?: string | null
  created_at: string
}
export const apiListInventoryTxns = (part_id?: string, limit = 100) =>
  api.get<InventoryTransaction[]>(`/inventory/transactions?${part_id ? `part_id=${part_id}&` : ''}limit=${limit}`)

// ─── BOM 物料表 (v3.23 Sprint Q) ───────────────────────
export interface BOMItem {
  id: string
  product_id: string
  component_part_id: string
  qty_per: number
  unit?: string | null
  scrap_rate?: number
  remark?: string | null
}
export const apiListBOM = (product_id: string) =>
  api.get<BOMItem[]>(`/production/bom/${product_id}`)
export const apiCreateBOMItem = (data: { product_id: string; component_part_id: string; qty_per: number; unit?: string; scrap_rate?: number }) =>
  api.post<BOMItem>('/production/bom-items', data)

// ─── 報表 URL 直接下載 ──────────────────────────────────
export const reportUrlAR = (overdueOnly = false) =>
  `/api/reports/ar-aging.xlsx?overdue_only=${overdueOnly}`
export const reportUrlInventoryMonthly = (yyyymm: string) =>
  `/api/reports/inventory-monthly.xlsx?period=${yyyymm}`
export const reportUrlTax401 = (year: number, periodNo: number, companyName = '') =>
  `/api/reports/tax-401.html?year=${year}&period_no=${periodNo}&company_name=${encodeURIComponent(companyName)}`

// ─── Analytics KPI（給報表 dashboard 用）────────────────
// Backend returns: { metric, value, generated_at, breakdown, interpretation, status }
export interface KpiResult {
  metric: string
  value: number
  generated_at: string
  breakdown?: Record<string, unknown>
  interpretation?: string
  status?: string
}
export const apiAnalyticsDSO = () => api.get<KpiResult>('/analytics/dso')
export const apiAnalyticsInventoryTurn = () => api.get<KpiResult>('/analytics/inventory-turn')
export const apiAnalyticsGrossMargin = () => api.get<KpiResult>('/analytics/gross-margin')
export const apiAnalyticsSummary = () => api.get<Record<string, unknown>>('/analytics/summary')

// ---------- domain typed helpers ----------

export interface Part {
  id: string; part_no: string; name: string; category: string; unit: string
  min_stock: number; max_stock: number; safety_stock: number
  lead_time_days: number; unit_cost: number; is_active: boolean; is_critical: boolean
}

export interface Supplier {
  id: string; code: string; name: string; tier: string; is_approved: boolean; is_active: boolean
}

export interface PurchaseOrder {
  id: string; po_no: string; supplier_id: string; status: string
  total_amount: number; order_date: string
  supplier?: Supplier | null
}

export interface ProductionOrder {
  id: string; wo_no: string; product_id: string; so_id?: string | null
  ordered_qty: number; completed_qty: number; rejected_qty: number
  status: string; priority: number; created_at: string
}

export interface SalesOrder {
  id: string; so_no: string; customer_id: string; status: string
  total_amount: number; order_date: string; payment_status: string
  customer?: { id: string; name: string } | null
}

export interface HealthResponse {
  status: string; app: string; version: string; db: string
  llm_provider: string; demo_bypass: boolean
}

export interface ChatResponse {
  reply: string; agent: string; session_id: string
  tool_calls?: Array<{ tool: string; args: unknown; result: string }>
  // v3.14：當 LLM_API_KEY 未設或失效時，前端依此 flag render 申請引導卡
  setup_required?: boolean
  setup_reason?: 'no_api_key' | 'invalid_key' | 'quota_exceeded'
}

export const apiHealth = () => api.get<HealthResponse>('/health')

export const apiLogin = (username: string, password: string) =>
  api.post<{ access_token: string; token_type: string; user: { id: string; username: string; employee_id: string; is_superuser: boolean; is_active: boolean } }>(
    '/auth/login', { username, password },
  )

// v3.38 N8：第三個 arg = AbortSignal（讓使用者可取消）
export const apiChat = (message: string, session_id: string, signal?: AbortSignal) =>
  request<ChatResponse>('POST', '/chat-v2', { message, session_id }, signal)

// ============================================================
// ConfirmCard (對話式 hard-write 確認卡，v3.1)
// ============================================================

export interface ConfirmCardData {
  id: string
  tool_name: string
  title: string
  summary: string[]
  slots_preview?: Record<string, unknown>
  risk_tier: 'read' | 'soft-write' | 'hard-write'
  created_at: string
  expires_at: string
  ttl_seconds: number
}

export interface ConfirmCardPayload {
  type: 'confirm_card'
  card: ConfirmCardData
}

export interface ConfirmCardResult {
  status: 'executed'
  card_id: string
  tool_name: string
  title: string
  result: Record<string, unknown> | string
}

export const apiConfirmCard = (cardId: string) =>
  api.post<ConfirmCardResult>(`/agents/confirm/${cardId}`)

export const apiCancelCard = (cardId: string) =>
  api.post<{ status: 'cancelled'; card_id: string }>(`/agents/cancel/${cardId}`)

export const apiGetCard = (cardId: string) =>
  api.get<ConfirmCardData>(`/agents/confirm/${cardId}`)

export const apiPendingCards = () =>
  api.get<{ total: number; cards: ConfirmCardData[] }>('/agents/pending')

// ============================================================
// Agent exec (v3.10 Track B — UI 直接呼 hard-write tool)
// ============================================================

export const apiExecTool = <TArgs extends Record<string, unknown>>(
  toolName: string,
  args: TArgs,
) => api.post<ConfirmCardPayload | { error: string } | Record<string, unknown>>(
  `/agents/exec/${toolName}`,
  args,
)

// ============================================================
// Onboarding (v3.10 Track D)
// ============================================================

export interface OnboardingStatus {
  has_demo_data: boolean
  demo_customers: number
  demo_suppliers: number
  demo_parts: number
  total_customers: number
  total_suppliers: number
  total_parts: number
}

export const apiOnboardingStatus = () =>
  api.get<OnboardingStatus>('/onboarding/status')

export const apiSeedDemo = () =>
  api.post<{
    inserted_customers: number
    inserted_suppliers: number
    inserted_parts: number
    skipped: number
    message: string
  }>('/onboarding/seed-demo')

// Sprint F (v3.13)：清除所有 DEMO- 前綴資料
export const apiClearDemo = () =>
  api.del<{
    deleted_customers: number
    deleted_suppliers: number
    deleted_parts: number
    deleted_inventory_rows: number
    message: string
  }>('/onboarding/clear-demo')

// ============================================================
// Reports (v3.10 Track C — 直接拿 URL 給 <a download>)
// ============================================================

export const reportUrls = {
  tax401Html: (year: number, periodNo: number, companyName = '') =>
    `/api/reports/tax-401.html?year=${year}&period_no=${periodNo}&company_name=${encodeURIComponent(companyName)}`,
  arAgingXlsx: (overdueOnly = false) =>
    `/api/reports/ar-aging.xlsx?overdue_only=${overdueOnly}`,
  inventoryMonthlyXlsx: (periodLabel = '', onlyLow = false) =>
    `/api/reports/inventory-monthly.xlsx?period_label=${encodeURIComponent(periodLabel)}&only_low=${onlyLow}`,
}

// ============================================================
// CRUD update/delete (v3.10 — fix「可以新增但不能修改和刪除」root cause)
// ============================================================

// Part
export const apiUpdatePart = (partId: string, data: Partial<Part>) =>
  api.patch<Part>(`/inventory/parts/${partId}`, data)
export const apiDeletePart = (partId: string) =>
  api.del<{ deleted: boolean; part_id: string; part_no: string }>(`/inventory/parts/${partId}`)

// Supplier
export const apiUpdateSupplier = (id: string, data: Partial<Supplier>) =>
  api.patch<Supplier>(`/purchase/suppliers/${id}`, data)
export const apiDeleteSupplier = (id: string) =>
  api.del<{ deleted: boolean; supplier_id: string; code: string }>(`/purchase/suppliers/${id}`)

// Customer
export interface Customer {
  id: string; code: string; name: string; grade: string
  credit_limit: number; is_active: boolean
  contact_person?: string | null; contact_phone?: string | null
}
export const apiUpdateCustomer = (id: string, data: Partial<Customer>) =>
  api.patch<Customer>(`/sales/customers/${id}`, data)
export const apiDeleteCustomer = (id: string) =>
  api.del<{ deleted: boolean; customer_id: string; code: string }>(`/sales/customers/${id}`)

// Cancel orders
export const apiCancelPO = (id: string, reason = '') =>
  api.post<PurchaseOrder>(`/purchase/orders/${id}/cancel`, { reason })
export const apiCancelSO = (id: string, reason = '') =>
  api.post<SalesOrder>(`/sales/orders/${id}/cancel`, { reason })
export const apiCancelWO = (id: string, reason = '') =>
  api.post<ProductionOrder>(`/production/work-orders/${id}/cancel`, { reason })

export const apiListParts = () => api.get<Part[]>('/inventory/parts')
export const apiCreatePart = (data: Partial<Part>) => api.post<Part>('/inventory/parts', data)
export const apiBelowSafety = () => api.get<Array<{ part_no: string; name: string; qty_available: number; safety_stock: number; shortage: number }>>('/inventory/below-safety')

export const apiListSuppliers = () => api.get<Supplier[]>('/purchase/suppliers')
export const apiListPOs = (status?: string) =>
  api.get<PurchaseOrder[]>(`/purchase/orders${status ? `?status=${status}` : ''}`)

export const apiListWOs = (status?: string) =>
  api.get<ProductionOrder[]>(`/production/work-orders${status ? `?status=${status}` : ''}`)
export const apiReleaseWO = (id: string) =>
  api.post<ProductionOrder>(`/production/work-orders/${id}/release`)

export const apiListSOs = (status?: string) =>
  api.get<SalesOrder[]>(`/sales/orders${status ? `?status=${status}` : ''}`)

export const apiListCustomers = () =>
  api.get<Array<{ id: string; code: string; name: string; grade: string; credit_limit: number; is_active: boolean }>>('/sales/customers')

export const apiListInspections = () =>
  api.get<Array<{ id: string; inspection_no: string; part_id: string; accepted_qty: number; rejected_qty: number; status: string }>>('/quality/inspections')

export const apiListNCs = () =>
  api.get<Array<{ id: string; nc_no: string; severity: string; description: string; qty_affected: number }>>('/quality/non-conformances')

export const apiRecentEvents = (limit = 50) =>
  api.get<Array<{ name: string; domain: string; entity_type: string; entity_id: string; data: Record<string, unknown>; created_at: string }>>(`/events/recent?limit=${limit}`)

// ============================================================
// Permission / RBAC
// ============================================================

export interface PermissionDef {
  id: string
  code: string
  resource: string
  action: string
  module: string
  name_zh: string | null
  description: string | null
  is_sensitive: boolean
  risk_level: 'low' | 'medium' | 'high' | 'critical'
}

export interface RolePermissionItem {
  code: string
  name_zh: string | null
  scope: string
}

export interface RoleV2 {
  id: string
  tenant_id: string | null
  code: string
  name_zh: string
  description: string | null
  is_system: boolean
  is_active: boolean
  priority: number
  icon: string | null
  color: string | null
  permissions: RolePermissionItem[]
  created_at: string
}

export interface UserRoleAssignment {
  id: string
  user_id: string
  role_id: string
  tenant_id: string
  granted_at: string
  granted_by: string | null
  expires_at: string | null
  delegation_from: string | null
  reason: string | null
  is_active: boolean
}

export interface PermissionOverride {
  id: string
  user_id: string
  permission_code: string
  grant_or_revoke: 'grant' | 'revoke'
  reason: string
  expires_at: string | null
  granted_at: string
  is_active: boolean
}

export interface EffectivePermissions {
  user_id: string
  roles: Array<{ role_code?: string; role_name?: string; tenant_id: string; expires_at?: string; is_delegation?: boolean }>
  permissions: Array<{ code: string; scope: string }>
  overrides: Array<{ code: string; type: string; reason: string; expires_at?: string }>
}

export const apiListPermissions = (module?: string) =>
  api.get<PermissionDef[]>(`/permission/permissions${module ? `?module=${module}` : ''}`)

export const apiListRoles = () => api.get<RoleV2[]>('/permission/roles')

export const apiGetRole = (id: string) => api.get<RoleV2>(`/permission/roles/${id}`)

export const apiCreateRole = (data: { tenant_id?: string; code: string; name_zh: string;
  description?: string; priority?: number; icon?: string; color?: string;
  permissions: Array<{ code: string; scope: string }> }) =>
  api.post<RoleV2>('/permission/roles', data)

export const apiCloneRole = (id: string, data: { new_code: string; new_name_zh: string; tenant_id?: string }) =>
  api.post<RoleV2>(`/permission/roles/${id}/clone`, data)

export const apiUpdateRolePermissions = (id: string, permissions: Array<{ code: string; scope: string }>) =>
  api.put<RoleV2>(`/permission/roles/${id}/permissions`, { permissions })

export const apiAssignRole = (data: { user_id: string; role_id: string; tenant_id: string;
  expires_at?: string; reason?: string; delegation_from?: string }) =>
  api.post<UserRoleAssignment>('/permission/assignments', data)

export const apiRevokeRole = (assignmentId: string) =>
  api.del<UserRoleAssignment>(`/permission/assignments/${assignmentId}`)

export const apiUserRoles = (userId: string) =>
  api.get<UserRoleAssignment[]>(`/permission/users/${userId}/roles`)

export const apiGrantOverride = (data: { user_id: string; permission_code: string;
  grant_or_revoke: 'grant' | 'revoke'; reason: string; expires_at?: string }) =>
  api.post<PermissionOverride>('/permission/overrides', data)

export const apiUserOverrides = (userId: string) =>
  api.get<PermissionOverride[]>(`/permission/users/${userId}/overrides`)

export const apiUserEffective = (userId: string) =>
  api.get<EffectivePermissions>(`/permission/users/${userId}/effective`)

export const apiMyEffective = () =>
  api.get<EffectivePermissions>('/permission/me/effective')

// ──────────────────────────────────────────────────────────
// Approval Workflow (v3.22 — 多階審批工作流)
// ──────────────────────────────────────────────────────────
export interface ApprovalRule {
  id: string
  name: string
  trigger_type: 'po' | 'so' | 'payment'
  condition_field: 'amount' | 'discount_pct'
  condition_op: 'gt' | 'gte' | 'lt' | 'lte' | 'eq'
  condition_value: number
  approver_role: string
  stages: number
  is_active: boolean
  created_at: string
}

export interface ApprovalStep {
  id: string
  stage: number
  approver_id: string | null
  approver_username: string | null
  action: 'approved' | 'rejected'
  comment: string | null
  decided_at: string
}

export interface ApprovalRequest {
  id: string
  rule_id: string
  trigger_type: 'po' | 'so' | 'payment'
  trigger_id: string
  trigger_summary: string
  requested_by: string | null
  approver_role: string
  current_stage: number
  total_stages: number
  status: 'pending' | 'approved' | 'rejected' | 'cancelled'
  created_at: string
  updated_at: string
  steps: ApprovalStep[]
}

export const apiListRules = (params?: { trigger_type?: string; active_only?: boolean }) => {
  const q = new URLSearchParams()
  if (params?.trigger_type) q.set('trigger_type', params.trigger_type)
  if (params?.active_only) q.set('active_only', 'true')
  const qs = q.toString()
  return api.get<ApprovalRule[]>(`/approvals/rules${qs ? `?${qs}` : ''}`)
}

export const apiCreateRule = (data: {
  name: string
  trigger_type: 'po' | 'so' | 'payment'
  condition_field: 'amount' | 'discount_pct'
  condition_op?: 'gt' | 'gte' | 'lt' | 'lte' | 'eq'
  condition_value: number
  approver_role: string
  stages?: number
  is_active?: boolean
}) => api.post<ApprovalRule>('/approvals/rules', data)

export const apiDeleteRule = (rule_id: string) =>
  api.del<{ deleted: boolean; rule_id: string }>(`/approvals/rules/${rule_id}`)

export const apiListPendingApprovals = (approver_role?: string) => {
  const qs = approver_role ? `?approver_role=${encodeURIComponent(approver_role)}` : ''
  return api.get<ApprovalRequest[]>(`/approvals/pending${qs}`)
}

export const apiListApprovalHistory = (params?: { status?: string; trigger_type?: string; limit?: number }) => {
  const q = new URLSearchParams()
  if (params?.status) q.set('status', params.status)
  if (params?.trigger_type) q.set('trigger_type', params.trigger_type)
  if (params?.limit) q.set('limit', String(params.limit))
  const qs = q.toString()
  return api.get<ApprovalRequest[]>(`/approvals/history${qs ? `?${qs}` : ''}`)
}

export const apiApprove = (request_id: string, comment?: string) =>
  api.post<ApprovalRequest>(`/approvals/${request_id}/approve`, { comment: comment ?? '' })

export const apiReject = (request_id: string, comment: string) =>
  api.post<ApprovalRequest>(`/approvals/${request_id}/reject`, { comment })
