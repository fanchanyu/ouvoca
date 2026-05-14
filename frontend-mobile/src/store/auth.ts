// 認證 store — 使用 Zustand + AsyncStorage 持久化
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import AsyncStorage from '@react-native-async-storage/async-storage'

export interface AuthUser {
  id: string
  username: string
  employee_id: string
  is_superuser: boolean
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
  logout: () => void
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
          },
        }),
    }),
    {
      name: 'llm-erp-mobile-auth',
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
)
