import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AIGenerationPanel } from './AIGenerationPanel'
import type { AIGenerationProgress } from '../../types'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('../../lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

describe('AIGenerationPanel', () => {
  it('should not render when not generating', () => {
    const { container } = render(
      <AIGenerationPanel aiProgress={null} isGenerating={false} />
    )

    expect(container.firstChild).toBeNull()
  })

  it('should show initializing state', () => {
    render(<AIGenerationPanel aiProgress={null} isGenerating={true} />)

    expect(screen.getByText('AI Analysis')).toBeInTheDocument()
    expect(screen.getByText('Initializing AI analysis...')).toBeInTheDocument()
  })

  it('should show AI phases', () => {
    const aiProgress: AIGenerationProgress = {
      phase: 'analyzing',
      message: 'Grouping findings by category',
      progress: 30,
      findings_processed: 5,
      findings_total: 20,
      timestamp: '2024-01-01T00:00:00Z',
    }

    render(<AIGenerationPanel aiProgress={aiProgress} isGenerating={true} />)

    expect(screen.getByText('AI Analysis')).toBeInTheDocument()
    expect(screen.getByText('Analyzing findings')).toBeInTheDocument()
    expect(screen.getByText('Finding root causes')).toBeInTheDocument()
    expect(screen.getByText('Generating remediations')).toBeInTheDocument()
    expect(screen.getByText('Calculating security score')).toBeInTheDocument()
    expect(screen.getByText('Generating executive summary')).toBeInTheDocument()
    expect(screen.getByText('Generating PR fixes')).toBeInTheDocument()
  })

  it('should show progress bar', () => {
    const aiProgress: AIGenerationProgress = {
      phase: 'root_causes',
      message: 'Identifying common patterns',
      progress: 50,
      findings_processed: 10,
      findings_total: 20,
      timestamp: '2024-01-01T00:00:00Z',
    }

    render(<AIGenerationPanel aiProgress={aiProgress} isGenerating={true} />)

    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.getAllByText('Identifying common patterns').length).toBeGreaterThanOrEqual(1)
  })

  it('should show findings count', () => {
    const aiProgress: AIGenerationProgress = {
      phase: 'remediations',
      message: 'Creating fix recommendations',
      progress: 60,
      findings_processed: 12,
      findings_total: 20,
      timestamp: '2024-01-01T00:00:00Z',
    }

    render(<AIGenerationPanel aiProgress={aiProgress} isGenerating={true} />)

    expect(
      screen.getByText('Analyzing 12 of 20 findings...')
    ).toBeInTheDocument()
  })
})
