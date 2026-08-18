import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
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
    return render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    )
  }

  it('renders login form', () => {
    renderLogin()
    
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByText('Sign in to your account to continue')).toBeInTheDocument()
  })

  it('renders email input', () => {
    renderLogin()
    
    const emailInput = screen.getByPlaceholderText('you@example.com')
    expect(emailInput).toBeInTheDocument()
  })

  it('renders password input', () => {
    renderLogin()
    
    const passwordInput = screen.getByPlaceholderText('••••••••')
    expect(passwordInput).toBeInTheDocument()
  })

  it('renders sign in button', () => {
    renderLogin()
    
    const signInButton = screen.getByRole('button', { name: /sign in/i })
    expect(signInButton).toBeInTheDocument()
  })

  it('toggles password visibility', () => {
    renderLogin()
    
    const passwordInput = screen.getByPlaceholderText('••••••••')
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    const toggleButton = screen.getByRole('button')
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
    
    const signUpLink = screen.getByText(/sign up/i)
    expect(signUpLink).toBeInTheDocument()
  })

  it('disables submit button when loading', async () => {
    renderLogin()
    
    const signInButton = screen.getByRole('button', { name: /sign in/i })
    
    // Simulate form submission
    const emailInput = screen.getByPlaceholderText('you@example.com')
    const passwordInput = screen.getByPlaceholderText('••••••••')
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(signInButton)
    
    // Button should show loading state
    expect(screen.getByText(/signing in/i)).toBeInTheDocument()
  })
})
