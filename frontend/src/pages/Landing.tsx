import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Shield, Zap, GitBranch, BarChart3, Sparkles, Check, ArrowRight,
  Github, Star, Users, Globe
} from 'lucide-react'
import { Button } from '../components/ui-animated'
import { cn } from '../lib/utils'
import { HeroScanner } from '../components/landing/HeroScanner'
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

      {/* Hero Section with Scanner */}
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
          {/* Hero Scanner Component */}
          <HeroScanner />
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
                  onClick={() => navigate('/register')}
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
