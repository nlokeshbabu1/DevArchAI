import '@testing-library/jest-dom'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../../stores/auth-store', () => ({
  useAuthStore: () => ({ token: 'test-token' }),
}))

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn(async () => ({
      data: [
        {
          id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
          repository_url: 'https://github.com/org/repo',
          status: 'completed',
          progress: 100,
          created_at: new Date().toISOString(),
        },
      ],
    })),
  },
}))

vi.mock('../../api/endpoints/scans', () => ({
  scansApi: {
    startUnifiedScan: vi.fn(),
  },
}))

import { ScansPage } from './ScansPage'

describe('ScansPage View Report navigation', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
  })

  it('navigates to the scan report route instead of history', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ScansPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const viewReport = await screen.findByRole('button', { name: /view report/i })
    fireEvent.click(viewReport)

    expect(mockNavigate).toHaveBeenCalledWith(
      '/scans/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    )
    expect(mockNavigate).not.toHaveBeenCalledWith('/history')
  })
})
