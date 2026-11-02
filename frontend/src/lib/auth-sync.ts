/**
 * Cross-tab authentication sync (no tokens in messages).
 */

export type AuthSyncMessage =
  | { type: 'AUTH_LOGIN' }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'AUTH_SESSION_REVOKED' }
  | { type: 'AUTH_REFRESH_COMPLETE' }
  | { type: 'AUTH_REFRESH_REQUIRED' }

const CHANNEL_NAME = 'devarchai-auth-sync'

let channel: BroadcastChannel | null = null

function getChannel(): BroadcastChannel | null {
  if (typeof window === 'undefined' || typeof BroadcastChannel === 'undefined') {
    return null
  }
  if (!channel) {
    channel = new BroadcastChannel(CHANNEL_NAME)
  }
  return channel
}

export function broadcastAuthEvent(message: AuthSyncMessage): void {
  getChannel()?.postMessage(message)
}

export function subscribeAuthSync(handler: (message: AuthSyncMessage) => void): () => void {
  const ch = getChannel()
  if (!ch) {
    return () => {}
  }
  const listener = (event: MessageEvent<AuthSyncMessage>) => {
    if (!event.data?.type) {
      return
    }
    handler(event.data)
  }
  ch.addEventListener('message', listener)
  return () => ch.removeEventListener('message', listener)
}

/** Serialize refresh across tabs (same cookie jar) to avoid rotation reuse. */
export async function withCrossTabRefreshLock<T>(fn: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && navigator.locks?.request) {
    return navigator.locks.request('devarchai-auth-refresh', fn)
  }
  return fn()
}
