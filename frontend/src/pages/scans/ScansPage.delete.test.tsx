import '@testing-library/jest-dom'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { deleteScan, mockNavigate } = vi.hoisted(() => ({
  deleteScan: vi.fn(),
  mockNavigate: vi.fn(),
}))

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
          id: '0407084e-498d-4874-8f16-a32d0225adac',
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
    deleteScan,
  },
}))

vi.mock('../../hooks/useToast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import { ScansPage } from './ScansPage'

describe('ScansPage delete scan', () => {
  beforeEach(() => {
    deleteScan.mockReset()
    deleteScan.mockResolvedValue({ message: 'ok', success: true })
  })

  it('confirms deletion and calls DELETE scan API', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ScansPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const openDelete = await screen.findByRole('button', {
      name: /delete scan for https:\/\/github.com\/org\/repo/i,
    })
    fireEvent.click(openDelete)

    const confirm = await screen.findByText('Delete scan')
    fireEvent.click(confirm)

    await waitFor(() => {
      expect(deleteScan).toHaveBeenCalledWith('0407084e-498d-4874-8f16-a32d0225adac')
    })
  })
})