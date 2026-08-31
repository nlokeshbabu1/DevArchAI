import { create } from 'zustand'
import { api } from '../lib/api'
import { setAccessToken, clearAuthMemory } from '../lib/auth-token'

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
  has_github?: boolean
  has_gitlab?: boolean
  provider?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string) => void
  logout: () => void
  setUser: (user: User) => void
  setLoading: (loading: boolean) => void
  checkAuth: () => void
  fetchUserInfo: () => Promise<void>
  refreshSession: () => Promise<boolean>
  serverLogout: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  (set, get) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,

    checkAuth: () => {
      const token = get().token

      if (token) {
        set({ isAuthenticated: true, isLoading: true })
        get().fetchUserInfo()
        return
      }

      set({ isLoading: true })
      get().refreshSession()
    },

    fetchUserInfo: async () => {
      const token = get().token

      if (!token) {
        set({ isLoading: false })
        return
      }

      try {
        const response = await api.get('/auth/me')

        const currentUser = get().user
        set({
          user: {
            ...currentUser,
            ...response.data,
            provider: response.data.provider || currentUser?.provider || 'email',
          } as User,
          isAuthenticated: true,
        })
      } catch (error: any) {
        if (error?.response) {
          get().logout()
        }
      } finally {
        set({ isLoading: false })
      }
    },

    login: (token: string) => {
      setAccessToken(token)

      set({
        token,
        isAuthenticated: true,
        isLoading: true,
      })

      setTimeout(() => {
        get().fetchUserInfo()
      }, 0)
    },

    refreshSession: async (): Promise<boolean> => {
      try {
        const response = await api.post<{ access_token: string; refresh_token?: string | null }>(
          '/auth/refresh',
          null,
          { withCredentials: true },
        )

        const { access_token: newToken } = response.data
        setAccessToken(newToken)
        set({
          token: newToken,
          isAuthenticated: true,
          isLoading: true,
        })

        await get().fetchUserInfo()
        return true
      } catch {
        clearAuthMemory()
        set({
          token: null,
          user: null,
          isAuthenticated: false,
          isLoading: false,
        })
        return false
      }
    },

    logout: () => {
      clearAuthMemory()

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

    setLoading: (loading: boolean) => {
      set({ isLoading: loading })
    },

    serverLogout: async () => {
      try {
        await api.post('/auth/logout')
      } catch {
        // Server logout may fail if token is already expired;
        // we still clear client state below.
      }
      get().logout()
    },
  }),
)
