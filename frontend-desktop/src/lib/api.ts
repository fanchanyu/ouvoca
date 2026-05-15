/**
 * Lightweight typed API client for the LLM-ERP backend.
 * All requests inject the JWT from the Zustand auth store.
 */
import { useAuthStore } from '../store/auth'

const BASE = '/api'

class ApiError extends Error {
  status: number
  payload: unknown
  constructor(status: number, message: string, payload: unknown) {
    super(message)
    this.status = status
    this.payload = payload
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = useAuthStore.getState().token
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
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

export { ApiError }

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
}

export const apiHealth = () => api.get<HealthResponse>('/health')

export const apiLogin = (username: string, password: string) =>
  api.post<{ access_token: string; token_type: string; user: { id: string; username: string; employee_id: string; is_superuser: boolean; is_active: boolean } }>(
    '/auth/login', { username, password },
  )

export const apiChat = (message: string, session_id: string) =>
  api.post<ChatResponse>('/chat-v2', { message, session_id })

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
