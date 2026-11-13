/** Guest scan session tokens returned by POST /scan/start (never put in URLs). */

const STORAGE_PREFIX = 'devarchai:scan-session:'

export function saveScanSessionToken(scanId: string, sessionToken: string): void {
  if (typeof window === 'undefined' || !scanId || !sessionToken) return
  try {
    sessionStorage.setItem(`${STORAGE_PREFIX}${scanId}`, sessionToken)
  } catch {
    /* ignore quota / private mode */
  }
}

export function getScanSessionToken(scanId: string | null | undefined): string | null {
  if (typeof window === 'undefined' || !scanId) return null
  try {
    return sessionStorage.getItem(`${STORAGE_PREFIX}${scanId}`)
  } catch {
    return null
  }
}

export function scanSessionHeader(scanId: string | null | undefined): Record<string, string> {
  const token = getScanSessionToken(scanId)
  return token ? { 'X-Session-Token': token } : {}
}
