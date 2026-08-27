import { useCallback, useRef, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useInView, useMotionValue, useSpring } from 'framer-motion'
import {
  ArrowRight, Check, Shield, GitBranch, Search, Brain,
  GitPullRequest, FileText, Play, ChevronDown
} from 'lucide-react'
import { Button } from '../components/ui-animated'
import { MagneticButton } from '../components/landing/MagneticButton'
import { Navbar } from '../components/landing/Navbar'
import { HeroVideo } from '../components/landing/HeroVideo'
import { FloatingTechCards } from '../components/landing/FloatingTechCards'
import { TechnologyMarquee } from '../components/landing/TechnologyMarquee'
import { WhyDevArchAI } from '../components/landing/WhyDevArchAI'
import { PricingSection } from '../components/landing/PricingSection'
import { BackgroundVideo } from '../components/landing/BackgroundVideo'

/* ─── Mouse Glow ───────────────────────────────────────────── */
function MouseGlow() {
  const [visible, setVisible] = useState(false)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springX = useSpring(x, { stiffness: 150, damping: 25 })
  const springY = useSpring(y, { stiffness: 150, damping: 25 })

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      if (!visible) setVisible(true)
      x.set(e.clientX)
      y.set(e.clientY)
    }
    const handleLeave = () => setVisible(false)
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseleave', handleLeave)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseleave', handleLeave)
    }
  }, [visible, x, y])

  return (
    <motion.div
      className="fixed pointer-events-none z-[9999] mix-blend-screen hidden lg:block"
      style={{
        x: springX,
        y: springY,
        translateX: '-50%',
        translateY: '-50%',
        width: 600,
        height: 600,
        opacity: visible ? 1 : 0,
        background: 'radial-gradient(circle, rgba(99, 102, 241, 0.04) 0%, rgba(139, 92, 246, 0.02) 30%, transparent 70%)',
      }}
      aria-hidden="true"
    />
  )
}

/* ─── Section Divider ─────────────────────────────────────── */
function SectionDivider() {
  return (
    <div className="relative">
      <div className="h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
    </div>
  )
}

