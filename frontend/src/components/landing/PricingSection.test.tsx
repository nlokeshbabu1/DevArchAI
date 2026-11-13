import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PricingSection } from './PricingSection'
import { clearProductConfigCache } from '../../hooks/useProductConfig'
import { api } from '../../lib/api'

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

describe('PricingSection product config', () => {
  beforeEach(() => {
    clearProductConfigCache()
    vi.mocked(api.get).mockReset()
  })

  it('shows Beta access section when beta_access_mode is true', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        beta_access_mode: true,
        checkout_enabled: false,
        show_upgrade_prompts: false,
        beta_label: 'DevArchAI Beta — Free Access',
        limits: { max_scans_per_month: 50, max_repositories: 10 },
      },
    })

    render(
      <BrowserRouter>
        <PricingSection />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /build and scan during beta/i })).toBeInTheDocument()
    })
    expect(screen.queryByText('$12')).not.toBeInTheDocument()
    expect(screen.queryByText('Start Free Trial')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /join beta/i })).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
  })

  it('shows commercial pricing when beta_access_mode is false', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        beta_access_mode: false,
        checkout_enabled: true,
        show_upgrade_prompts: true,
        beta_label: null,
      },
    })

    render(
      <BrowserRouter>
        <PricingSection />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Choose Your Plan')).toBeInTheDocument()
    })
    expect(screen.getByText('$0')).toBeInTheDocument()
    expect(screen.getByText('Plus')).toBeInTheDocument()
    expect(screen.getByText('AI Remediation Gating')).toBeInTheDocument()
  })

  it('falls back to commercial pricing on API error', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network'))

    render(
      <BrowserRouter>
        <PricingSection />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Choose Your Plan')).toBeInTheDocument()
    })
  })
})
