/**
 * In-memory access token store.
 *
 * The access token is held ONLY in JavaScript memory.  It is never
 * written to localStorage, sessionStorage, IndexedDB, or cookies.
 *
 * On browser reload the token is gone; the Axios interceptor will
 * automatically call POST /auth/refresh (the HttpOnly refresh cookie
 * is sent by the browser) to obtain a fresh access token.
 */

import axios, { AxiosError } from 'axios'
import { resolveRefreshUrl } from './api-base-url'
import { broadcastAuthEvent, subscribeAuthSync, withCrossTabRefreshLock } from './auth-sync'

let _accessToken: string | null = null
let _orgId: string | null = null

export function getAccessToken(): string | null {
  return _accessToken
}

export function setAccessToken(token: string | null): void {
  _accessToken = token
}

export function getOrgId(): string | null {
  return _orgId
}

export function setOrgId(id: string | null): void {
  _orgId = id
}

export function clearAuthMemory(): void {
  _accessToken = null
  _orgId = null
}

function shouldBroadcastSessionRevoked(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false
  }
  if (error.response?.status !== 401) {
    return false
  }
  const detail = error.response?.data?.detail
  if (typeof detail !== 'string') {
    return false
  }
  return /revoked|reuse|log in again/i.test(detail)
}

function waitForCrossTabRefreshComplete(timeoutMs = 15000): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      unsubscribe()
      reject(new Error('refresh wait timeout'))
    }, timeoutMs)

    const unsubscribe = subscribeAuthSync((message) => {
      if (message.type === 'AUTH_REFRESH_COMPLETE') {
        window.clearTimeout(timer)
        unsubscribe()
        resolve()
      }
    })
  })
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

async function postRefreshOnce(): Promise<string> {
  const response = await axios.post<{ access_token: string }>(
    resolveRefreshUrl(),
    null,
    { withCredentials: true, timeout: 30000 },
  )
  const { access_token } = response.data
  setAccessToken(access_token)
  broadcastAuthEvent({ type: 'AUTH_REFRESH_COMPLETE' })
  return access_token
}

async function postRefreshWithRotationRetry(): Promise<string> {
  try {
    return await postRefreshOnce()
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 429) {
      throw error
    }
    broadcastAuthEvent({ type: 'AUTH_REFRESH_REQUIRED' })
    try {
      await waitForCrossTabRefreshComplete()
    } catch {
      await sleep(400)
    }
    return postRefreshOnce()
  }
}

// ---------------------------------------------------------------------------
// Single-flight refresh (in-tab + Web Locks cross-tab).
// ---------------------------------------------------------------------------
let refreshInFlight: Promise<string> | null = null

export async function performRefresh(): Promise<string> {
  if (refreshInFlight) {
    return refreshInFlight
  }

  refreshInFlight = (async () => {
    try {
      return await withCrossTabRefreshLock(() => postRefreshWithRotationRetry())
    } catch (err) {
      clearAuthMemory()
      if (shouldBroadcastSessionRevoked(err)) {
        broadcastAuthEvent({ type: 'AUTH_SESSION_REVOKED' })
      }
      throw err
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

export function hasRefreshInFlight(): boolean {
  return refreshInFlight !== null
}
