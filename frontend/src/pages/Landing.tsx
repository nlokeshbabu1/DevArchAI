import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Shield, Zap, GitBranch, BarChart3, Sparkles, Check, ArrowRight,
  Github, FileCode, Brain, Rocket, Server, Cloud, Lock, Layers,
  Terminal, Database, ChevronRight, Star, Users, Globe, Play
} from 'lucide-react'
import { Button, Card } from '../components/ui'
import { cn } from '../lib/utils'
import { useState, useEffect } from 'react'
import { ScanningAnimation } from '../components/ui/LoadingAnimation'
import { LandingScanner } from '../components/scanner/LandingScanner'

const technologies = [
  { name: 'Docker', icon: Terminal, description: 'Container security scanning' },
  { name: 'Kubernetes', icon: Cloud, description: 'K8s manifest analysis' },
  { name: 'Terraform', icon: Layers, description: 'IaC security checks' },
  { name: 'GitHub Actions', icon: Github, description: 'CI/CD pipeline security' },
  { name: 'AWS', icon: Server, description: 'Cloud infrastructure' },
  { name: 'Azure', icon: Cloud, description: 'Cloud security' },
]

const pricingPlans = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Perfect for getting started',
    features: [
      '3 scans per month',
      '1 repository',
      'View security score',
      'Basic issue detection',
      'Detected technologies',
    ],
    limitations: [
      'AI suggestions blurred',
      'No report exports',
      'No GitHub automation',
    ],
    cta: 'Get Started',
    popular: false,
    highlight: false,
    planId: 'free',
  },
  {
    name: 'Plus',
    price: '$12',
    period: 'per month',
    description: 'For individual developers',
    features: [
      '50 scans per month',
      '5 repositories',
      'Full AI fix suggestions',
      'Copy AI remediation code',
      'PDF report download',
      '10 reports per month',
      'Priority email support',
    ],
    limitations: [
      'No GitHub PR automation',
      'No team features',
    ],
    cta: 'Start Free Trial',
    popular: true,
    highlight: true,
    planId: 'plus',
  },
  {
    name: 'Pro',
    price: '$29',
    period: 'per month',
    description: 'For professional DevOps engineers',
    features: [
      'Unlimited scans',
      'Unlimited repositories',
      'AI remediation (Docker, K8s, Terraform)',
      'Download security patches',
      'Export JSON / SARIF / Excel',
      'Scan history dashboard',
      'Architecture visualization',
      'GitHub app integration',
      'API access (1000 req/hr)',
      'Priority support',
    ],
    limitations: [],
    cta: 'Start Free Trial',
    popular: false,
    highlight: true,
    planId: 'pro',
  },
  {
    name: 'Enterprise',
    price: '$99',
    period: 'per month',
    description: 'For companies and teams',
    features: [
      'Everything in Pro',
      'GitHub PR auto-fix',
      'CI/CD pipeline integration',
      'Unlimited team members',
      'Organization scanning',
      'Compliance reporting',
      'Custom security rules',
      'Full API access (5000 req/hr)',
      'Dedicated support',
      'SLA guarantee',
    ],
    limitations: [],
    cta: 'Contact Sales',
    popular: false,
    highlight: false,
    planId: 'enterprise',
  },
]

const testimonials = [
  {
    name: 'Sarah Chen',
    role: 'DevOps Lead at TechCorp',
    content: 'DevArchAI caught critical security issues in our Terraform configs before they reached production. Saved us from a potential breach.',
    avatar: 'SC',
    rating: 5,
  },
  {
    name: 'Marcus Rodriguez',
    role: 'SRE at StartupXYZ',
    content: 'The AI recommendations are incredibly accurate. It\'s like having a senior DevOps engineer review every line of infrastructure code.',
    avatar: 'MR',
    rating: 5,
  },
  {
    name: 'Emily Watson',
    role: 'Security Engineer at Enterprise Inc',
    content: 'Finally, a tool that understands both security AND DevOps. The comprehensive reports make compliance audits so much easier.',
    avatar: 'EW',
    rating: 5,
  },
]

