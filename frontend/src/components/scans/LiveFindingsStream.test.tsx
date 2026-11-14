import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import '@testing-library/jest-dom'
import type { LiveFinding } from '../../types'

import { LiveFindingsStream } from './LiveFindingsStream'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('../../lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

const makeFinding = (overrides: Partial<LiveFinding> = {}): LiveFinding => ({
  rule_id: 'R001',
  rule_name: 'Test Rule',
  severity: 'medium',
  category: 'security',
  description: 'A test finding description',
  timestamp: '2024-01-01T00:00:00Z',
  ...overrides,
})

describe('LiveFindingsStream', () => {
  it('should show empty state when no findings', () => {
    render(<LiveFindingsStream findings={[]} isVisible={true} />)

    expect(screen.getByText('Live Findings')).toBeInTheDocument()
    expect(screen.getByText('Waiting for findings…')).toBeInTheDocument()
  })

  it('should render findings', () => {
    const findings = [
      makeFinding({ rule_id: 'R001', rule_name: 'Hardcoded Secret' }),
      makeFinding({ rule_id: 'R002', rule_name: 'SQL Injection' }),
    ]

    render(<LiveFindingsStream findings={findings} isVisible={true} />)

    expect(screen.getByText('Hardcoded Secret')).toBeInTheDocument()
    expect(screen.getByText('SQL Injection')).toBeInTheDocument()
  })

  it('should show severity badges', () => {
    const findings = [
      makeFinding({ rule_id: 'R001', severity: 'critical' }),
      makeFinding({ rule_id: 'R002', severity: 'high' }),
      makeFinding({ rule_id: 'R003', severity: 'medium' }),
    ]

    render(<LiveFindingsStream findings={findings} isVisible={true} />)

    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })

  it('should limit to 20 findings', () => {
    const findings = Array.from({ length: 30 }, (_, i) =>
      makeFinding({ rule_id: `R${i}`, rule_name: `Rule ${i}` })
    )

    render(<LiveFindingsStream findings={findings} isVisible={true} />)

    expect(screen.getByText('Rule 10')).toBeInTheDocument()
    expect(screen.getByText('Rule 29')).toBeInTheDocument()
    expect(screen.queryByText('Rule 9')).not.toBeInTheDocument()
  })

  it('should not render when not visible', () => {
    const findings = [makeFinding()]

    const { container } = render(
      <LiveFindingsStream findings={findings} isVisible={false} />
    )

    expect(container.firstChild).toBeNull()
  })
})