/* ─── Fade Up Variants ────────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] },
  }),
}

/* ─── Story Steps ─────────────────────────────────────────── */
const storySteps = [
  {
    icon: GitBranch,
    title: 'Connect Your Repository',
    description: 'Point to any GitHub, GitLab, or Bitbucket repository. No complex setup — just a URL.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  {
    icon: Search,
    title: 'Technology Detection',
    description: 'Our engine automatically identifies Docker, Kubernetes, Terraform, CI/CD, and cloud configurations.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
  {
    icon: Shield,
    title: 'AI Security Scan',
    description: '500+ security rules scan for vulnerabilities, secrets, misconfigurations, and compliance gaps.',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
  },
  {
    icon: Brain,
    title: 'AI Fix Recommendations',
    description: 'Every finding includes production-ready code fixes with best practices and documentation.',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
  },
  {
    icon: GitPullRequest,
    title: 'Pull Request Creation',
    description: 'Automated PRs with inline fix suggestions, ready to merge into your codebase.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
  {
    icon: FileText,
    title: 'Compliance Reports',
    description: 'Download PDF, Excel, or JSON reports for SOC 2, HIPAA, and PCI-DSS compliance.',
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

/* ─── Main Landing ────────────────────────────────────────── */
export function Landing() {
  const navigate = useNavigate()

  const handleStartScan = useCallback(() => {
    navigate('/register')
  }, [navigate])

  return (
    <div className="min-h-screen overflow-x-hidden">
      <BackgroundVideo />
      <div className="relative z-[1]">
        <MouseGlow />
        <Navbar />

        {/* ===== HERO ===== */}
        <section className="relative min-h-[calc(100vh-4rem)] flex items-center overflow-hidden">

          <FloatingTechCards />

          {/* Hero ambient glows — depth layers */}
          <div className="absolute top-[12%] left-1/2 -translate-x-1/2 w-[44rem] h-80 bg-primary/[0.09] rounded-full blur-[130px] pointer-events-none" />
          <div className="absolute bottom-[14%] right-[10%] w-[30rem] h-72 bg-blue-500/[0.07] rounded-full blur-[120px] pointer-events-none" />
          <div className="absolute top-[24%] left-[6%] w-80 h-80 bg-primary/[0.04] rounded-full blur-[110px] pointer-events-none" />
          {/* Very soft volumetric light */}
          <div
            className="absolute top-[-12%] left-[28%] w-48 h-[140%] pointer-events-none"
            style={{ background: 'linear-gradient(to bottom, rgba(124, 92, 255, 0.05), transparent 70%)', transform: 'rotate(16deg)' }}
          />

          {/* Centered radial glow behind headline for contrast */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse 60% 50% at 50% 40%, rgba(3, 0, 15, 0.5) 0%, rgba(3, 0, 15, 0.25) 55%, transparent 100%)',
            }}
          />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 py-20 lg:py-0">
            <div className="max-w-3xl mx-auto text-center">
              <motion.div
                  custom={0}
                  variants={fadeUp}
                  initial="hidden"
                  animate="visible"
                  className="mb-6"
                >
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-400" />
                    </span>
                    <span className="text-xs font-medium text-slate-400">DevSecOps Security Platform</span>
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
                  before production
                </motion.h1>

                <motion.p
                  custom={2}
                  variants={fadeUp}
                  initial="hidden"
                  animate="visible"
                  className="text-base sm:text-lg text-slate-400 leading-relaxed mb-10 max-w-[600px] mx-auto"
                >
                  Scan Terraform, Kubernetes, Helm, Docker, GitHub Actions, GitLab CI, and Jenkins pipelines.
                  Get AI-powered remediation with RAG security knowledge and live documentation when needed.
                </motion.p>

                <motion.div
                  custom={3}
                  variants={fadeUp}
                  initial="hidden"
                  animate="visible"
                  className="flex flex-row flex-wrap gap-3 mb-10 justify-center"
                >
                  <MagneticButton onClick={handleStartScan}>
                    <Button
                      variant="primary"
                      size="lg"
                      className="btn-premium h-[50px] px-7 text-sm font-semibold"
                    >
                      Start Free Scan
                      <ArrowRight className="h-4 w-4 ml-1.5" />
                    </Button>
                  </MagneticButton>
                  <Button
                    variant="secondary"
                    size="lg"
                    onClick={() => document.getElementById('live-demo')?.scrollIntoView({ behavior: 'smooth' })}
                    className="btn-secondary-premium h-[50px] px-7 text-sm font-semibold"
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    Watch Demo
                  </Button>
                </motion.div>

                <motion.div
                  custom={4}
                  variants={fadeUp}
                  initial="hidden"
                  animate="visible"
                  className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-400 justify-center"
                >
                  {['No credit card required', 'Free tier available', 'Instant results'].map((item) => (
                    <div key={item} className="flex items-center gap-2">
                      <Check className="h-3.5 w-3.5 text-green-400/80" />
                      <span>{item}</span>
                    </div>
                  ))}
                </motion.div>
            </div>
          </div>

          {/* Scroll indicator */}
          <motion.div
            className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 z-10"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.5, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-widest">Scroll to explore</span>
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
            >
              <ChevronDown className="h-4 w-4 text-slate-500" />
            </motion.div>
          </motion.div>
        </section>

        {/* ===== LIVE PRODUCT DEMO ===== */}
        <section id="live-demo" className="relative py-12 lg:py-16 overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <motion.div
              className="text-center mb-10 space-y-3"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20 mb-4 backdrop-blur-sm">
                <Play className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary/90">See It In Action</span>
              </div>
              <h2 className="display-lg text-white">
                Live Product Demo
              </h2>
              <p className="text-base text-slate-400 max-w-2xl mx-auto">
                Watch DevArchAI scan a real repository — from import through Docker, Kubernetes, Terraform, and CI/CD analysis to AI-powered report generation
              </p>
            </motion.div>

            <motion.div
              className="max-w-4xl mx-auto"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="relative rounded-2xl border border-white/[0.08] bg-[#0a0f1e]/80 backdrop-blur-md overflow-hidden shadow-[0_0_80px_-16px_rgba(99,102,241,0.1)]">
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                <HeroVideo />
              </div>
            </motion.div>
          </div>
        </section>
        <SectionDivider />

        {/* ===== TECHNOLOGY MARQUEE ===== */}
        <TechnologyMarquee />

        {/* ===== TECHNOLOGY COVERAGE ===== */}
        <section className="py-10 lg:py-14">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto text-center mb-8">
              <h2 className="text-lg font-semibold text-white mb-2">What DevArchAI scans</h2>
              <p className="text-sm text-slate-400">
                Repository and infrastructure-as-code security — clearly separated from cloud posture (AWS available today).
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2 max-w-4xl mx-auto">
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-3">Available now</p>
                <ul className="grid grid-cols-2 gap-2 text-sm text-slate-300">
                  {['Terraform', 'Kubernetes', 'Helm', 'Docker', 'GitHub Actions', 'GitLab CI', 'Jenkins', 'AWS Cloud'].map((tech) => (
                    <li key={tech} className="flex items-center gap-2">
                      <Check className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                      {tech}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/[0.04] p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-3">Coming soon</p>
                <ul className="grid grid-cols-2 gap-2 text-sm text-slate-400">
                  {['Azure DevOps', 'Azure Cloud', 'GCP Cloud', 'Bitbucket', 'Pulumi', 'Ansible'].map((tech) => (
                    <li key={tech} className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-indigo-400/60 shrink-0" />
                      {tech}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>
        <SectionDivider />

        {/* ===== FEATURES (Why DevArchAI) ===== */}
        <div id="features">
          <WhyDevArchAI />
        </div>
        <SectionDivider />

        {/* ===== ARCHITECTURE (How It Works) ===== */}
        <section id="how-it-works" className="py-12 lg:py-16">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
              <div className="lg:sticky lg:top-24">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                >
                  <p className="text-sm font-medium text-primary mb-3">Architecture</p>
                  <h2 className="display-lg text-white mb-4">
                    From repository to production readiness
                  </h2>
                  <p className="text-base text-slate-400 max-w-lg leading-relaxed">
                    A single scan triggers a comprehensive analysis pipeline. Every step is automated.
                    You get actionable results in under 30 seconds.
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

        {/* ===== PRICING ===== */}
        <section id="pricing">
          <PricingSection />
        </section>
        <SectionDivider />

        {/* ===== FINAL CTA ===== */}
        <section className="py-16 lg:py-24 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <motion.div
              className="max-w-3xl mx-auto text-center"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="space-y-5">
                <h2 className="display-lg text-white">
                  Secure your pipeline{' '}
                  <span className="gradient-text">today</span>
                </h2>
                <p className="text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
                  Detect vulnerabilities, secrets, infrastructure risks, and CI/CD issues before deployment.
                  Start scanning in under 30 seconds.
                </p>
                <div className="flex flex-row flex-wrap gap-3 justify-center pt-2">
                  <MagneticButton onClick={() => navigate('/register')}>
                    <Button
                      variant="primary"
                      size="lg"
                      className="btn-premium h-[50px] px-7 text-sm font-semibold"
                    >
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
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    See How It Works
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ===== FOOTER ===== */}
        <footer
          className="border-t border-white/[0.06] py-10 pb-[max(2.5rem,env(safe-area-inset-bottom))]"
          role="contentinfo"
        >
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
              <div className="col-span-2 md:col-span-1">
                <div className="flex items-center gap-2 mb-3">
                  <div className="flex items-center justify-center w-7 h-7 rounded-md bg-primary/10 border border-primary/20">
                    <Shield className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <span className="text-sm font-semibold text-white">DevArchAI</span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
                  AI-powered DevOps security scanning for infrastructure-as-code.
                </p>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Product</h4>
                <ul className="space-y-1 text-sm text-slate-400">
                  <li><a href="#features" className="block py-1.5 hover:text-white transition-colors">Features</a></li>
                  <li><a href="#pricing" className="block py-1.5 hover:text-white transition-colors">Pricing</a></li>
                  <li><a href="#how-it-works" className="block py-1.5 hover:text-white transition-colors">Architecture</a></li>
                  <li><a href="#live-demo" className="block py-1.5 hover:text-white transition-colors">Demo</a></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Resources</h4>
                <ul className="space-y-1 text-sm text-slate-400">
                  <li><a href="/docs" className="block py-1.5 hover:text-white transition-colors">Documentation</a></li>
                  <li><a href="/docs/ai-recommendations" className="block py-1.5 hover:text-white transition-colors">AI Recommendations</a></li>
                  <li><span className="block py-1.5 text-slate-500">Blog — Coming Soon</span></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Company</h4>
                <ul className="space-y-1 text-sm text-slate-400">
                  <li><a href="mailto:support@devarchai.com" className="block py-1.5 hover:text-white transition-colors">Contact</a></li>
                  <li><a href="/docs/getting-started" className="block py-1.5 hover:text-white transition-colors">Acceptable Use</a></li>
                  <li><span className="block py-1.5 text-slate-500">About — Coming Soon</span></li>
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
