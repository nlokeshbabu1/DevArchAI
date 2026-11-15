import { motion, useInView } from 'framer-motion'
import {
  ArrowRight, Check, Shield, GitBranch, Search, Brain,
  GitPullRequest, FileText,
} from 'lucide-react'
import { useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

import { AIAssistantSection } from '../components/landing/AIAssistantSection'
import { BackgroundVideo } from '../components/landing/BackgroundVideo'
import { FAQ } from '../components/landing/FAQ'
import { HeroVideo } from '../components/landing/HeroVideo'
import { HeroProductPreview, LandingProductPreview } from '../components/landing/LandingProductPreview'
import { MagneticButton } from '../components/landing/MagneticButton'
import { Navbar } from '../components/landing/Navbar'
import { PlatformCapabilities } from '../components/landing/PlatformCapabilities'
import { PricingSection } from '../components/landing/PricingSection'
import { RepositoryIntegrationsSection } from '../components/landing/RepositoryIntegrationsSection'
import { SupportedTechnologiesSection } from '../components/landing/SupportedTechnologiesSection'
import { WhyDevArchAI } from '../components/landing/WhyDevArchAI'
import { Button } from '../components/ui-animated'
import { useProductConfigState } from '../hooks/useProductConfig'

function SectionDivider() {
  return <div className="h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
}

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] },
  }),
}

