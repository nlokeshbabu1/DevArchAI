import { motion } from 'framer-motion'
import { Check, X, Sparkles, ArrowRight, Zap, Shield, Globe, Star } from 'lucide-react'
import { memo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import { cn } from '../../lib/utils'
import { Button, Card } from '../ui-animated'

interface PricingPlan {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  limitations: string[]
  cta: string
  popular: boolean
  highlight: boolean
  enterprise?: boolean
  planId: string
  icon: React.ElementType
}

const pricingPlans: PricingPlan[] = [
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
      'Community support',
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
    icon: Shield,
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
    icon: Sparkles,
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
    icon: Zap,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For companies and teams',
    features: [
      'SSO / SAML authentication',
      'Role-based access control (RBAC)',
      'Audit logs & compliance',
      'Private deployment options',
      'Dedicated support engineer',
      '99.9% uptime SLA',
      'Custom integrations',
      'Priority support',
    ],
    limitations: [],
    cta: 'Contact Sales',
    popular: false,
    highlight: false,
    enterprise: true,
    planId: 'enterprise',
    icon: Globe,
  },
]

const PricingCard = memo(function PricingCard({
  plan, index, onNavigate,
}: {
  plan: PricingPlan; index: number; onNavigate: (path: string) => void
}) {
  const Icon = plan.icon

  const handleCta = useCallback(() => {
    if (plan.planId === 'free') {
      onNavigate('/register')
    } else if (plan.planId === 'enterprise') {
      window.open('mailto:sales@devarchai.com', '_blank')
    } else {
      onNavigate('/billing')
    }
  }, [plan.planId, onNavigate])

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card
        className={cn(
          'relative h-full flex flex-col p-5 transition-all duration-300',
          plan.highlight
            ? 'border-primary/40 shadow-lg shadow-primary/[0.08]'
            : 'border-white/[0.08] hover:border-white/[0.15]',
          plan.popular && 'ring-2 ring-primary/40',
          plan.enterprise && 'border-primary/25 shadow-lg shadow-primary/[0.04]'
        )}
        hover
      >
        {plan.popular && (
          <div className="absolute -top-3 left-1/2 -translate-x-1/2">
            <div className="px-3 py-1 rounded-full bg-primary text-xs font-semibold text-white shadow-lg shadow-primary/25">
              Most Popular
            </div>
          </div>
        )}
        {plan.enterprise && (
          <div className="absolute -top-3 left-1/2 -translate-x-1/2">
            <div className="px-3 py-1 rounded-full bg-primary text-xs font-semibold text-white shadow-lg shadow-primary/25 flex items-center gap-1">
              <Globe className="h-3 w-3" />
              Enterprise
            </div>
          </div>
        )}

        <div className="text-center space-y-3 mb-5">
          <div className={cn(
            'p-2.5 rounded-xl w-fit mx-auto border border-white/[0.06]',
            plan.highlight ? 'bg-primary/10' : 'bg-white/[0.04]'
          )}>
            <Icon className="h-7 w-7 text-primary" />
          </div>

          <div>
            <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
            <div className="flex items-baseline justify-center gap-1">
              <span className="text-3xl font-bold text-white">{plan.price}</span>
              {plan.period && <span className="text-sm text-slate-400">/{plan.period}</span>}
            </div>
            <p className="text-sm text-slate-400 mt-1.5">{plan.description}</p>
          </div>
        </div>

        <div className="space-y-2.5 mb-5 flex-1">
          {plan.features.map((feature) => (
            <div key={feature} className="flex items-start gap-2 text-sm">
              <Check className="h-4 w-4 text-green-400/80 flex-shrink-0 mt-0.5" />
              <span className="text-slate-400 text-[13px]">{feature}</span>
            </div>
          ))}

          {plan.limitations.length > 0 && (
            <>
              <div className="my-2.5 border-t border-white/[0.06]" />
              {plan.limitations.map((limitation) => (
                <div key={limitation} className="flex items-start gap-2 text-sm">
                  <X className="h-4 w-4 text-red-400/60 flex-shrink-0 mt-0.5" />
                  <span className="text-slate-400/70 text-[13px]">{limitation}</span>
                </div>
              ))}
            </>
          )}
        </div>

        <Button
          variant={plan.highlight ? 'primary' : 'secondary'}
          size="lg"
          className="w-full btn-premium"
          onClick={handleCta}
        >
          {plan.cta}
          {plan.highlight && <ArrowRight className="h-4 w-4 ml-1.5" />}
        </Button>
      </Card>
    </motion.div>
  )
})

