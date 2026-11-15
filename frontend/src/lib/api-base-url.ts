/**
 * Single source of truth for API origin (must match where HttpOnly refresh cookies are set).
 *
 * In local dev with Vite, leave VITE_API_BASE_URL unset so requests go to the dev server
 * origin (e.g. http://localhost:5174) and the `/api` proxy forwards to the backend.
 * Do not point this at http://localhost:8000 unless the app is also served from :8000.
 */

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/$/, '')
}

function browserOrigin(): string {
  return typeof window !== 'undefined' ? window.location.origin : ''
}

export function getConfiguredApiBaseUrl(): string {
  const fromEnv =
    (import.meta.env.VITE_API_BASE_URL)?.trim() ||
    (import.meta.env.VITE_API_URL)?.trim()
  if (fromEnv) {
    return normalizeBaseUrl(fromEnv)
  }
  return normalizeBaseUrl(browserOrigin())
}

export function getApiV1BaseUrl(): string {
  const base = getConfiguredApiBaseUrl()
  return base ? `${base}/api/v1` : '/api/v1'
}

export function resolveRefreshUrl(): string {
  return `${getConfiguredApiBaseUrl()}/api/v1/auth/refresh`
}

export function warnIfDevApiOriginMismatch(): void {
  if (!import.meta.env.DEV || typeof window === 'undefined') {
    return
  }
  const configured = (import.meta.env.VITE_API_BASE_URL)?.trim()
  if (!configured) {
    return
  }
  try {
    const cfg = new URL(configured)
    const page = new URL(window.location.href)
    if (cfg.origin !== page.origin) {
      console.warn(
        '[DevArchAI] VITE_API_BASE_URL origin differs from the page origin. ' +
          'HttpOnly refresh cookies are scoped to the login response host; use the Vite proxy ' +
          '(unset VITE_API_BASE_URL) or serve the UI from the same origin as the API.',
      )
    }
  } catch {
    // ignore invalid URL
  }
}
