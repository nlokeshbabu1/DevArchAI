import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UserAccountMenu, userInitials } from './UserAccountMenu'

describe('UserAccountMenu', () => {
  it('renders real user identity fields', () => {
    render(
      <UserAccountMenu
        user={{ email: 'dev@example.com', username: 'devuser', full_name: 'Dev User', plan: 'plus', role: 'admin' }}
        productConfig={{
          beta_access_mode: true,
          beta_label: 'Beta',
          checkout_enabled: false,
          show_upgrade_prompts: false,
          limits: {},
        }}
        onSettings={vi.fn()}
        onLogout={vi.fn()}
      />,
    )
    expect(screen.getByText('Dev User')).toBeInTheDocument()
    expect(screen.getByText('dev@example.com')).toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
  })

  it('calls logout handler', () => {
    const onLogout = vi.fn()
    render(
      <UserAccountMenu
        user={{ email: 'a@b.com', username: 'ab' }}
        productConfig={{
          beta_access_mode: false,
          checkout_enabled: true,
          show_upgrade_prompts: true,
          limits: {},
        }}
        onSettings={vi.fn()}
        onBilling={vi.fn()}
        onLogout={onLogout}
      />,
    )
    fireEvent.click(screen.getByRole('menuitem', { name: /log out/i }))
    expect(onLogout).toHaveBeenCalled()
  })

  it('builds initials from display name', () => {
    expect(userInitials({ full_name: 'Jane Doe', email: 'j@d.com' })).toBe('JD')
    expect(userInitials({ username: 'solo', email: 's@d.com' })).toBe('SO')
  })
})