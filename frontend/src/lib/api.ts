import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { getAccessToken, setAccessToken, clearAuthMemory } from './auth-token'

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
}

interface RefreshTokenResponse {
  access_token: string
  refresh_token?: string | null
}

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/$/, '')
}

function getFallbackBaseUrl(): string {
  return typeof window !== 'undefined' ? window.location.origin : ''
}

function getConfiguredBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
  return normalizeBaseUrl(configuredBaseUrl || getFallbackBaseUrl())
}

function redirectToLogin() {
  if (typeof window === 'undefined') {
    return
  }

  window.location.href = '/login'
}

// ---------------------------------------------------------------------------
// Refresh-lock: only ONE refresh request at a time.  All concurrent callers
// that hit a 401 wait on the same Promise so they all get the new token.
// ---------------------------------------------------------------------------
let refreshPromise: Promise<string> | null = null

function doRefresh(originalRequest: InternalAxiosRequestConfig): Promise<string> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const refreshResponse = await axios.post<RefreshTokenResponse>(
        `${API_V1_BASE_URL}/auth/refresh`,
        null,
        { withCredentials: true },
      )

      const { access_token } = refreshResponse.data
      setAccessToken(access_token)
      return access_token
    } catch (err) {
      clearAuthMemory()
      redirectToLogin()
      throw err
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export const API_BASE_URL = getConfiguredBaseUrl()
export const API_V1_BASE_URL = API_BASE_URL ? `${API_BASE_URL}/api/v1` : '/api/v1'

export function buildBackendUrl(path: string): string {
  const baseUrl = API_BASE_URL || getFallbackBaseUrl()
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return new URL(normalizedPath, baseUrl).toString()
}

export const api = axios.create({
  baseURL: API_V1_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
  withCredentials: true,
})

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken()

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined

    if (!originalRequest) {
      return Promise.reject(error)
    }

    const shouldRefresh =
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh')

    if (!shouldRefresh) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const newToken = await doRefresh(originalRequest)

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
      }

      return api(originalRequest)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  },
)

export function buildWebSocketUrl(path: string): string {
  const baseUrl = API_BASE_URL || getFallbackBaseUrl()
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(normalizedPath, baseUrl)

  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.hash = ''

  return url.toString()
}

export default api
