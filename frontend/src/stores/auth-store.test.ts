import { describe, it, expect, beforeEach } from 'vitest'
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
    useAuthStore.getState().setLoading(true)
    expect(useAuthStore.getState().isLoading).toBe(true)
    
    useAuthStore.getState().setLoading(false)
    expect(useAuthStore.getState().isLoading).toBe(false)
  })

  it('checks authentication status', () => {
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    
    useAuthStore.getState().login('token')
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })
})
