import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { Landing } from '../Landing'

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

describe('Landing Page', () => {
  const renderLanding = () => {
    return render(
      <BrowserRouter>
        <Landing />
      </BrowserRouter>
    )
  }

  it('renders hero section with main heading', () => {
    renderLanding()
    expect(screen.getByText(/Secure Your DevOps/i)).toBeInTheDocument()
    expect(screen.getByText(/Before Production/i)).toBeInTheDocument()
  })

  it('renders CTA buttons', () => {
    renderLanding()
    expect(screen.getByText(/Start Free Scan/i)).toBeInTheDocument()
    expect(screen.getByText(/Watch Demo/i)).toBeInTheDocument()
  })

  it('renders stats section', () => {
    renderLanding()
    expect(screen.getByText(/10,000\+/i)).toBeInTheDocument()
    expect(screen.getByText(/500\+/i)).toBeInTheDocument()
    expect(screen.getByText(/< 30s/i)).toBeInTheDocument()
    expect(screen.getByText(/99\.9%/i)).toBeInTheDocument()
  })

  it('renders how it works section with 5 steps', () => {
    renderLanding()
    expect(screen.getByText(/How DevArchAI Works/i)).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 }).length).toBeGreaterThanOrEqual(5)
  })

  it('renders supported technologies section', () => {
    renderLanding()
    expect(screen.getByText(/Docker/i)).toBeInTheDocument()
    expect(screen.getByText(/Kubernetes/i)).toBeInTheDocument()
    expect(screen.getByText(/Terraform/i)).toBeInTheDocument()
    expect(screen.getByText(/GitHub Actions/i)).toBeInTheDocument()
  })

  it('renders pricing plans', () => {
    renderLanding()
    expect(screen.getByText(/Free/i)).toBeInTheDocument()
    expect(screen.getByText(/Pro/i)).toBeInTheDocument()
    expect(screen.getByText(/Team/i)).toBeInTheDocument()
    expect(screen.getByText(/\$29/i)).toBeInTheDocument()
    expect(screen.getByText(/\$99/i)).toBeInTheDocument()
  })

  it('renders testimonials section', () => {
    renderLanding()
    expect(screen.getByText(/Loved by DevOps Teams/i)).toBeInTheDocument()
  })

  it('has proper navigation header', () => {
    renderLanding()
    expect(screen.getByText(/DevArchAI/i)).toBeInTheDocument()
    expect(screen.getByText(/Login/i)).toBeInTheDocument()
    expect(screen.getByText(/Get Started/i)).toBeInTheDocument()
  })

  it('renders live analysis demo', () => {
    renderLanding()
    expect(screen.getByText(/See It In Action/i)).toBeInTheDocument()
    expect(screen.getByText(/Live Analysis Demo/i)).toBeInTheDocument()
  })
})