export function Landing() {
  const navigate = useNavigate()
  const [animationStep, setAnimationStep] = useState(0)

  const animationSteps = [
    { text: 'Connecting to GitHub repository...', icon: Github },
    { text: 'Detecting DevOps stack...', icon: GitBranch },
    { text: 'Scanning Docker, Terraform, CI/CD files...', icon: Shield },
    { text: 'Running security and architecture checks...', icon: Zap },
    { text: 'Generating AI recommendations...', icon: Sparkles },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setAnimationStep((prev) => (prev + 1) % animationSteps.length)
    }, 2000)
    return () => clearInterval(timer)
  }, [])

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 }
    }
  }

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <motion.div
              className="flex items-center gap-3"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 border border-white/20">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold gradient-text">DevArchAI</span>
            </motion.div>
            <motion.div
              className="flex items-center gap-4"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/login')}
                className="hidden sm:flex"
              >
                Login
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/register')}
                glow
              >
                Get Started
              </Button>
            </motion.div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative py-20 lg:py-32 overflow-hidden">
        {/* Background gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <motion.div
            className="absolute -top-40 -right-40 w-96 h-96 bg-primary/20 rounded-full blur-3xl"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.3, 0.5, 0.3],
            }}
            transition={{ duration: 5, repeat: Infinity }}
          />
          <motion.div
            className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl"
            animate={{
              scale: [1.2, 1, 1.2],
              opacity: [0.5, 0.3, 0.5],
            }}
            transition={{ duration: 5, repeat: Infinity }}
          />
        </div>

        <div className="container mx-auto px-4 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              className="max-w-2xl space-y-8"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {/* Badge */}
              <motion.div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30 backdrop-blur-sm shadow-lg shadow-primary/20"
                variants={itemVariants}
              >
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary">AI-Powered DevSecOps Platform</span>
              </motion.div>

              {/* Title */}
              <motion.h1
                className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight"
                variants={itemVariants}
              >
                <span className="gradient-text">Secure Your DevOps</span>
                <br />
                <span className="text-foreground">Before Production</span>
              </motion.h1>

              {/* Description */}
              <motion.p
                className="text-lg md:text-xl text-muted-foreground"
                variants={itemVariants}
              >
                Analyze GitHub repositories to detect infrastructure vulnerabilities in Docker, Terraform, Kubernetes and CI/CD pipelines. Get AI-powered fix recommendations instantly.
              </motion.p>

              {/* Scanner Component */}
              <motion.div
                className="pt-4"
                variants={itemVariants}
              >
                <LandingScanner />
              </motion.div>

              {/* Social proof */}
              <motion.div
                className="flex items-center gap-6 pt-4"
                variants={itemVariants}
              >
                <div className="flex -space-x-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-indigo-600/20 border-2 border-background flex items-center justify-center text-xs font-medium text-primary"
                    >
                      {String.fromCharCode(64 + i)}
                    </div>
                  ))}
                </div>
                <div>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground">Trusted by 10,000+ developers</p>
                </div>
              </motion.div>
            </motion.div>

            {/* Right side - Scanning Animation */}
            <motion.div
              className="hidden lg:block"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <ScanningAnimation />
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 border-y border-white/10 bg-white/5">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
            {[
              { label: 'Repositories Analyzed', value: '10,000+' },
              { label: 'Security Rules', value: '500+' },
              { label: 'Avg. Analysis Time', value: '< 30s' },
              { label: 'Accuracy Rate', value: '99.9%' },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <p className="text-3xl md:text-4xl font-bold gradient-text">{stat.value}</p>
                <p className="text-sm text-muted-foreground mt-2">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Why DevOps Security is Difficult */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">Why DevOps Security is Difficult</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Modern infrastructure is complex. Security teams struggle to keep up with the pace of change.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {[
              {
                icon: Lock,
                title: 'Multiple Tools & Formats',
                description: 'Docker, K8s, Terraform, CI/CD - each with their own security concerns and best practices.',
              },
              {
                icon: Zap,
                title: 'Fast-Paced Development',
                description: 'Deployments happen multiple times per day. Manual security reviews can\'t keep up.',
              },
              {
                icon: Brain,
                title: 'Expertise Gap',
                description: 'Security teams lack DevOps context. DevOps teams lack security expertise.',
              },
              {
                icon: Server,
                title: 'Cloud Complexity',
                description: 'AWS, Azure, GCP - each with hundreds of services and configuration options.',
              },
              {
                icon: GitBranch,
                title: 'Distributed Ownership',
                description: 'Infrastructure code is spread across repos, teams, and environments.',
              },
              {
                icon: AlertTriangle,
                title: 'False Positives',
                description: 'Traditional scanners generate noise. Teams ignore alerts due to alert fatigue.',
              },
            ].map((item, index) => (
              <motion.div
                key={item.title}
                className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="p-3 rounded-xl w-fit bg-red-500/10 border border-red-500/30 mb-4">
                  <item.icon className="h-6 w-6 text-red-400" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">{item.title}</h3>
                <p className="text-muted-foreground">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How the Platform Works */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">How DevArchAI Works</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Get comprehensive security analysis in 5 simple steps.
            </p>
          </motion.div>

          <div className="max-w-4xl mx-auto space-y-6">
            {[
              {
                step: '01',
                icon: Github,
                title: 'Connect Repository',
                description: 'Provide your GitHub repository URL or upload infrastructure files directly.',
              },
              {
                step: '02',
                icon: FileCode,
                title: 'Automatic Detection',
                description: 'We automatically detect your DevOps stack - Docker, K8s, Terraform, CI/CD.',
              },
              {
                step: '03',
                icon: Shield,
                title: 'Run Security Rules',
                description: '500+ security rules check for misconfigurations, vulnerabilities, and best practices.',
              },
              {
                step: '04',
                icon: Brain,
                title: 'AI Analysis',
                description: 'AI analyzes findings and provides context-aware fix recommendations.',
              },
              {
                step: '05',
                icon: Rocket,
                title: 'Get Actionable Report',
                description: 'Receive a comprehensive report with prioritized issues and fix suggestions.',
              },
            ].map((item, index) => (
              <motion.div
                key={item.step}
                className="flex items-start gap-6 p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="flex-shrink-0">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center shadow-lg shadow-primary/30">
                      <item.icon className="h-8 w-8 text-white" />
                    </div>
                    <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-background border-2 border-primary flex items-center justify-center">
                      <span className="text-xs font-bold text-primary">{item.step}</span>
                    </div>
                  </div>
                </div>
                <div className="flex-1 pt-2">
                  <h3 className="text-xl font-semibold text-foreground mb-2">{item.title}</h3>
                  <p className="text-muted-foreground">{item.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Supported Technologies */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">Supported Technologies</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Comprehensive coverage for your entire DevOps stack.
            </p>
          </motion.div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 max-w-5xl mx-auto">
            {technologies.map((tech, index) => (
              <motion.div
                key={tech.name}
                className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10 text-center hover:border-primary/30 transition-all duration-300"
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.05 }}
              >
                <tech.icon className="h-10 w-10 text-primary mx-auto mb-3" />
                <h3 className="font-semibold text-foreground mb-1">{tech.name}</h3>
                <p className="text-xs text-muted-foreground">{tech.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Live Scan Demo */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">See It In Action</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Watch how DevArchAI analyzes your infrastructure in real-time.
            </p>
          </motion.div>

          <div className="max-w-2xl mx-auto">
            <Card className="p-6" hover={false}>
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground text-left">
                  Live Analysis Demo
                </h3>
                <div className="space-y-3">
                  {animationSteps.map((step, index) => {
                    const Icon = step.icon
                    const isActive = index === animationStep
                    const isCompleted = index < animationStep

                    return (
                      <motion.div
                        key={index}
                        className={cn(
                          'flex items-center gap-3 p-3 rounded-lg transition-all duration-300',
                          isActive
                            ? 'bg-primary/15 border border-primary/30'
                            : isCompleted
                            ? 'bg-green-500/10 border border-green-500/30'
                            : 'bg-white/5 border border-white/10'
                        )}
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: index * 0.1 }}
                      >
                        <div className={cn(
                          'p-2 rounded-lg transition-all duration-300',
                          isActive
                            ? 'bg-primary/20'
                            : isCompleted
                            ? 'bg-green-500/20'
                            : 'bg-white/10'
                        )}>
                          {isCompleted ? (
                            <Check className="h-4 w-4 text-green-400" />
                          ) : (
                            <Icon className={cn(
                              'h-4 w-4',
                              isActive ? 'text-primary animate-pulse' : 'text-muted-foreground'
                            )} />
                          )}
                        </div>
                        <span className={cn(
                          'text-sm font-medium transition-colors duration-300',
                          isActive
                            ? 'text-primary'
                            : isCompleted
                            ? 'text-green-400'
                            : 'text-muted-foreground'
                        )}>
                          {step.text}
                        </span>
                        {isActive && (
                          <motion.div
                            className="ml-auto"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          >
                            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full" />
                          </motion.div>
                        )}
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">Loved by DevOps Teams</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              See what security engineers and DevOps teams are saying.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={testimonial.name}
                className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-muted-foreground mb-6">"{testimonial.content}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center text-sm font-medium text-white">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{testimonial.name}</p>
                    <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Plans */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">Simple, Transparent Pricing</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Start free and scale as you grow. No hidden fees.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {pricingPlans.map((plan, index) => (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    'p-6 h-full flex flex-col relative',
                    plan.highlight && 'border-primary/50 shadow-lg shadow-primary/10',
                    plan.popular && 'ring-2 ring-primary'
                  )}
                  hover
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="inline-flex items-center gap-1 px-4 py-1.5 rounded-full text-xs font-medium bg-primary text-primary-foreground shadow-lg">
                        <Star className="h-3 w-3 fill-current" />
                        Most Popular
                      </span>
                    </div>
                  )}

                  <div className="mb-6">
                    <h3 className="text-xl font-semibold text-foreground">{plan.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">{plan.description}</p>
                  </div>

                  <div className="mb-6">
                    <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                    <span className="text-muted-foreground ml-2">/{plan.period}</span>
                  </div>

                  <ul className="space-y-3 mb-6 flex-1">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2">
                        <Check className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                    {plan.limitations && plan.limitations.length > 0 && (
                      <>
                        <li className="pt-3 border-t border-white/10" />
                        {plan.limitations.map((limitation) => (
                          <li key={limitation} className="flex items-start gap-2">
                            <Lock className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                            <span className="text-sm text-muted-foreground">{limitation}</span>
                          </li>
                        ))}
                      </>
                    )}
                  </ul>

                  <Button
                    variant={plan.highlight ? 'primary' : 'secondary'}
                    className="w-full"
                    glow={plan.highlight}
                    onClick={() => navigate(plan.highlight ? '/register' : '/login')}
                  >
                    {plan.cta}
                  </Button>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <Card className="max-w-4xl mx-auto p-12 text-center glow-primary" hover={false}>
            <div className="space-y-8">
              <motion.div
                className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30"
                initial={{ scale: 0.8, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
              >
                <Shield className="h-12 w-12 text-white" />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="text-3xl md:text-4xl font-bold mb-4">
                  <span className="gradient-text">Ready to Secure Your Infrastructure?</span>
                </h2>
                <p className="text-lg text-muted-foreground max-w-xl mx-auto">
                  Start analyzing your DevOps architecture today. Get actionable security recommendations in seconds.
                </p>
              </motion.div>

              <motion.div
                className="flex flex-col sm:flex-row items-center justify-center gap-4"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
              >
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => navigate('/register')}
                  className="w-full sm:w-auto px-8 py-6 text-lg"
                  glow
                >
                  Start Free Trial
                  <ArrowRight className="h-5 w-5" />
                </Button>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => navigate('/login')}
                  className="w-full sm:w-auto px-8 py-6 text-lg"
                >
                  Login to Existing Account
                </Button>
              </motion.div>
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
                  <Shield className="h-4 w-4 text-white" />
                </div>
                <span className="font-semibold gradient-text">DevArchAI</span>
              </div>
              <p className="text-sm text-muted-foreground">
                AI-powered DevSecOps platform for modern infrastructure security.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-foreground mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">Features</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Pricing</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Integrations</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Changelog</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-foreground mb-4">Resources</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">Documentation</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">API Reference</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Community</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-foreground mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">About</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Security</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-white/10">
            <p className="text-sm text-muted-foreground">
              &copy; 2024 DevArchAI. All rights reserved.
            </p>
            <div className="flex items-center gap-6">
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                <Globe className="h-5 w-5" />
              </a>
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                <Github className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function AlertTriangle() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  )
}
