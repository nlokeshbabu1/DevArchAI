import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { getAccessToken, performRefresh } from './auth-token'

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
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
// Refresh handling. The actual /auth/refresh call is single-flight and shared
// app-wide via performRefresh() (see auth-token.ts) so that concurrent callers
// from the 401 interceptor and from auth-store.refreshSession() never issue two
// refreshes with the same (rotated) cookie in parallel.
// ---------------------------------------------------------------------------
function doRefresh(): Promise<string> {
  return performRefresh().catch((err) => {
    redirectToLogin()
    throw err
  })
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
      const newToken = await doRefresh()

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
