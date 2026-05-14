/**
 * Mobile API client — 共用 desktop 的 endpoints
 *
 * 設定方式 Configuration:
 *   1. 編輯 app.json 的 extra.apiBaseUrl
 *   2. 開發時可用 http://你電腦的IP:8000（手機要在同網段）
 *      例：http://192.168.1.100:8000
 */
import Constants from 'expo-constants'
import { useAuthStore } from '../store/auth'

const API_BASE: string =
  Constants.expoConfig?.extra?.apiBaseUrl || 'http://localhost:8000'

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

  const resp = await fetch(`${API_BASE}/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  let payload: unknown = null
  try {
    payload = await resp.json()
  } catch {/* ignore */}

  if (!resp.ok) {
    const msg = (payload as { detail?: string })?.detail || resp.statusText
    if (resp.status === 401) useAuthStore.getState().logout()
    throw new ApiError(resp.status, msg, payload)
  }
  return payload as T
}

export const api = {
  get: <T,>(path: string) => request<T>('GET', path),
  post: <T,>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T,>(path: string, body?: unknown) => request<T>('PUT', path, body),
  del: <T,>(path: string) => request<T>('DELETE', path),
}

export { ApiError, API_BASE }

// ───────────── Typed endpoints ─────────────

export interface HealthResponse {
  status: string
  app: string
  version: string
  db: string
  llm_provider: string
  demo_bypass: boolean
}

export const apiHealth = () => api.get<HealthResponse>('/health')

export const apiLogin = (username: string, password: string) =>
  api.post<{
    access_token: string
    user: {
      id: string
      username: string
      employee_id: string
      is_superuser: boolean
    }
  }>('/auth/login', { username, password })

export interface Part {
  id: string
  part_no: string
  name: string
  category: string
  safety_stock: number
  unit_cost: number
  is_active: boolean
}

export const apiListParts = () => api.get<Part[]>('/inventory/parts')

export const apiBelowSafety = () =>
  api.get<Array<{
    part_no: string
    name: string
    qty_available: number
    safety_stock: number
    shortage: number
  }>>('/inventory/below-safety')

export interface WorkOrder {
  id: string
  wo_no: string
  product_id: string
  status: string
  ordered_qty: number
  completed_qty: number
  priority: number
  created_at: string
}

export const apiListWOs = (status?: string) =>
  api.get<WorkOrder[]>(
    `/production/work-orders${status ? `?status=${status}` : ''}`,
  )

export const apiChat = (message: string, session_id: string) =>
  api.post<{
    reply: string
    agent: string
    session_id: string
  }>('/chat-v2', { message, session_id })
