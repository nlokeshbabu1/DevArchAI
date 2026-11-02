import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { broadcastAuthEvent, subscribeAuthSync, withCrossTabRefreshLock } from './auth-sync'

describe('auth-sync', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'BroadcastChannel',
      class {
        name: string
        listeners: Array<(event: MessageEvent) => void> = []
        constructor(name: string) {
          this.name = name
        }
        postMessage(data: unknown) {
          for (const listener of this.listeners) {
            listener({ data } as MessageEvent)
          }
        }
        addEventListener(_type: string, listener: (event: MessageEvent) => void) {
          this.listeners.push(listener)
        }
        removeEventListener(_type: string, listener: (event: MessageEvent) => void) {
          this.listeners = this.listeners.filter((l) => l !== listener)
        }
        close() {}
      },
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('delivers auth events without token payloads', () => {
    const handler = vi.fn()
    subscribeAuthSync(handler)
    broadcastAuthEvent({ type: 'AUTH_LOGOUT' })
    expect(handler).toHaveBeenCalledWith({ type: 'AUTH_LOGOUT' })
    const payload = JSON.stringify(handler.mock.calls[0][0])
    expect(payload).not.toMatch(/token/i)
  })

  it('runs refresh lock callback', async () => {
    const fn = vi.fn(async () => 'ok')
    await expect(withCrossTabRefreshLock(fn)).resolves.toBe('ok')
    expect(fn).toHaveBeenCalledOnce()
  })
})
