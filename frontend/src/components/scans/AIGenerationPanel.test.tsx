import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import '@testing-library/jest-dom'
import type { AIGenerationProgress } from '../../types'

import { AIGenerationPanel } from './AIGenerationPanel'

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
      phase: 'llm',
      message: 'Grouping findings by category',
      progress: 30,
      findings_processed: 5,
      findings_total: 20,
      timestamp: '2024-01-01T00:00:00Z',
    }

    render(<AIGenerationPanel aiProgress={aiProgress} isGenerating={true} />)

    expect(screen.getByText('AI Analysis')).toBeInTheDocument()
    expect(screen.getByText('Loading DevArchAI knowledge')).toBeInTheDocument()
    expect(screen.getByText('Checking documentation needs')).toBeInTheDocument()
    expect(screen.getByText('Fetching current documentation')).toBeInTheDocument()
    expect(screen.getByText('Generating AI recommendation')).toBeInTheDocument()
    expect(screen.getByText('AI recommendation ready')).toBeInTheDocument()
    expect(screen.getByText('Using cached recommendation')).toBeInTheDocument()
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
