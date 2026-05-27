import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AuthUser {
  id: string
  username: string
  employee_id: string
  is_superuser: boolean
  roles?: string[]
  /** F-7：使用者有效權限 code 清單（從 /api/permission/me/effective 載入）。 */
  permissions?: string[]
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
  setPermissions: (permissions: string[]) => void
  logout: () => void
  /** Convenience for demo / dev — sets a "demo" token recognised by backend. */
  loginAsDemo: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      setPermissions: (permissions) =>
        set((s) => (s.user ? { user: { ...s.user, permissions } } : {})),
      logout: () => set({ token: null, user: null }),
      loginAsDemo: () =>
        set({
          token: 'demo',
          user: {
            id: 'demo-admin',
            username: 'demo',
            employee_id: 'demo-admin',
            is_superuser: true,
            roles: ['admin'],
            permissions: ['*'],
          },
        }),
    }),
    { name: 'llm-erp-auth' },
  ),
)
