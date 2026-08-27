import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('framer-motion', () => {
  const createMotionComponent = (tag: string) => {
    const Component = ({ children, ...props }: any) => {
      const { initial, animate, transition, exit, whileHover, whileTap, ...domProps } = props
      const Tag = tag
      return <Tag {...domProps}>{children}</Tag>
    }
    Component.displayName = `motion.${tag}`
    return Component
  }

  const motion = new Proxy({}, {
    get(_: any, prop: string) {
      return createMotionComponent(prop)
    },
  })

  return {
    motion,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    useReducedMotion: () => false,
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: vi.fn(() => ({ id: 'test-scan-id' })),
    useNavigate: vi.fn(() => vi.fn()),
  }
})

const mockGetStages = vi.fn()
const mockGetScanState = vi.fn()
const mockGetScanResults = vi.fn()

vi.mock('../api/endpoints/scans', () => ({
  scansApi: {
    getStages: (...args: any[]) => mockGetStages(...args),
    getScanState: (...args: any[]) => mockGetScanState(...args),
    getScanResults: (...args: any[]) => mockGetScanResults(...args),
  },
}))

vi.mock('../api/endpoints/pull-requests', () => ({
  prApi: { createPR: vi.fn() },
}))

vi.mock('../api/endpoints/reports', () => ({
  reportsApi: { downloadReport: vi.fn() },
}))

vi.mock('../hooks/useScanWebSocket', () => ({
  useScanWebSocket: vi.fn(() => ({
    lifecycleState: 'running',
    scanState: null,
    error: null,
    connectionStatus: 'connecting',
  })),
}))

vi.mock('../components/scan-results/ScanResultsDashboard', () => ({
  ScanResultsDashboard: ({ repoName }: any) => (
    <div data-testid="scan-results-dashboard">
      <h2>Security Report for {repoName}</h2>
    </div>
  ),
}))

vi.mock('../lib/utils', async () => {
  const actual = await vi.importActual('../lib/utils')
  return {
    ...actual,
    copyToClipboard: vi.fn().mockResolvedValue(true),
  }
})

vi.mock('../components/ui-animated', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>{children}</button>
  ),
  Card: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}))

import { ScanProgressPage } from './ScanProgressPage'
import { useParams, useNavigate } from 'react-router-dom'
import { useScanWebSocket } from '../hooks/useScanWebSocket'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
}

function renderPage(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      {ui}
    </QueryClientProvider>
  )
}

const defaultWsMock = {
  lifecycleState: 'running' as const,
  scanState: null,
  error: null,
  connectionStatus: 'connecting' as const,
  completedStages: [] as const,
  failedStages: [] as const,
}

function mockWs(overrides: Record<string, unknown> = {}) {
  return { ...defaultWsMock, ...overrides }
}

const mockScanState = (overrides: Record<string, any> = {}) => ({
  scanId: 'test-scan-id',
  status: 'running',
  currentStage: 'scanning',
  progress: 50,
  detectedStack: [],
  isTerminal: false,
  scanners: {},
  liveFindings: [],
  aiProgress: null,
  stageTransitions: [],
  filesScanned: 0,
  totalFiles: 0,
  severityCounts: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  logs: [],
  ...overrides,
})

