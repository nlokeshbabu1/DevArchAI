/**
 * Authentication store using Zustand
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,

      // Check if token exists in localStorage
      checkAuth: () => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
        if (token) {
          set({ token, isAuthenticated: true })
        }
        set({ isLoading: false })
      },

      login: (token: string) => {
        localStorage.setItem('access_token', token)
        set({ token, isAuthenticated: true })
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('current_org_id')
        set({ token: null, user: null, isAuthenticated: false })
      },

      setUser: (user: User) => {
        set({ user, isAuthenticated: true })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
)
