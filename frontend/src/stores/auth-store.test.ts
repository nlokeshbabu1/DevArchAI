import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

import { useAuthStore } from '../stores/auth-store'

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      isAuthenticated: false,
      user: null,
      isLoading: false,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('initializes with default state', () => {
    const state = useAuthStore.getState()
    
    expect(state.isAuthenticated).toBe(false)
    expect(state.user).toBeNull()
    expect(state.isLoading).toBe(false)
  })

  it('sets user on login', () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      username: 'testuser',
    }
    
    useAuthStore.getState().setUser(mockUser)
    
    const state = useAuthStore.getState()
    expect(state.user).toEqual(mockUser)
  })

  it('sets authentication on login', () => {
    const mockToken = 'mock-jwt-token'
    
    useAuthStore.getState().login(mockToken)
    
    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
  })

  it('clears state on logout', () => {
    // First login
    useAuthStore.getState().login('token')
    useAuthStore.getState().setUser({ id: '123', email: 'test@test.com', username: 'test' })
    
    // Then logout
    useAuthStore.getState().logout()
    
    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(false)
    expect(state.user).toBeNull()
  })

  it('updates loading state', () => {
    useAuthStore.setState({ isLoading: true })
    expect(useAuthStore.getState().isLoading).toBe(true)

    useAuthStore.setState({ isLoading: false })
    expect(useAuthStore.getState().isLoading).toBe(false)
  })

  it('serverLogout calls backend logout before clearing state', async () => {
    const { api } = await import('../lib/api')
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: { message: 'ok' } })
    const replaceMock = vi.fn()
    const originalLocation = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, replace: replaceMock },
    })

    useAuthStore.getState().login('token')
    await useAuthStore.getState().serverLogout()

    expect(postSpy).toHaveBeenCalledWith('/auth/logout')
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(replaceMock).toHaveBeenCalledWith('/login')

    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
  })

  it('single-flights concurrent refreshSession calls', async () => {
    const { default: axios } = await import('axios')
    let refreshCalls = 0

    vi.spyOn(axios, 'post').mockImplementation(async (url: string) => {
      if (String(url).includes('/auth/refresh')) {
        refreshCalls += 1
        await new Promise((r) => setTimeout(r, 10))
        return { data: { access_token: 'refreshed-token' } }
      }
      if (String(url).includes('/auth/me')) {
        return { data: { id: '123', email: 'a@b.co', username: 'user' } }
      }
      return { data: {} }
    }) as any

    const [first, second] = await Promise.all([
      useAuthStore.getState().refreshSession(),
      useAuthStore.getState().refreshSession(),
    ])

    expect(first).toBe(true)
    expect(second).toBe(true)
    // Both callers share ONE refresh request -> no double rotation.
    expect(refreshCalls).toBe(1)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })
})
