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

const makeStages = (count: number): StageMetadata[] =>
  Array.from({ length: count }, (_, i) => ({
    id: `stage_${i}` as ScanStage,
    label: `Stage ${i}`,
    icon: 'circle',
    order: i,
  }))

describe('ScanPipeline', () => {
  const defaultProps = {
    stages: makeStages(3),
    currentStage: null,
    completedStages: [],
    failedStages: [],
    progress: 0,
    isComplete: false,
    hasFailed: false,
  }

  it('should render all stages', () => {
    const stages = makeStages(4)
    render(<ScanPipeline {...defaultProps} stages={stages} />)

    expect(screen.getByText('Stage 0')).toBeInTheDocument()
    expect(screen.getByText('Stage 1')).toBeInTheDocument()
    expect(screen.getByText('Stage 2')).toBeInTheDocument()
    expect(screen.getByText('Stage 3')).toBeInTheDocument()
  })

  it('should show completed checkmarks', () => {
    const stages = makeStages(3)
    render(
      <ScanPipeline
        {...defaultProps}
        stages={stages}
        completedStages={['stage_0', 'stage_1']}
      />
    )

    const svgElements = document.querySelectorAll('svg')
    const checkCircles = Array.from(svgElements).filter(
      (el) => el.classList?.contains?.('text-emerald-400') || el.closest('[class*="emerald"]')
    )
    expect(checkCircles.length).toBeGreaterThanOrEqual(2)
  })

  it('should show spinner for active stage', () => {
    const stages = makeStages(3)
    render(
      <ScanPipeline
        {...defaultProps}
        stages={stages}
        currentStage="stage_1"
      />
    )

    const blueIcons = document.querySelectorAll('.text-blue-400')
    expect(blueIcons.length).toBeGreaterThanOrEqual(1)
  })

  it('should show failed X', () => {
    const stages = makeStages(3)
    render(
      <ScanPipeline
        {...defaultProps}
        stages={stages}
        failedStages={['stage_2']}
      />
    )

    const svgElements = document.querySelectorAll('svg')
    const redIcons = Array.from(svgElements).filter(
      (el) => el.classList?.contains?.('text-red-400') || el.closest('[class*="red"]')
    )
    expect(redIcons.length).toBeGreaterThanOrEqual(1)
  })

  it('should show progress bar', () => {
    render(<ScanPipeline {...defaultProps} progress={65} />)

    expect(screen.getByText('65%')).toBeInTheDocument()
  })

  it('should handle empty stages', () => {
    render(<ScanPipeline {...defaultProps} stages={[]} />)

    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})
