import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ScanProgressOverlay } from '../scans/ScanProgressOverlay'

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
}))

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  repositoryName: 'myorg/my-repo',
  branch: 'main',
  progressData: { progress: 45, currentStep: 'Running Security Rules' },
  isComplete: false,
  hasFailed: false,
  onComplete: vi.fn(),
}

describe('ScanProgressOverlay', () => {
  test('renders progress percentage', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getAllByText('45%').length).toBeGreaterThanOrEqual(1)
  })

  test('shows Scan in Progress state', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('Scan in Progress')).toBeInTheDocument()
  })

  test('shows repository name and branch', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('myorg/my-repo')).toBeInTheDocument()
    expect(screen.getByText('main')).toBeInTheDocument()
  })

  test('shows Scan Complete with Close and Dismiss buttons', () => {
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
    expect(screen.getByText('Close')).toBeInTheDocument()
    expect(screen.getByText('Dismiss')).toBeInTheDocument()
  })

  test('shows score comparison when previousScore is provided', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        isComplete={true}
        progressData={{ progress: 100 }}
        previousScore={70}
        resultSummary={{
          securityScore: 85,
          grade: 'B',
          severityCounts: { critical: 0, high: 1, medium: 3, low: 5 },
          filesScanned: 42,
          scanDuration: 120,
        }}
      />
    )
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('+15')).toBeInTheDocument()
  })

  test('shows Scan Failed state with retry button', () => {
    render(
      <ScanProgressOverlay
        {...defaultProps}
        hasFailed={true}
        progressData={{ progress: 30, error: 'Connection timeout' }}
        onRetry={vi.fn()}
      />
    )
    expect(screen.getByText('Scan Failed')).toBeInTheDocument()
    expect(screen.getByText('Retry Scan')).toBeInTheDocument()
  })

  test('does not render when isOpen is false', () => {
    const { container } = render(
      <ScanProgressOverlay {...defaultProps} isOpen={false} />
    )
    expect(container.innerHTML).toBe('')
  })

  test('shows scan stages timeline', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('Scan Stages')).toBeInTheDocument()
    expect(screen.getByText('Cloning Repository')).toBeInTheDocument()
    expect(screen.getByText('Detecting Technologies')).toBeInTheDocument()
    expect(screen.getAllByText('Running Docker Rules').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Saving Findings')).toBeInTheDocument()
  })

  test('shows elapsed time', () => {
    render(<ScanProgressOverlay {...defaultProps} />)
    expect(screen.getByText('0:00')).toBeInTheDocument()
  })
})
