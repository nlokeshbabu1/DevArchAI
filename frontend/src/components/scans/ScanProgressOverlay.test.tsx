import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ScanProgressOverlay } from './ScanProgressOverlay'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props} data-motion="div">{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('../../lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
  formatDuration: (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  },
}))

vi.mock('lucide-react', () => ({
  CheckCircle: () => <span data-testid="icon-checkcircle">CheckCircle</span>,
  CheckCircle2: () => <span data-testid="icon-checkcircle2">CheckCircle2</span>,
  XCircle: () => <span data-testid="icon-xcircle">XCircle</span>,
  Circle: () => <span data-testid="icon-circle">Circle</span>,
  Clock: () => <span data-testid="icon-clock">Clock</span>,
  GitBranch: () => <span data-testid="icon-gitbranch">GitBranch</span>,
  Loader2: () => <span data-testid="icon-loader">Loader2</span>,
  AlertCircle: () => <span data-testid="icon-alert">AlertCircle</span>,
  X: () => <span data-testid="icon-x">X</span>,
  TrendingUp: () => <span data-testid="icon-trendingup">TrendingUp</span>,
  TrendingDown: () => <span data-testid="icon-trendingdown">TrendingDown</span>,
  CheckCheck: () => <span data-testid="icon-checkcheck">CheckCheck</span>,
}))

vi.mock('../ui-animated', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>{children}</button>
  ),
}))

const defaultStages = [
  { id: 'connecting_repository' as const, label: 'Connect to repository', icon: 'git-branch', order: 1, kind: 'base' as const },
  { id: 'cloning' as const, label: 'Clone repository', icon: 'download', order: 2, kind: 'base' as const },
  { id: 'detecting_technologies' as const, label: 'Detect technologies', icon: 'search', order: 4, kind: 'base' as const },
  { id: 'scanning' as const, label: 'Security scan', icon: 'shield', order: 5, kind: 'base' as const },
]

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  repositoryName: 'myorg/my-repo',
  branch: 'main',
  progressData: { currentStep: 'Analyzing repository...' },
  isComplete: false,
  hasFailed: false,
  onComplete: vi.fn(),
  stages: defaultStages,
  currentStage: 'scanning' as const,
}

describe('ScanProgressOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render repository name and branch', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('myorg/my-repo')).toBeInTheDocument()
    expect(screen.getByText('main')).toBeInTheDocument()
  })

  it('should render lifecycle stages from backend', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('Connect to repository')).toBeInTheDocument()
    expect(screen.getByText('Clone repository')).toBeInTheDocument()
    expect(screen.getAllByText('Security scan').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Detect technologies')).toBeInTheDocument()
  })

  it('should show current step message in subtitle', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getAllByText('Analyzing repository...').length).toBeGreaterThanOrEqual(1)
  })

  it('should show elapsed time when startedAt is provided', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        startedAt={new Date(Date.now() - 5000).toISOString()}
      />
    )
    expect(screen.getByTestId('icon-clock')).toBeInTheDocument()
  })

  it('should show success state when isComplete is true', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        isComplete={true}
        resultSummary={{
          securityScore: 85,
          grade: 'B',
          severityCounts: { critical: 0, high: 1, medium: 3, low: 5 },
          filesScanned: 42,
          scanDuration: 120,
        }}
      />
    )
    expect(screen.getAllByText('Scan Complete').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByTestId('icon-checkcheck')).toBeInTheDocument()
  })

  it('should show failure state when hasFailed is true', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        hasFailed={true}
        progressData={{ error: 'Connection timeout' }}
      />
    )
    expect(screen.getByText('Scan Failed')).toBeInTheDocument()
    expect(screen.getAllByText('Connection timeout').length).toBeGreaterThanOrEqual(1)
  })

  it('should call onComplete when complete and action button clicked', () => {
    const onComplete = vi.fn()
    render(
      <ScanProgressOverlay
        {...defaultProps}
        isComplete={true}
        onComplete={onComplete}
      />
    )

    fireEvent.click(screen.getByText('View Results'))
    expect(onComplete).toHaveBeenCalled()
  })

  it('should call onRetry when retry button clicked in failed state', () => {
    const onRetry = vi.fn()
    render(
      <ScanProgressOverlay
        {...defaultProps}
        hasFailed={true}
        progressData={{ error: 'Timeout' }}
        onRetry={onRetry}
      />
    )

    fireEvent.click(screen.getByText('Retry Scan'))
    expect(onRetry).toHaveBeenCalled()
  })

  it('should render detected technologies dynamically', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        currentStage="detecting_technologies"
        technologies={{
          docker: { technology: 'Docker', detected: true, findings: 4 },
          kubernetes: { technology: 'Kubernetes', detected: true, findings: 21 },
        }}
      />
    )
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('Kubernetes')).toBeInTheDocument()
    expect(screen.getByText('4 findings')).toBeInTheDocument()
  })
})
