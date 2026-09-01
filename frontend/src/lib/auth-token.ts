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

// ---------------------------------------------------------------------------
// Single-flight refresh.
//
// The access token is in-memory only, so on every page refresh several code
// paths may try to restore the session at once (App + ProtectedRoute mount
// effects, plus the 401 interceptor of any early component request). Each
// attempt POSTs /auth/refresh with the SAME HttpOnly refresh cookie. The
// backend ROTATES the cookie on each successful refresh, so a concurrent
// duplicate request would present the now-revoked token and be treated as
// token reuse -> the entire session gets revoked (logout). One shared promise
// guarantees only a single /auth/refresh is in flight at any moment across
// the whole app.
// ---------------------------------------------------------------------------
let refreshInFlight: Promise<string> | null = null

function resolveRefreshUrl(): string {
  const origin =
    typeof window !== 'undefined' ? window.location.origin : ''
  const configured = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
  const base = (configured || origin).replace(/\/$/, '')
  return `${base}/api/v1/auth/refresh`
}

export async function performRefresh(): Promise<string> {
  if (refreshInFlight) {
    return refreshInFlight
  }

  refreshInFlight = (async () => {
    try {
      const { default: axios } = await import('axios')
      const response = await axios.post<{ access_token: string }>(
        resolveRefreshUrl(),
        null,
        { withCredentials: true, timeout: 30000 },
      )
      const { access_token } = response.data
      setAccessToken(access_token)
      return access_token
    } catch (err) {
      clearAuthMemory()
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
