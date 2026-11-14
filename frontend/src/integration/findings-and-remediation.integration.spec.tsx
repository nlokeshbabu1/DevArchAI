import '@testing-library/jest-dom'

import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FindingDetailsDrawer } from '../components/scan-results/FindingDetailsDrawer'
import type { Finding } from '../types'

import { sampleFindings } from './fixtures/findings'
import { renderWithProviders } from './test-utils'

describe('integration: finding details and remediation metadata', () => {
  it('renders remediation summary when processing_metadata is present', () => {
    const finding = sampleFindings[0] as unknown as Finding

    renderWithProviders(
      <FindingDetailsDrawer
        finding={finding}
        isOpen
        onClose={() => undefined}
        currentScore={72}
        onCopyFix={() => undefined}
        onDownloadPatch={() => undefined}
        onCreatePR={() => undefined}
      />,
    )

    expect(screen.getByLabelText('Finding details')).toBeInTheDocument()
    expect(screen.getByText(/non-root user/i)).toBeInTheDocument()
    expect(screen.getByText(/stored remediation patch/i)).toBeInTheDocument()
  })
})
