import { render, screen, within, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, it, expect, vi } from 'vitest'

import { clearProductConfigCache } from '../../hooks/useProductConfig'
import { api } from '../../lib/api'
import { Landing } from '../Landing'

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

describe('Landing Page', () => {
  beforeEach(() => {
    clearProductConfigCache()
    vi.mocked(api.get).mockResolvedValue({
      data: {
        beta_access_mode: false,
        checkout_enabled: true,
        show_upgrade_prompts: true,
        beta_label: null,
      },
    })
  })

  const renderLanding = () => {
    return render(
      <BrowserRouter>
        <Landing />
      </BrowserRouter>
    )
  }

  it('renders hero section with main heading', () => {
    renderLanding()
    const heroHeading = screen.getByRole('heading', { level: 1 })
    expect(heroHeading.textContent).toMatch(/secure your devops stack before production/i)
  })

  it('renders CTA buttons', () => {
    renderLanding()
    expect(screen.getAllByText(/Start Free Scan/i).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/Watch Demo/i)).toBeInTheDocument()
  })

  it('renders hero trust markers', () => {
    renderLanding()
    expect(screen.getByText('No credit card required')).toBeInTheDocument()
    expect(screen.getByText('Free tier available')).toBeInTheDocument()
    expect(screen.getByText('Instant results')).toBeInTheDocument()
  })

  it('renders architecture section with pipeline steps', () => {
    renderLanding()
    const sectionHeading = screen.getAllByRole('heading', { level: 2 })
      .find(h => /from repository to production readiness/i.test(h.textContent || ''))
    expect(sectionHeading).toBeDefined()
    // Six pipeline steps are rendered as level-3 headings
    expect(screen.getAllByRole('heading', { level: 3 }).length).toBeGreaterThanOrEqual(6)
    expect(screen.getByText('Connect Your Repository')).toBeInTheDocument()
    expect(screen.getByText('Technology Detection')).toBeInTheDocument()
    expect(screen.getByText('AI Security Scan')).toBeInTheDocument()
  })

  it('renders supported technologies section', () => {
    renderLanding()
    expect(screen.getAllByText('Docker').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Kubernetes').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Terraform').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('GitHub Actions').length).toBeGreaterThanOrEqual(1)
  })

  it('renders pricing plans', async () => {
    renderLanding()
    const pricing = within(document.getElementById('pricing') as HTMLElement)
    await waitFor(() => {
      expect(pricing.getByText('Free')).toBeInTheDocument()
    })
    expect(pricing.getByText('$0')).toBeInTheDocument()
    expect(pricing.getByText('Plus')).toBeInTheDocument()
    expect(pricing.getByText('$12')).toBeInTheDocument()
    expect(pricing.getByText('Pro')).toBeInTheDocument()
    expect(pricing.getByText('$29')).toBeInTheDocument()
    expect(pricing.getAllByText('Enterprise').length).toBeGreaterThanOrEqual(1)
    expect(pricing.getByText('Custom')).toBeInTheDocument()
  })

  it('renders final call-to-action section', () => {
    renderLanding()
    const ctaHeading = screen.getAllByRole('heading', { level: 2 })
      .find(h => /secure your pipeline/i.test(h.textContent || ''))
    expect(ctaHeading).toBeDefined()
    expect(screen.getByText(/See How It Works/i)).toBeInTheDocument()
  })

  it('has proper navigation header', () => {
    renderLanding()
    expect(screen.getAllByText(/DevArchAI/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Log In/i)).toBeInTheDocument()
  })

  it('renders live analysis demo', () => {
    renderLanding()
    expect(screen.getByText(/See It In Action/i)).toBeInTheDocument()
    expect(screen.getByText(/Live Product Demo/i)).toBeInTheDocument()
  })

  it('has a footer with compliance links', () => {
    renderLanding()
    expect(screen.getByText(/All rights reserved/i)).toBeInTheDocument()
    expect(screen.getByText('Documentation')).toBeInTheDocument()
    expect(screen.getAllByText('Acceptable Use').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Contact Support')).toBeInTheDocument()
  })
})
