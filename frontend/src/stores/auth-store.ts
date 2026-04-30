import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'

interface User {
  id: string
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
  is_verified: boolean
  role: string
  current_org_id?: string
  plan?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string) => void
  logout: () => void
  setUser: (user: User) => void
  checkAuth: () => void
  fetchUserInfo: () => Promise<void>
}

const API_URL = import.meta.env.VITE_API_URL

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,

      // ✅ FIXED: no direct localStorage access
      checkAuth: () => {
        const token = get().token

        if (!token) {
          set({ isAuthenticated: false, isLoading: false })
          return
        }

        set({ isAuthenticated: true })
        get().fetchUserInfo()
      },

      // ✅ FIXED: correct API base URL
      fetchUserInfo: async () => {
        const token = get().token

        if (!token) {
          set({ isLoading: false })
          return
        }

        try {
          const response = await api.get('/auth/me', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })

          set({ user: response.data, isAuthenticated: true })
        } catch (error: any) {
          console.error('Failed to fetch user info:', error)
          if (error?.response) {
            get().logout()
          }
        } finally {
          set({ isLoading: false })
        }
      },

      // ✅ FIXED: no localStorage manual handling
      login: (token: string) => {
        set({
          token,
          isAuthenticated: true,
          isLoading: true,
        })

        setTimeout(() => {
          get().fetchUserInfo()
        }, 0)
      },

      // ✅ CLEAN logout
      logout: () => {
        set({
          token: null,
          user: null,
          isAuthenticated: false,
          isLoading: false,
        })

        window.location.replace('/')
      },

      setUser: (user: User) => {
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
