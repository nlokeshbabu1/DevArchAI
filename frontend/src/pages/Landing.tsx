import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Shield, Zap, GitBranch, BarChart3, Check, ArrowRight, AlertTriangle,
  Github, Star, Terminal, Layers, Cloud, Box, Sparkles
} from 'lucide-react'
import { Button } from '../components/ui-animated'
import { cn } from '../lib/utils'
import { DetectedTechStack } from '../components/landing/DetectedTechStack'
import { TrustSection } from '../components/landing/TrustSection'
import { PricingSection } from '../components/landing/PricingSection'

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

  const handleStartScan = () => {
    // Users must login first to scan
    navigate('/login')
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

      {/* Hero Section - TOP */}
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
          <div className="max-w-5xl mx-auto text-center space-y-8">
            {/* Main Headline */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold leading-tight">
                <span className="gradient-text">Detect DevOps Security Risks</span>
                <br />
                <span className="text-foreground">Before Production</span>
              </h1>
            </motion.div>

            {/* Subheading */}
            <motion.p
              className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              Scan Terraform, Kubernetes, Docker, and CI/CD pipelines in seconds
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              className="flex flex-col sm:flex-row gap-4 justify-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <Button
                variant="primary"
                size="lg"
                onClick={handleStartScan}
                className="px-8 py-6 text-lg"
                glow
              >
                Start Free Scan
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => {
                  document.getElementById('demo-preview')?.scrollIntoView({ behavior: 'smooth' })
                }}
                className="px-8 py-6 text-lg"
              >
                View Demo
              </Button>
            </motion.div>

            {/* Trust Indicators */}
            <motion.div
              className="flex flex-wrap justify-center gap-6 text-sm text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            >
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-400" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-400" />
                <span>Free tier available</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-400" />
                <span>Instant results</span>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section - Subtle, below hero */}
      <section className="py-8 border-y border-white/5 bg-white/[0.02]">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            {[
              { label: 'Repositories Analyzed', value: '10,000+' },
              { label: 'Security Rules', value: '500+' },
              { label: 'Technologies Supported', value: '40+' },
              { label: 'Avg. Scan Time', value: '< 30s' },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                className="text-center"
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <p className="text-2xl md:text-3xl font-bold gradient-text">{stat.value}</p>
                <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Preview Card */}
      <section id="demo-preview" className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12 space-y-4">
            <motion.h2
              className="text-4xl font-bold gradient-text"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              See What We Find
            </motion.h2>
            <motion.p
              className="text-lg text-muted-foreground max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              Real scan results from production infrastructure
            </motion.p>
          </div>

          {/* Mock Scan Result Card */}
          <motion.div
            className="max-w-4xl mx-auto"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-white/0 backdrop-blur-sm overflow-hidden">
              {/* Card Header */}
              <div className="p-6 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 border border-primary/30">
                      <Terminal className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground">terraform-infrastructure</h3>
                      <p className="text-sm text-muted-foreground">github.com/example/terraform-infra</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-green-400">72</div>
                    <div className="text-xs text-muted-foreground">Security Score</div>
                  </div>
                </div>
              </div>

              {/* Severity Stats */}
              <div className="p-6 border-b border-white/10">
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-400">3</div>
                    <div className="text-xs text-muted-foreground">Critical</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-400">8</div>
                    <div className="text-xs text-muted-foreground">High</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-400">12</div>
                    <div className="text-xs text-muted-foreground">Medium</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-400">15</div>
                    <div className="text-xs text-muted-foreground">Low</div>
                  </div>
                </div>
              </div>

              {/* Sample Findings */}
              <div className="p-6 space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <AlertTriangle className="h-5 w-5 text-orange-400" />
                  <h4 className="font-semibold text-foreground">Sample Findings</h4>
                </div>

                {/* Finding 1 */}
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
                  <div className="flex items-start gap-3">
                    <div className="p-1.5 rounded bg-red-500/20">
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
                          CRITICAL
                        </span>
                        <span className="text-xs font-mono text-muted-foreground">TF-STATE-004</span>
                      </div>
                      <h5 className="font-medium text-foreground mb-1">Backend State Encryption Required</h5>
                      <p className="text-sm text-muted-foreground">Terraform state file is not encrypted. State files may contain sensitive data.</p>
                    </div>
                  </div>
                </div>

                {/* Finding 2 */}
                <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/30">
                  <div className="flex items-start gap-3">
                    <div className="p-1.5 rounded bg-orange-500/20">
                      <AlertTriangle className="h-4 w-4 text-orange-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-orange-500/20 text-orange-400 border border-orange-500/30">
                          HIGH
                        </span>
                        <span className="text-xs font-mono text-muted-foreground">DKR-SEC-001</span>
                      </div>
                      <h5 className="font-medium text-foreground mb-1">Run Docker Container as Non-Root User</h5>
                      <p className="text-sm text-muted-foreground">Docker container is running as root user, which poses security risks.</p>
                    </div>
                  </div>
                </div>

                {/* Finding 3 */}
                <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                  <div className="flex items-start gap-3">
                    <div className="p-1.5 rounded bg-yellow-500/20">
                      <AlertTriangle className="h-4 w-4 text-yellow-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                          MEDIUM
                        </span>
                        <span className="text-xs font-mono text-muted-foreground">K8S-SEC-001</span>
                      </div>
                      <h5 className="font-medium text-foreground mb-1">Kubernetes Pod Security Context Missing</h5>
                      <p className="text-sm text-muted-foreground">Pod does not define security context, allowing privileged containers.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* CTA Footer */}
              <div className="p-6 bg-gradient-to-r from-primary/10 to-indigo-600/10 border-t border-white/10">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <p className="text-sm text-muted-foreground">
                    See all 38 findings with AI-powered fix recommendations
                  </p>
                  <Button
                    variant="primary"
                    size="md"
                    onClick={handleStartScan}
                    glow
                  >
                    Start Your Free Scan
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Detected Technologies Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <DetectedTechStack />
        </div>
      </section>

      {/* Trust Section */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <TrustSection />
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-4xl font-bold gradient-text">
              How DevArchAI Works
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Get comprehensive security analysis in 5 simple steps
            </p>
          </div>

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
                icon: GitBranch,
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
                icon: Sparkles,
                title: 'AI Analysis',
                description: 'AI analyzes findings and provides context-aware fix recommendations.',
              },
              {
                step: '05',
                icon: BarChart3,
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

      {/* Testimonials */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-4xl font-bold gradient-text">
              Loved by DevOps Teams
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              See what security engineers and DevOps teams are saying
            </p>
          </div>

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
                <p className="text-muted-foreground mb-6 leading-relaxed">
                  "{testimonial.content}"
                </p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-indigo-600/20 border-2 border-primary/30 flex items-center justify-center text-sm font-semibold text-primary">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">{testimonial.name}</p>
                    <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <PricingSection />
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <motion.div
            className="max-w-4xl mx-auto text-center p-12 rounded-3xl bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30 backdrop-blur-sm"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className="space-y-6">
              <h2 className="text-4xl md:text-5xl font-bold gradient-text">
                Ready to Secure Your DevOps?
              </h2>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Start scanning your repositories today and get AI-powered remediation suggestions in seconds.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => navigate('/login')}
                  glow
                >
                  Start Free Scan
                  <ArrowRight className="h-5 w-5 ml-2" />
                </Button>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => navigate('/pricing')}
                >
                  View Pricing
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                <Check className="h-4 w-4 inline mr-1 text-green-400" />
                No credit card required • Free tier available
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <span className="font-bold gradient-text">DevArchAI</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
              <a href="#" className="hover:text-foreground transition-colors">Terms</a>
              <a href="#" className="hover:text-foreground transition-colors">Security</a>
              <a href="#" className="hover:text-foreground transition-colors">Contact</a>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2024 DevArchAI. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
