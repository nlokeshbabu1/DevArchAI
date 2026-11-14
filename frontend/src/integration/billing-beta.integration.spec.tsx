import '@testing-library/jest-dom'

import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PricingSection } from '../components/landing/PricingSection'
import { clearProductConfigCache } from '../hooks/useProductConfig'
import { api } from '../lib/api'

import { renderWithProviders } from './test-utils'

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

describe('integration: billing product config and Beta access UI', () => {
  beforeEach(() => {
    clearProductConfigCache()
    vi.mocked(api.get).mockReset()
  })

  it('loads product config via API and shows Beta access copy', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        beta_access_mode: true,
        checkout_enabled: false,
        show_upgrade_prompts: false,
        beta_label: 'DevArchAI Beta — Free Access',
        limits: { max_scans_per_month: 50, max_repositories: 10 },
      },
    })

    renderWithProviders(<PricingSection />, { route: '/' })

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled()
      expect(screen.getByRole('heading', { name: /build and scan during beta/i })).toBeInTheDocument()
    })
  })
})