const storySteps = [
  {
    icon: GitBranch,
    title: 'Connect Your Repository',
    description: 'Sign up, then connect GitHub or GitLab — or start a scan from a public repository URL.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  {
    icon: Search,
    title: 'Technology Detection',
    description: 'DevArchAI detects Docker, Kubernetes, Terraform, CI/CD configs, and cloud-related files in the repo.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
  {
    icon: Shield,
    title: 'Security Scan',
    description: 'Registered scanners and policy rules surface misconfigurations, secrets, and dependency risks.',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
  },
  {
    icon: Brain,
    title: 'AI Fix Recommendations',
    description: 'Eligible findings receive RAG-backed remediation; informational items remain visible without LLM analysis.',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
  },
  {
    icon: GitPullRequest,
    title: 'Pull Request Creation',
    description: 'Where permissions allow, open PRs with suggested fixes from the dashboard.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
  {
    icon: FileText,
    title: 'Compliance Reports',
    description: 'Export findings and reports for audits within your plan limits.',
    color: 'text-primary',
    bg: 'bg-primary/10',
  },
]

function StoryStep({
  step, index, isLast,
}: {
  step: typeof storySteps[0]; index: number; isLast: boolean
}) {
  const Icon = step.icon
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <motion.div
      ref={ref}
      className="relative flex gap-6 pb-6"
      initial={{ opacity: 0, x: -20 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ delay: index * 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      {!isLast && (
        <div className="absolute left-6 top-14 bottom-0 w-px bg-gradient-to-b from-white/10 to-transparent" />
      )}
      <div className="relative flex-shrink-0">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border border-white/[0.06] ${step.bg}`}>
          <Icon className={`h-5 w-5 ${step.color}`} />
        </div>
        <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#0B1020] border-2 border-primary/40 flex items-center justify-center">
          <span className="text-[8px] font-bold text-primary">{index + 1}</span>
        </div>
      </div>
      <div className="flex-1 pt-1">
        <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:border-white/[0.1] transition-colors duration-300">
          <h3 className="text-base font-semibold text-white mb-1">{step.title}</h3>
          <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>
        </div>
      </div>
    </motion.div>
  )
}

export function Landing() {
  const navigate = useNavigate()
  const { config } = useProductConfigState()

  const handleStartScan = useCallback(() => {
    navigate('/register')
  }, [navigate])

  const trustMarkers = config.beta_access_mode
    ? ['Free access during Beta', 'No payment during Beta', 'Usage limits apply']
    : ['No credit card required', 'Free tier available', 'Instant results']

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#050814]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:left-4 focus:top-4 focus:rounded-lg focus:bg-primary focus:px-3 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>
      <BackgroundVideo />
      <div className="relative z-[1]">
        <Navbar />

        <main id="main-content">
          {/* Hero */}
          <section className="relative pt-24 pb-16 lg:pt-28 lg:pb-20 overflow-hidden">
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  'radial-gradient(ellipse 70% 55% at 50% 0%, rgba(124, 92, 255, 0.12), transparent 55%)',
              }}
              aria-hidden
            />

            <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
              <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                <div className="text-center lg:text-left">
                  <motion.div
                    custom={0}
                    variants={fadeUp}
                    initial="hidden"
                    animate="visible"
                    className="mb-6 flex justify-center lg:justify-start"
                  >
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm">
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
                      </span>
                      <span className="text-xs font-medium text-slate-400">
                        {config.beta_access_mode
                          ? config.beta_label || 'DevArchAI Beta — Free Access'
                          : 'Enterprise DevSecOps scanning'}
                      </span>
                    </div>
                  </motion.div>

                  <motion.h1
                    custom={1}
                    variants={fadeUp}
                    initial="hidden"
                    animate="visible"
                    className="display-xl text-white mb-6"
                  >
                    Secure your{' '}
                    <span className="gradient-text">DevOps stack</span>{' '}
                    before production.
                  </motion.h1>

                  <motion.p
                    custom={2}
                    variants={fadeUp}
                    initial="hidden"
                    animate="visible"
                    className="text-base sm:text-lg text-slate-400 leading-relaxed mb-8 max-w-xl mx-auto lg:mx-0"
                  >
                    Discover infrastructure misconfigurations, container risks and CI/CD security issues before they reach
                    production. Scan your repositories and get actionable AI-powered remediation.
                  </motion.p>

                  <motion.div
                    custom={3}
                    variants={fadeUp}
                    initial="hidden"
                    animate="visible"
                    className="flex flex-col sm:flex-row flex-wrap gap-3 mb-8 justify-center lg:justify-start"
                  >
                    <MagneticButton onClick={handleStartScan}>
                      <Button
                        variant="primary"
                        size="lg"
                        className="btn-premium h-[50px] px-7 text-sm font-semibold w-full sm:w-auto"
                      >
                        {config.beta_access_mode ? 'Join Beta — Free' : 'Start Free Scan'}
                        <ArrowRight className="h-4 w-4 ml-1.5" />
                      </Button>
                    </MagneticButton>
                    <Button
                      variant="secondary"
                      size="lg"
                      onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                      className="btn-secondary-premium h-[50px] px-7 text-sm font-semibold w-full sm:w-auto"
                    >
                      Explore Features
                    </Button>
                  </motion.div>

                  <motion.p
                    custom={3}
                    variants={fadeUp}
                    initial="hidden"
                    animate="visible"
                    className="text-xs text-slate-500 mb-4 text-center lg:text-left"
                  >
                    Registration required to connect private repositories and save scan history.
                  </motion.p>

                  <motion.div
                    custom={4}
                    variants={fadeUp}
                    initial="hidden"
                    animate="visible"
                    className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-400 justify-center lg:justify-start"
                  >
                    {trustMarkers.map((item) => (
                      <div key={item} className="flex items-center gap-2">
                        <Check className="h-3.5 w-3.5 text-emerald-400/80" aria-hidden />
                        <span>{item}</span>
                      </div>
                    ))}
                  </motion.div>
                </div>

                <HeroProductPreview />
              </div>
            </div>
          </section>

          <SectionDivider />

          <SupportedTechnologiesSection />
          <SectionDivider />

          <LandingProductPreview />
          <SectionDivider />

          <span id="features">
            <PlatformCapabilities />
          </span>
          <SectionDivider />

          <div className="py-6">
            <WhyDevArchAI />
          </div>
          <SectionDivider />

          <section id="how-it-works" className="py-16 lg:py-24 scroll-mt-20">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
              <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
                <div className="lg:sticky lg:top-24">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <p className="text-sm font-medium text-primary mb-3">How it works</p>
                    <h2 className="display-lg text-white mb-4">
                      From repository to production readiness
                    </h2>
                    <p className="text-base text-slate-400 max-w-lg leading-relaxed">
                      One scan runs detection, policy checks, and optional AI remediation. Results appear as soon as the
                      security phase completes.
                    </p>
                  </motion.div>
                </div>
                <div className="relative">
                  {storySteps.map((step, index) => (
                    <StoryStep
                      key={step.title}
                      step={step}
                      index={index}
                      isLast={index === storySteps.length - 1}
                    />
                  ))}
                </div>
              </div>
            </div>
          </section>
          <SectionDivider />

          <AIAssistantSection />
          <SectionDivider />

          <RepositoryIntegrationsSection />
          <SectionDivider />

          <section id="live-demo" className="relative py-16 lg:py-20 overflow-hidden scroll-mt-20">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
              <div className="text-center mb-10 space-y-3 max-w-2xl mx-auto">
                <h2 className="display-lg text-white">Walkthrough</h2>
                <p className="text-base text-slate-400">
                  Optional video overview of the scan flow — the in-app UI above reflects the live product.
                </p>
              </div>
              <div className="max-w-4xl mx-auto rounded-2xl border border-white/[0.08] bg-[#0a0f1e]/80 backdrop-blur-md overflow-hidden">
                <HeroVideo />
              </div>
            </div>
          </section>
          <SectionDivider />

          <section id="pricing" className="scroll-mt-20">
            <PricingSection />
          </section>
          <SectionDivider />

          <div id="faq">
            <FAQ />
          </div>
          <SectionDivider />

          <section className="py-16 lg:py-24 relative overflow-hidden">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
              <motion.div
                className="max-w-3xl mx-auto text-center"
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              >
                <h2 className="display-lg text-white mb-4">
                  Secure your pipeline{' '}
                  <span className="gradient-text">today</span>
                </h2>
                <p className="text-base text-slate-400 max-w-xl mx-auto leading-relaxed mb-6">
                  Detect vulnerabilities, secrets, and misconfigurations before deployment.
                </p>
                <div className="flex flex-row flex-wrap gap-3 justify-center">
                  <MagneticButton onClick={() => navigate('/register')}>
                    <Button variant="primary" size="lg" className="btn-premium h-[50px] px-7 text-sm font-semibold">
                      Start Free Scan
                      <ArrowRight className="h-4 w-4 ml-1.5" />
                    </Button>
                  </MagneticButton>
                  <Button
                    variant="secondary"
                    size="lg"
                    onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
                    className="btn-secondary-premium h-[50px] px-7 text-sm font-semibold"
                  >
                    See How It Works
                  </Button>
                </div>
              </motion.div>
            </div>
          </section>
        </main>

        <footer
          className="border-t border-white/[0.06] py-10 pb-[max(2.5rem,env(safe-area-inset-bottom))]"
          role="contentinfo"
        >
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
              <div className="col-span-2 md:col-span-1">
                <div className="flex items-center gap-2 mb-3">
                  <div className="flex items-center justify-center w-7 h-7 rounded-md bg-primary/10 border border-primary/20">
                    <Shield className="h-3.5 w-3.5 text-primary" aria-hidden />
                  </div>
                  <span className="text-sm font-semibold text-white">DevArchAI</span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
                  AI-assisted DevOps security scanning for infrastructure-as-code and repositories.
                </p>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Product</h4>
                <ul className="space-y-1 text-sm text-slate-400">
                  <li><a href="#features" className="block py-1.5 hover:text-white transition-colors">Features</a></li>
                  <li><a href="#technologies" className="block py-1.5 hover:text-white transition-colors">Technologies</a></li>
                  <li><a href="#pricing" className="block py-1.5 hover:text-white transition-colors">Pricing</a></li>
                  <li><a href="#how-it-works" className="block py-1.5 hover:text-white transition-colors">How it works</a></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Resources</h4>
                <ul className="space-y-1 text-sm text-slate-400">
                  <li><a href="/docs" className="block py-1.5 hover:text-white transition-colors">Documentation</a></li>
                  <li><a href="/docs/ai-recommendations" className="block py-1.5 hover:text-white transition-colors">AI Recommendations</a></li>
                  <li><a href="#faq" className="block py-1.5 hover:text-white transition-colors">FAQ</a></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Company</h4>
                <ul className="space-y-1 text-sm text-slate-400">
                  <li><a href="mailto:support@devarchai.com" className="block py-1.5 hover:text-white transition-colors">Contact</a></li>
                  <li><a href="/docs/getting-started" className="block py-1.5 hover:text-white transition-colors">Acceptable Use</a></li>
                </ul>
              </div>
            </div>
            <div className="border-t border-white/[0.06] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-xs text-slate-400">
                &copy; {new Date().getFullYear()} DevArchAI. All rights reserved.
              </p>
              <div className="flex items-center gap-4 text-xs text-slate-400">
                <a href="/docs/getting-started" className="hover:text-white transition-colors py-1">Acceptable Use</a>
                <a href="mailto:support@devarchai.com" className="hover:text-white transition-colors py-1">Contact Support</a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}