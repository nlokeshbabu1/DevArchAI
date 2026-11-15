import { motion, AnimatePresence } from 'framer-motion'
import { Shield, ArrowRight, Menu, X } from 'lucide-react'
import { useState, useEffect, useCallback, useRef, memo } from 'react'
import { useNavigate } from 'react-router-dom'

import { useProductConfigState } from '../../hooks/useProductConfig'
import { Button } from '../ui-animated'


const navLinksBase = [
  { label: 'Features', href: '#features' },
  { label: 'Supported Technologies', href: '#technologies' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Pricing', href: '#pricing', labelBeta: 'Beta Access' },
] as const

const NavItem = memo(function NavItem({
  label, href, onClick,
}: {
  label: string; href?: string; onClick?: () => void
}) {
  return (
    <a
      href={href}
      onClick={onClick}
      className="px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors duration-200 rounded-lg hover:bg-white/[0.04]"
    >
      {label}
    </a>
  )
})

export function Navbar() {
  const navigate = useNavigate()
  const { config } = useProductConfigState()
  const navLinks = navLinksBase.map((link) => ({
    ...link,
    label: config.beta_access_mode && 'labelBeta' in link ? link.labelBeta : link.label,
  }))
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const mobileMenuRef = useRef<HTMLDivElement>(null)
  const menuButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Body scroll lock when mobile menu is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.classList.add('menu-open')
    } else {
      document.body.classList.remove('menu-open')
    }
    return () => document.body.classList.remove('menu-open')
  }, [mobileOpen])

  // Keyboard: Escape to close mobile menu
  useEffect(() => {
    if (!mobileOpen) {return}
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileOpen(false)
        menuButtonRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [mobileOpen])

  // Focus trap inside mobile menu
  useEffect(() => {
    if (!mobileOpen || !mobileMenuRef.current) {return}
    const focusableSelector = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
    const focusable = mobileMenuRef.current.querySelectorAll<HTMLElement>(focusableSelector)
    if (focusable.length === 0) {return}

    // Focus first element when menu opens
    focusable[0]?.focus()

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') {return}
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', handleTab)
    return () => document.removeEventListener('keydown', handleTab)
  }, [mobileOpen])

  const handleNavClick = useCallback((href: string) => {
    setMobileOpen(false)
    const el = document.querySelector(href)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }, [])

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'glass-nav-solid border-b border-white/[0.06]' : 'glass-nav'
      }`}
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <motion.div
            className="flex items-center gap-2.5"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 border border-primary/20">
              <Shield className="h-4 w-4 text-primary" />
            </div>
            <span className="text-base font-semibold text-white tracking-tight">DevArchAI</span>
          </motion.div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-0.5" role="navigation" aria-label="Main navigation">
            {navLinks.map((link) => (
              <NavItem
                key={link.label}
                label={link.label}
                href={link.href}
                onClick={() => handleNavClick(link.href)}
              />
            ))}
          </nav>

          {/* Desktop Actions */}
          <motion.div
            className="hidden md:flex items-center gap-2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
          >
            <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
              Log In
            </Button>
            <Button variant="primary" size="sm" className="btn-premium" onClick={() => navigate('/register')}>
              Start Free Scan
              <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </motion.div>

          {/* Mobile Menu Button — 44x44px touch target */}
          <button
            ref={menuButtonRef}
            className="md:hidden relative w-11 h-11 flex items-center justify-center text-slate-400 hover:text-white transition-colors rounded-lg"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
            aria-controls="mobile-menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu with backdrop blur */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="md:hidden fixed inset-0 top-16 bg-black/40 backdrop-blur-sm z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setMobileOpen(false)}
              aria-hidden="true"
            />
            {/* Menu panel */}
            <motion.div
              ref={mobileMenuRef}
              id="mobile-menu"
              role="dialog"
              aria-label="Mobile navigation"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="md:hidden relative z-50 border-t border-white/[0.06] bg-[#0B1020]/95 backdrop-blur-xl"
            >
              <div className="container mx-auto px-4 py-4 space-y-1">
                {navLinks.map((link) => (
                  <a
                    key={link.label}
                    href={link.href}
                    onClick={() => handleNavClick(link.href)}
                    className="block px-3 py-3 text-sm text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-white/[0.04] touch-target"
                  >
                    {link.label}
                  </a>
                ))}
                <div className="pt-3 border-t border-white/[0.06] space-y-2">
                  <Button variant="ghost" size="sm" className="w-full touch-target" onClick={() => { navigate('/login'); setMobileOpen(false) }}>
                    Log In
                  </Button>
                  <Button variant="primary" size="sm" className="w-full btn-premium touch-target" onClick={() => { navigate('/register'); setMobileOpen(false) }}>
                    Start Free Scan
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </header>
  )
}
