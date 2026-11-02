import { create } from 'zustand'
import { api } from '../lib/api'
import { clearAuthMemory, performRefresh, setAccessToken } from '../lib/auth-token'
import { broadcastAuthEvent, subscribeAuthSync, type AuthSyncMessage } from '../lib/auth-sync'
import { clearUserQueryCache } from '../lib/query-client'

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
  sessionChecked: boolean
  logoutInProgress: boolean
  login: (token: string) => void
  logout: (options?: { redirectTo?: string; broadcast?: boolean }) => void
  setUser: (user: User) => void
  setLoading: (loading: boolean) => void
  checkAuth: () => void
  fetchUserInfo: () => Promise<void>
  refreshSession: (options?: { silent?: boolean }) => Promise<boolean>
  serverLogout: () => Promise<void>
}

let syncInitialized = false
let refreshSessionInFlight: Promise<boolean> | null = null
let checkAuthInFlight = false

function handleAuthSyncMessage(message: AuthSyncMessage): void {
  const store = useAuthStore.getState()
  switch (message.type) {
    case 'AUTH_LOGIN':
    case 'AUTH_REFRESH_COMPLETE':
    case 'AUTH_REFRESH_REQUIRED':
      void store.refreshSession({ silent: true })
      break
    case 'AUTH_LOGOUT':
    case 'AUTH_SESSION_REVOKED':
      store.logout({ redirectTo: '/login', broadcast: false })
      break
    default:
      break
  }
}

export function initAuthSync(): void {
  if (syncInitialized || typeof window === 'undefined') {
    return
  }
  syncInitialized = true
  subscribeAuthSync(handleAuthSyncMessage)
}

export const useAuthStore = create<AuthState>()(
  (set, get) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
    sessionChecked: false,
    logoutInProgress: false,

    checkAuth: () => {
      if (checkAuthInFlight) {
        return
      }
      checkAuthInFlight = true

      const token = get().token

      if (token) {
        set({ isAuthenticated: true, isLoading: true })
        void get()
          .fetchUserInfo()
          .finally(() => {
            checkAuthInFlight = false
            set({ sessionChecked: true })
          })
        return
      }

      set({ isLoading: true })
      void get()
        .refreshSession()
        .finally(() => {
          checkAuthInFlight = false
          set({ sessionChecked: true })
        })
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
        if (error?.response?.status === 401) {
          const restored = await get().refreshSession({ silent: true })
          if (!restored) {
            get().logout({ redirectTo: '/login', broadcast: false })
          }
        } else if (error?.response) {
          get().logout({ redirectTo: '/login', broadcast: false })
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

      broadcastAuthEvent({ type: 'AUTH_LOGIN' })

      setTimeout(() => {
        void get().fetchUserInfo()
      }, 0)
    },

    refreshSession: async (options?: { silent?: boolean }): Promise<boolean> => {
      if (refreshSessionInFlight) {
        return refreshSessionInFlight
      }

      refreshSessionInFlight = (async () => {
        if (!options?.silent) {
          set({ isLoading: true })
        }
        try {
          const newToken = await performRefresh()

          set({
            token: newToken,
            isAuthenticated: true,
            isLoading: true,
          })

          await get().fetchUserInfo()
          return true
        } catch {
          clearAuthMemory()
          clearUserQueryCache()
          set({
            token: null,
            user: null,
            isAuthenticated: false,
            isLoading: false,
            sessionChecked: true,
          })
          return false
        } finally {
          refreshSessionInFlight = null
        }
      })()

      return refreshSessionInFlight
    },

    logout: (options?: { redirectTo?: string; broadcast?: boolean }) => {
      clearAuthMemory()
      clearUserQueryCache()

      set({
        token: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        sessionChecked: true,
        logoutInProgress: false,
      })

      if (options?.broadcast !== false) {
        broadcastAuthEvent({ type: 'AUTH_LOGOUT' })
      }

      const target = options?.redirectTo ?? '/'
      if (typeof window !== 'undefined') {
        window.location.replace(target)
      }
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
      if (get().logoutInProgress) {
        return
      }
      set({ logoutInProgress: true })
      try {
        await api.post('/auth/logout')
      } catch {
        // Still clear client state; cookie may already be cleared server-side.
      }
      get().logout({ redirectTo: '/login', broadcast: true })
    },
  }),
)