function CommercialGatingSection() {
  return (
    <motion.div
      className="mt-14 p-7 rounded-2xl bg-primary/[0.04] border border-primary/15"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="text-center space-y-3 mb-8">
        <h3 className="text-xl font-bold text-white">
          AI Remediation Gating
        </h3>
        <p className="text-slate-400 max-w-2xl mx-auto text-sm">
          See what&apos;s included with each plan when viewing scan results
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-5">
        {[
          {
            plan: 'Free Plan',
            icon: Shield,
            description: 'See scan results but AI remediation is blurred',
            visual: (
              <div className="p-4 rounded-xl bg-black/30 border border-white/[0.06]">
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <div
                      key={i}
                      className="h-2.5 bg-white/[0.08] rounded animate-pulse"
                      style={{ width: `${80 - i * 10}%` }}
                    />
                  ))}
                </div>
                <div className="mt-3 text-xs text-slate-400 text-center">
                  AI Fix Locked
                </div>
              </div>
            ),
          },
          {
            plan: 'Plus Plan',
            icon: Sparkles,
            description: 'Full AI remediation unlocked with copy-paste code',
            visual: (
              <div className="p-4 rounded-xl bg-primary/[0.08] border border-primary/20">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span className="text-xs font-semibold text-primary">AI Fix</span>
                </div>
                <div className="space-y-1.5">
                  {[...Array(3)].map((_, i) => (
                    <div
                      key={i}
                      className="h-2 bg-primary/25 rounded"
                      style={{ width: `${90 - i * 15}%` }}
                    />
                  ))}
                </div>
                <div className="mt-3 text-xs text-primary text-center">
                  Full Code Visible
                </div>
              </div>
            ),
          },
          {
            plan: 'Pro Plan',
            icon: Zap,
            description: 'Everything in Plus + automated PR creation',
            visual: (
              <div className="p-4 rounded-xl bg-primary/10 border border-primary/20">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-primary" />
                  <span className="text-xs font-semibold text-primary">Auto-Fix</span>
                </div>
                <div className="space-y-1.5">
                  {[...Array(3)].map((_, i) => (
                    <div
                      key={i}
                      className="h-2 bg-primary/35 rounded"
                      style={{ width: `${95 - i * 10}%` }}
                    />
                  ))}
                </div>
                <div className="mt-3 text-xs text-primary text-center">
                  Auto PR Creation
                </div>
              </div>
            ),
          },
        ].map((item, index) => {
          const Icon = item.icon

          return (
            <motion.div
              key={item.plan}
              className="space-y-3"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.08, duration: 0.4 }}
            >
              <div className="text-center">
                <Icon className="h-7 w-7 text-primary mx-auto mb-1.5" />
                <h4 className="font-semibold text-white text-sm">{item.plan}</h4>
              </div>
              {item.visual}
              <p className="text-xs text-center text-slate-400">
                {item.description}
              </p>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

export function CommercialPricingSection() {
  const navigate = useNavigate()

  return (
    <>
      <div className="text-center mb-12 space-y-3">
        <motion.div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.08] border border-primary/20"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <Star className="h-4 w-4 text-primary/80" />
          <span className="text-sm font-medium text-primary/90">Simple, Transparent Pricing</span>
        </motion.div>

        <h2 className="display-lg text-white">
          Choose Your Plan
        </h2>
        <p className="text-base text-slate-400 max-w-2xl mx-auto">
          Start free, upgrade when you need more power
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {pricingPlans.map((plan, index) => (
          <PricingCard key={plan.name} plan={plan} index={index} onNavigate={navigate} />
        ))}
      </div>

      <CommercialGatingSection />
    </>
  )
}

export function PricingSectionSkeleton() {
  return (
    <div className="py-16 lg:py-24" aria-busy="true" aria-label="Loading pricing">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-4xl">
        <div className="h-10 w-2/3 mx-auto rounded-lg bg-white/[0.06] animate-pulse mb-4" />
        <div className="h-5 w-1/2 mx-auto rounded bg-white/[0.04] animate-pulse mb-10" />
        <div className="h-64 rounded-2xl bg-white/[0.04] border border-white/[0.06] animate-pulse" />
      </div>
    </div>
  )
}
