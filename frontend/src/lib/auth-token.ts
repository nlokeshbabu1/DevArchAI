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
