import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import '@testing-library/jest-dom'
import type { ScannerStatus } from '../../types'

import { ScannerCards } from './ScannerCards'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('../../lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

describe('ScannerCards', () => {
  it('should show skeleton when no scanners', () => {
    render(<ScannerCards scanners={{}} detectedStack={[]} />)

    const skeletonCards = document.querySelectorAll('.animate-pulse')
    expect(skeletonCards.length).toBeGreaterThanOrEqual(1)
  })

  it('should render scanner cards', () => {
    const scanners: Record<string, ScannerStatus> = {
      hadolint: {
        scanner_id: 'hadolint',
        scanner_name: 'Docker',
        status: 'running',
        findings_count: 0,
      },
      gitleaks: {
        scanner_id: 'gitleaks',
        scanner_name: 'Secrets',
        status: 'pending',
        findings_count: 0,
      },
    }

    render(<ScannerCards scanners={scanners} detectedStack={[]} />)

    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('Dockerfile linting')).toBeInTheDocument()
    expect(screen.getByText('Secrets')).toBeInTheDocument()
    expect(screen.getByText('Secret detection')).toBeInTheDocument()
  })

  it('should show running status', () => {
    const scanners: Record<string, ScannerStatus> = {
      hadolint: {
        scanner_id: 'hadolint',
        scanner_name: 'Docker',
        status: 'running',
        findings_count: 0,
      },
    }

    render(<ScannerCards scanners={scanners} detectedStack={[]} />)

    const spinners = document.querySelectorAll('.animate-spin')
    expect(spinners.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Running')).toBeInTheDocument()
  })

  it('should show completed status', () => {
    const scanners: Record<string, ScannerStatus> = {
      gitleaks: {
        scanner_id: 'gitleaks',
        scanner_name: 'Secrets',
        status: 'completed_with_findings',
        findings_count: 3,
        duration_ms: 2500,
      },
    }

    render(<ScannerCards scanners={scanners} detectedStack={[]} />)

    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('3 findings')).toBeInTheDocument()
    expect(screen.getByText('2.5 sec')).toBeInTheDocument()
  })

  it('should show failed status', () => {
    const scanners: Record<string, ScannerStatus> = {
      checkov: {
        scanner_id: 'checkov',
        scanner_name: 'IaC',
        status: 'failed',
        findings_count: 0,
        error: 'Scanner crashed',
      },
    }

    render(<ScannerCards scanners={scanners} detectedStack={[]} />)

    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('Scanner crashed')).toBeInTheDocument()
  })

  it('should show detected technologies', () => {
    const scanners: Record<string, ScannerStatus> = {}
    const stack = ['Docker', 'Kubernetes', 'TypeScript']

    render(<ScannerCards scanners={scanners} detectedStack={stack} />)

    expect(screen.getByText('Detected')).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('Kubernetes')).toBeInTheDocument()
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
  })
})
