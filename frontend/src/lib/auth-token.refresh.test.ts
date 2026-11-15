import axios from 'axios'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('./auth-sync', () => ({
  broadcastAuthEvent: vi.fn(),
  subscribeAuthSync: vi.fn((handler: (msg: { type: string }) => void) => {
    queueMicrotask(() => handler({ type: 'AUTH_REFRESH_COMPLETE' }))
    return () => {}
  }),
  withCrossTabRefreshLock: (fn: () => Promise<string>) => fn(),
}))

vi.mock('./api-base-url', () => ({
  resolveRefreshUrl: () => 'http://localhost/api/v1/auth/refresh',
}))

describe('performRefresh rotation retry', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('retries after 429 when another tab holds the rotation lock', async () => {
    const axiosError = Object.assign(new Error('429'), {
      isAxiosError: true,
      response: { status: 429 },
    })

    const post = vi
      .spyOn(axios, 'post')
      .mockRejectedValueOnce(axiosError)
      .mockResolvedValueOnce({ data: { access_token: 'new-token' } })

    vi.spyOn(axios, 'isAxiosError').mockImplementation((v) => Boolean((v as { isAxiosError?: boolean })?.isAxiosError))

    const { performRefresh, getAccessToken, clearAuthMemory } = await import('./auth-token')
    clearAuthMemory()
    const token = await performRefresh()
    expect(token).toBe('new-token')
    expect(getAccessToken()).toBe('new-token')
    expect(post).toHaveBeenCalledTimes(2)
  })
})
