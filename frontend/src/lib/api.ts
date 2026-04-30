import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
}

interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
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

function getStorageItem(key: string): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  return window.localStorage.getItem(key)
}

function clearAuthStorage() {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem('access_token')
  window.localStorage.removeItem('refresh_token')
  window.localStorage.removeItem('current_org_id')
}

function redirectToLogin() {
  if (typeof window === 'undefined') {
    return
  }

  window.location.href = '/login'
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
})

api.interceptors.request.use(
  (config) => {
    const token = getStorageItem('access_token')
    const orgId = getStorageItem('current_org_id')

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    if (orgId && config.headers) {
      config.headers['X-Organization-ID'] = orgId
    }

    console.debug('[api request]', (config.method || 'get').toUpperCase(), axios.getUri(config))
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

    const refreshToken = getStorageItem('refresh_token')
    if (!refreshToken) {
      clearAuthStorage()
      redirectToLogin()
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const refreshResponse = await axios.post<RefreshTokenResponse>(
        `${API_V1_BASE_URL}/auth/refresh`,
        null,
        {
          headers: {
            Authorization: `Bearer ${refreshToken}`,
          },
        },
      )

      const { access_token, refresh_token } = refreshResponse.data

      if (typeof window !== 'undefined') {
        window.localStorage.setItem('access_token', access_token)
        window.localStorage.setItem('refresh_token', refresh_token)
      }

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${access_token}`
      }

      return api(originalRequest)
    } catch (refreshError) {
      clearAuthStorage()
      redirectToLogin()
      return Promise.reject(refreshError)
    }
  },
)

export function buildWebSocketUrl(path: string): string {
  const baseUrl = API_BASE_URL || getFallbackBaseUrl()
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(normalizedPath, baseUrl)

  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.search = ''
  url.hash = ''

  return url.toString()
}

export default api
