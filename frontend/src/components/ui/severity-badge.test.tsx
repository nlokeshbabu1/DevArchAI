import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SeverityBadge } from '../components/ui/severity-badge'

describe('SeverityBadge', () => {
  it('renders critical severity', () => {
    render(<SeverityBadge severity="critical" />)
    
    expect(screen.getByText('Critical')).toBeInTheDocument()
  })

  it('renders high severity', () => {
    render(<SeverityBadge severity="high" />)
    
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('renders medium severity', () => {
    render(<SeverityBadge severity="medium" />)
    
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })

  it('renders low severity', () => {
    render(<SeverityBadge severity="low" />)
    
    expect(screen.getByText('Low')).toBeInTheDocument()
  })

  it('renders info severity', () => {
    render(<SeverityBadge severity="info" />)
    
    expect(screen.getByText('Info')).toBeInTheDocument()
  })

  it('shows icon by default', () => {
    render(<SeverityBadge severity="high" />)
    
    expect(screen.getByRole('img')).toBeInTheDocument()
  })

  it('hides icon when showIcon is false', () => {
    render(<SeverityBadge severity="high" showIcon={false} />)
    
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('applies size classes', () => {
    const { rerender } = render(<SeverityBadge severity="high" size="sm" />)
    expect(screen.getByText('High')).toHaveClass('text-xs')
    
    rerender(<SeverityBadge severity="high" size="md" />)
    expect(screen.getByText('High')).toHaveClass('text-sm')
    
    rerender(<SeverityBadge severity="high" size="lg" />)
    expect(screen.getByText('High')).toHaveClass('text-base')
  })
})