describe('ScanProgressPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useParams).mockReturnValue({ id: 'test-scan-id' })
    vi.mocked(useNavigate).mockReturnValue(vi.fn())
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs())

    mockGetStages.mockResolvedValue([
      { id: 'connecting_repository', label: 'Connecting to repository', icon: 'git-branch', order: 0, kind: 'base' },
      { id: 'cloning', label: 'Cloning repository', icon: 'download', order: 1, kind: 'base' },
      { id: 'detecting_technologies', label: 'Detecting technologies', icon: 'cpu', order: 2, kind: 'base' },
      { id: 'scanning', label: 'Running security rules', icon: 'shield', order: 3, kind: 'base' },
      { id: 'analyzing', label: 'Analyzing findings', icon: 'brain', order: 4, kind: 'base' },
      { id: 'scan_completed', label: 'Scan completed', icon: 'check', order: 5, kind: 'base' },
    ])
    mockGetScanState.mockResolvedValue({
      scan_id: 'test-scan-id',
      status: 'running',
      current_stage: 'scanning',
      progress: 50,
      is_terminal: false,
      detected_stack: [],
      started_at: '2024-01-01T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
    })
  })

  it('should show loading state initially', async () => {
    mockGetScanState.mockReturnValue(new Promise(() => {}))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    expect(screen.getByText('Connecting to scan...')).toBeInTheDocument()
  })

  it('should show error state on fetch failure', async () => {
    vi.useFakeTimers()
    mockGetScanState.mockRejectedValue(new Error('Not found'))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await vi.advanceTimersByTimeAsync(15000)
    expect(screen.getByText('Scan Not Found')).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('should render stage timeline when scanning', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({ currentStage: 'scanning' }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getAllByText('Running security rules').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('Connecting to repository')).toBeInTheDocument()
      expect(screen.getByText('Cloning repository')).toBeInTheDocument()
    })
  })

  it('should show progress percentage from backend', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({ progress: 75 }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      const pctElements = screen.getAllByText(/%/)
      expect(pctElements.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('should show elapsed time', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({
        startedAt: new Date(Date.now() - 65000).toISOString(),
      }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText(/01:/)).toBeInTheDocument()
    })
  })

  it('should show disabled Rescan button during scan', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState(),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      const rescanBtn = screen.getByText('Rescan')
      expect(rescanBtn).toBeDisabled()
    })
  })

  it('should show detected technologies', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({
        detectedStack: ['Docker', 'Terraform', 'Kubernetes'],
      }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getAllByText('Docker').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('Terraform').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('Kubernetes').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('should show file scanning progress', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({ filesScanned: 245, totalFiles: 1380 }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText(/245\/1380 files/)).toBeInTheDocument()
    })
  })

  it('should show scanner cards when scanners exist', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({
        scanners: {
          hadolint: { scanner_id: 'hadolint', scanner_name: 'hadolint', status: 'running', findings_count: 0 },
        },
      }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Scanner Progress')).toBeInTheDocument()
      expect(screen.getByText('hadolint')).toBeInTheDocument()
    })
  })

  it('should show live findings with severity', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({
        liveFindings: [
          { rule_id: 'R001', rule_name: 'Hardcoded Secret', severity: 'critical', category: 'secrets', description: 'Found secret', timestamp: new Date().toISOString() },
        ],
        severityCounts: { critical: 1, high: 0, medium: 0, low: 0, info: 0 },
      }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Live Findings')).toBeInTheDocument()
      expect(screen.getByText('Hardcoded Secret')).toBeInTheDocument()
    })
  })

  it('should show AI generation panel during ai_generation stage', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({
        currentStage: 'ai_generation',
        aiProgress: { phase: 'analyzing', message: 'Analyzing findings', progress: 45, findings_processed: 5, findings_total: 10, timestamp: new Date().toISOString() },
      }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('AI Analysis')).toBeInTheDocument()
      expect(screen.getByText('Analyzing 5 of 10 findings')).toBeInTheDocument()
    })
  })

  it('should show full report when scan completes', async () => {
    mockGetScanState.mockResolvedValue({
      scan_id: 'test-scan-id',
      status: 'completed',
      current_stage: null,
      progress: 100,
      is_terminal: true,
      detected_stack: [],
      started_at: '2024-01-01T00:00:00Z',
      completed_at: '2024-01-01T00:01:08Z',
      created_at: '2024-01-01T00:00:00Z',
    })
    mockGetScanResults.mockResolvedValue({
      scan_id: 'test-scan-id',
      repository_name: 'myorg/repo',
      security_score: 85,
      findings: [],
      files_analyzed: 150,
      branch: 'main',
      analysis_duration_seconds: 68,
      ai_suggestions_count: 5,
    })

    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'completed',
      scanState: mockScanState({
        status: 'completed',
        currentStage: null,
        progress: 100,
        isTerminal: true,
      }),
      error: null,
      connectionStatus: 'disconnected',
    }))

    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('scan-results-dashboard')).toBeInTheDocument()
    }, { timeout: 10000 })

    expect(screen.getByText('Security Report for myorg/repo')).toBeInTheDocument()
  })

  it('should show failed state when scan fails', async () => {
    mockGetScanState.mockResolvedValue({
      scan_id: 'test-scan-id',
      status: 'failed',
      current_stage: null,
      progress: 0,
      is_terminal: true,
      error_message: 'Scan timed out',
      detected_stack: [],
      created_at: '2024-01-01T00:00:00Z',
    })

    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'failed',
      scanState: mockScanState({
        status: 'failed',
        currentStage: null,
        progress: 0,
        isTerminal: true,
        errorMessage: 'Scan timed out',
      }),
      error: null,
      connectionStatus: 'disconnected',
    }))

    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Scan Failed')).toBeInTheDocument()
      expect(screen.getByText('Scan timed out')).toBeInTheDocument()
    })
  })

  it('should connect WebSocket with scan id', async () => {
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(useScanWebSocket).toHaveBeenCalledWith(
        expect.objectContaining({ scanId: 'test-scan-id' })
      )
    })
  })

  it('should show completed stages with checkmarks', async () => {
    vi.mocked(useScanWebSocket).mockReturnValue(mockWs({
      lifecycleState: 'running',
      scanState: mockScanState({ currentStage: 'scanning' }),
      error: null,
      connectionStatus: 'connected',
    }))
    renderPage(
      <MemoryRouter>
        <ScanProgressPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Connecting to repository')).toBeInTheDocument()
      expect(screen.getByText('Cloning repository')).toBeInTheDocument()
      expect(screen.getByText('Detecting technologies')).toBeInTheDocument()
      expect(screen.getAllByText('Running security rules').length).toBeGreaterThanOrEqual(1)
    })
  })
})
