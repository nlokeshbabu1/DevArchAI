import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ScanPipeline } from './ScanPipeline'
import type { ScanStage, StageMetadata } from '../../types'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

vi.mock('../../lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

const canonicalStages: StageMetadata[] = [
  { id: 'connecting_repository', label: 'Connecting', icon: 'globe', order: 0, kind: 'base' },
  { id: 'cloning', label: 'Cloning', icon: 'download', order: 1, kind: 'base' },
  { id: 'detecting_technologies', label: 'Detecting', icon: 'cpu', order: 2, kind: 'base' },
  { id: 'scanning', label: 'Scanning', icon: 'shield', order: 3, kind: 'base' },
  { id: 'analyzing', label: 'Analyzing', icon: 'brain', order: 4, kind: 'base' },
]

describe('ScanPipeline', () => {
  const defaultProps = {
    stages: canonicalStages,
    currentStage: null as ScanStage | null,
    completedStages: [] as ScanStage[],
    failedStages: [] as ScanStage[],
    progress: 0,
    isComplete: false,
    hasFailed: false,
  }

  it('should render lifecycle stages', () => {
    render(<ScanPipeline {...defaultProps} />)
    expect(screen.getByText('Connecting')).toBeInTheDocument()
    expect(screen.getByText('Cloning')).toBeInTheDocument()
    expect(screen.getByText('Scanning')).toBeInTheDocument()
  })

  it('should show completed checkmarks', () => {
    render(
      <ScanPipeline
        {...defaultProps}
        completedStages={['connecting_repository', 'cloning']}
      />,
    )
    const svgElements = document.querySelectorAll('svg')
    const checkCircles = Array.from(svgElements).filter(
      (el) => el.classList?.contains?.('text-emerald-400') || el.closest('[class*="emerald"]'),
    )
    expect(checkCircles.length).toBeGreaterThanOrEqual(2)
  })

  it('should show spinner for active stage', () => {
    render(<ScanPipeline {...defaultProps} currentStage="scanning" />)
    const blueIcons = document.querySelectorAll('.text-indigo-400')
    expect(blueIcons.length).toBeGreaterThanOrEqual(1)
  })

  it('should show failed X', () => {
    render(<ScanPipeline {...defaultProps} failedStages={['analyzing']} />)
    const svgElements = document.querySelectorAll('svg')
    const redIcons = Array.from(svgElements).filter(
      (el) => el.classList?.contains?.('text-red-400') || el.closest('[class*="red"]'),
    )
    expect(redIcons.length).toBeGreaterThanOrEqual(1)
  })

  it('should show progress bar when enabled', () => {
    render(<ScanPipeline {...defaultProps} progress={65} showProgressBar />)
    expect(screen.getByText('65%')).toBeInTheDocument()
  })

  it('should handle empty stages', () => {
    render(<ScanPipeline {...defaultProps} stages={[]} showProgressBar />)
    expect(screen.getByRole('list', { name: 'Scan pipeline progress' })).toBeInTheDocument()
  })
})
