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
  Clock: () => <span data-testid="icon-clock">Clock</span>,
  GitBranch: () => <span data-testid="icon-gitbranch">GitBranch</span>,
  Loader2: () => <span data-testid="icon-loader">Loader2</span>,
  AlertCircle: () => <span data-testid="icon-alert">AlertCircle</span>,
  X: () => <span data-testid="icon-x">X</span>,
  TrendingUp: () => <span data-testid="icon-trendingup">TrendingUp</span>,
  TrendingDown: () => <span data-testid="icon-trendingdown">TrendingDown</span>,
  Activity: () => <span data-testid="icon-activity">Activity</span>,
  Search: () => <span data-testid="icon-search">Search</span>,
  FileCode: () => <span data-testid="icon-filecode">FileCode</span>,
  Layers: () => <span data-testid="icon-layers">Layers</span>,
  Shield: () => <span data-testid="icon-shield">Shield</span>,
  Brain: () => <span data-testid="icon-brain">Brain</span>,
  FileText: () => <span data-testid="icon-filetext">FileText</span>,
  CheckCheck: () => <span data-testid="icon-checkcheck">CheckCheck</span>,
  Filter: () => <span data-testid="icon-filter">Filter</span>,
  Download: () => <span data-testid="icon-download">Download</span>,
}))

vi.mock('../ui-animated', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>{children}</button>
  ),
}))

const defaultStages = [
  { id: 'connecting' as const, label: 'Connecting to Repository', icon: 'git-branch', order: 0 },
  { id: 'cloning' as const, label: 'Cloning Repository', icon: 'download', order: 1 },
  { id: 'technology_detection' as const, label: 'Detecting Technologies', icon: 'search', order: 2 },
  { id: 'scanning' as const, label: 'Running Security Scan', icon: 'shield', order: 3 },
]

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  repositoryName: 'myorg/my-repo',
  branch: 'main',
  progressData: { progress: 65, currentStep: 'Scanning files' },
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

  it('should show progress bar with correct percentage', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getAllByText('65%').length).toBeGreaterThanOrEqual(1)
  })

  it('should render stages from backend', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('Connecting to Repository')).toBeInTheDocument()
    expect(screen.getByText('Cloning Repository')).toBeInTheDocument()
    expect(screen.getByText('Detecting Technologies')).toBeInTheDocument()
    // "Running Security Scan" appears as both the currentStep label and the stage label
    expect(screen.getAllByText('Running Security Scan').length).toBeGreaterThanOrEqual(1)
  })

  it('should highlight completed stages based on currentStage', () => {
    render(<ScanProgressOverlay {...defaultProps} currentStage="scanning" />)
    expect(screen.getByText('Scan Stages')).toBeInTheDocument()
    expect(screen.getByText('Stage 4/4')).toBeInTheDocument()
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
        progressData={{ progress: 100 }}
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
        progressData={{ progress: 30, error: 'Connection timeout' }}
      />
    )
    expect(screen.getByText('Scan Failed')).toBeInTheDocument()
    // Error text appears in both the subtitle and the detail area
    expect(screen.getAllByText('Connection timeout').length).toBeGreaterThanOrEqual(1)
    // AlertCircle icon appears in both header and error details
    expect(screen.getAllByTestId('icon-alert').length).toBeGreaterThanOrEqual(1)
  })

  it('should call onComplete when complete and action button clicked', () => {
    const onComplete = vi.fn()
    render(
      <ScanProgressOverlay
        {...defaultProps}
        isComplete={true}
        progressData={{ progress: 100 }}
        onComplete={onComplete}
      />
    )

    const viewBtn = screen.getByText('View Results')
    fireEvent.click(viewBtn)

    expect(onComplete).toHaveBeenCalled()
  })

  it('should call onRetry when retry button clicked in failed state', () => {
    const onRetry = vi.fn()
    render(
      <ScanProgressOverlay
        {...defaultProps}
        hasFailed={true}
        progressData={{ progress: 30, error: 'Timeout' }}
        onRetry={onRetry}
      />
    )

    const retryBtn = screen.getByText('Retry Scan')
    fireEvent.click(retryBtn)

    expect(onRetry).toHaveBeenCalled()
  })

  it('should show resultSummary when provided', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        isComplete={true}
        progressData={{ progress: 100 }}
        resultSummary={{
          securityScore: 85,
          grade: 'B',
          severityCounts: { critical: 0, high: 1, medium: 3, low: 5 },
          filesScanned: 42,
          scanDuration: 120,
        }}
      />
    )
    // When no previousScore is provided, severity counts grid is shown
    expect(screen.getByText('critical')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()
    expect(screen.getByText('low')).toBeInTheDocument()
    expect(screen.getAllByText('Scan Complete').length).toBeGreaterThanOrEqual(1)
  })
})
