import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Login } from './Login'

// Mock the auth store
vi.mock('../../stores/auth-store', () => ({
  useAuthStore: vi.fn(() => ({
    login: vi.fn(),
    setUser: vi.fn(),
  })),
}))

// Mock API
vi.mock('../../api/endpoints/auth', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}))

describe('Login', () => {
  const renderLogin = () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  it('renders login form', () => {
    renderLogin()

    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByText('Sign in to continue securing your infrastructure')).toBeInTheDocument()
  })

  it('renders email input', () => {
    renderLogin()

    const emailInput = screen.getByPlaceholderText('you@company.com')
    expect(emailInput).toBeInTheDocument()
  })

  it('renders password input', () => {
    renderLogin()

    const passwordInput = screen.getByPlaceholderText('Enter your password')
    expect(passwordInput).toBeInTheDocument()
  })

  it('renders sign in button', () => {
    renderLogin()

    const signInButton = screen.getByRole('button', { name: /sign in/i })
    expect(signInButton).toBeInTheDocument()
  })

  it('toggles password visibility', () => {
    renderLogin()

    const passwordInput = screen.getByPlaceholderText('Enter your password')
    expect(passwordInput).toHaveAttribute('type', 'password')

    const toggleButton = screen.getByRole('button', { name: 'Show password' })
    fireEvent.click(toggleButton)

    expect(passwordInput).toHaveAttribute('type', 'text')
  })

  it('has remember me checkbox', () => {
    renderLogin()

    const rememberMeCheckbox = screen.getByLabelText(/remember me/i)
    expect(rememberMeCheckbox).toBeInTheDocument()
  })

  it('has forgot password link', () => {
    renderLogin()

    const forgotPasswordLink = screen.getByText(/forgot password\?/i)
    expect(forgotPasswordLink).toBeInTheDocument()
  })

  it('has sign up link', () => {
    renderLogin()

    const signUpLink = screen.getByText(/create free account/i)
    expect(signUpLink).toBeInTheDocument()
  })

  it('disables submit button when loading', async () => {
    renderLogin()

    const signInButton = screen.getByRole('button', { name: /sign in/i })

    // Simulate form submission
    const emailInput = screen.getByPlaceholderText('you@company.com')
    const passwordInput = screen.getByPlaceholderText('Enter your password')

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(signInButton)

    // Button should show loading state and be disabled while submitting
    const submittingButton = screen.getByRole('button', { name: /signing in/i })
    expect(submittingButton).toBeDisabled()
  })
})
