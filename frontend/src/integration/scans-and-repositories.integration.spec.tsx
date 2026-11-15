import '@testing-library/jest-dom'

import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../lib/api'
import { ScansPage } from '../pages/scans/ScansPage'

import { FIXTURE_SCAN_ID, sampleScanList } from './fixtures/scans'
import { renderWithProviders } from './test-utils'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../stores/auth-store', () => ({
  useAuthStore: () => ({ token: 'integration-token', isAuthenticated: true }),
}))

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('integration: scan list and navigation', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/scans' || url.startsWith('/scans')) {
        return { data: sampleScanList }
      }
      throw new Error(`Unexpected GET ${url}`)
    })
  })

  it('loads scans from API and navigates to scan detail on View Report', async () => {
    renderWithProviders(<ScansPage />, { route: '/scans' })

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/scans')
    })

    const viewReport = await screen.findByRole('button', { name: /view report/i })
    fireEvent.click(viewReport)

    expect(mockNavigate).toHaveBeenCalledWith(`/scans/${FIXTURE_SCAN_ID}`)
  })
})
