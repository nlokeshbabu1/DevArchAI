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
  plan?: string  // Subscription plan: free, plus, pro, enterprise
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

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,

      // Check if token exists in localStorage
      checkAuth: () => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
        if (token) {
          set({ token, isAuthenticated: true })
          // Fetch user info when token exists
          get().fetchUserInfo()
        } else {
          set({ isLoading: false })
        }
      },

      // Fetch user info from API
      fetchUserInfo: async () => {
        const token = get().token
        if (!token) {
          set({ isLoading: false })
          return
        }

        try {
          const response = await fetch('/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          })
          
          if (response.ok) {
            const userData = await response.json()
            set({ user: userData, isAuthenticated: true })
          } else {
            // Token invalid, clear auth
            get().logout()
          }
        } catch (error) {
          console.error('Failed to fetch user info:', error)
        } finally {
          set({ isLoading: false })
        }
      },

      login: (token: string) => {
        localStorage.setItem('access_token', token)
        set({ token, isAuthenticated: true })
        // Fetch user info after login
        set({ isLoading: true })
        setTimeout(() => {
          // Use setTimeout to ensure state is updated
          useAuthStore.getState().fetchUserInfo()
        }, 0)
      },

      logout: () => {
        // Clear all storage first to prevent race conditions
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth-storage')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('current_org_id')
          sessionStorage.clear()
        }

        // Then clear state
        set({
          token: null,
          user: null,
          isAuthenticated: false,
          isLoading: false
        })

        // Force hard redirect to landing page
        window.location.replace('/')
      },

      setUser: (user: User) => {
        set({ user, isAuthenticated: true, isLoading: false })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, isAuthenticated: state.isAuthenticated, user: state.user }),
    }
  )
)
