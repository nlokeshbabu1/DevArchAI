import '@testing-library/jest-dom'

import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

import { renderWithProviders } from './test-utils'

const authState = vi.hoisted(() => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  sessionChecked: true,
  logoutInProgress: false,
  login: vi.fn(),
  logout: vi.fn(),
  setUser: vi.fn(),
  setLoading: vi.fn(),
  checkAuth: vi.fn(),
  fetchUserInfo: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue(false),
  serverLogout: vi.fn(),
}))

vi.mock('../stores/auth-store', () => ({
  initAuthSync: vi.fn(),
  useAuthStore: Object.assign(
    (selector?: (s: typeof authState) => unknown) => {
      if (typeof selector === 'function') {
        return selector(authState)
      }
      return authState
    },
    {
      getState: () => authState,
    },
  ),
}))

describe('integration: authentication and protected routes', () => {
  beforeEach(() => {
    authState.isAuthenticated = false
    authState.isLoading = false
  })

  it('redirects unauthenticated users from dashboard to login', async () => {
    renderWithProviders(<App />, { route: '/dashboard' })

    await waitFor(() => {
      expect(screen.getByText('Welcome back')).toBeInTheDocument()
    })
  })

  it('allows authenticated users to reach dashboard shell', async () => {
    authState.isAuthenticated = true

    renderWithProviders(<App />, { route: '/dashboard' })

    await waitFor(() => {
      expect(screen.queryByText('Welcome back')).not.toBeInTheDocument()
    })
  })
})
