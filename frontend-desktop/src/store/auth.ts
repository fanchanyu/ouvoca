import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AuthUser {
  id: string
  username: string
  employee_id: string
  is_superuser: boolean
  roles?: string[]
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
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
          },
        }),
    }),
    { name: 'llm-erp-auth' },
  ),
)
