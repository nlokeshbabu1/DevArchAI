import { motion } from 'framer-motion'
import { Check, X, Sparkles, ArrowRight, Zap, Shield, Globe, Star } from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'

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
    icon: Globe,
  },
]

export function PricingSection() {
  const navigate = useNavigate()

  return (
    <div className="w-full max-w-7xl mx-auto">
      <div className="text-center mb-16 space-y-4">
        <motion.div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30"
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <Star className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-primary">Simple, Transparent Pricing</span>
        </motion.div>

        <h2 className="text-4xl md:text-5xl font-bold gradient-text">
          Choose Your Plan
        </h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Start free, upgrade when you need more power
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        {pricingPlans.map((plan, index) => {
          const Icon = plan.icon
          
          return (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
            >
              <Card
                className={cn(
                  'relative h-full flex flex-col p-6 transition-all duration-300',
                  plan.highlight
                    ? 'border-primary/50 shadow-lg shadow-primary/10'
                    : 'border-white/10 hover:border-white/20',
                  plan.popular && 'ring-2 ring-primary/50'
                )}
                hover
              >
                {/* Popular Badge */}
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <div className="px-3 py-1 rounded-full bg-gradient-to-r from-primary to-indigo-600 text-xs font-semibold text-white shadow-lg">
                      Most Popular
                    </div>
                  </div>
                )}

                {/* Plan Header */}
                <div className="text-center space-y-4 mb-6">
                  <div className={cn(
                    'p-3 rounded-xl w-fit mx-auto bg-gradient-to-br border border-white/10',
                    plan.highlight
                      ? 'from-primary/20 to-indigo-600/20'
                      : 'from-white/10 to-white/5'
                  )}>
                    <Icon className="h-8 w-8 text-primary" />
                  </div>

                  <div>
                    <h3 className="text-2xl font-bold text-foreground mb-1">
                      {plan.name}
                    </h3>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-4xl font-bold gradient-text">{plan.price}</span>
                      <span className="text-sm text-muted-foreground">/{plan.period}</span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-2">
                      {plan.description}
                    </p>
                  </div>
                </div>

                {/* Features */}
                <div className="space-y-3 mb-6 flex-1">
                  {plan.features.map((feature) => (
                    <div key={feature} className="flex items-start gap-2 text-sm">
                      <Check className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                      <span className="text-muted-foreground">{feature}</span>
                    </div>
                  ))}
                  
                  {plan.limitations.length > 0 && (
                    <>
                      <div className="my-3 border-t border-white/10" />
                      {plan.limitations.map((limitation) => (
                        <div key={limitation} className="flex items-start gap-2 text-sm">
                          <X className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                          <span className="text-muted-foreground">{limitation}</span>
                        </div>
                      ))}
                    </>
                  )}
                </div>

                {/* CTA Button */}
                <Button
                  variant={plan.highlight ? 'primary' : 'secondary'}
                  size="lg"
                  className="w-full"
                  onClick={() => {
                    if (plan.planId === 'free') {
                      navigate('/register')
                    } else if (plan.planId === 'enterprise') {
                      navigate('/contact')
                    } else {
                      navigate('/billing')
                    }
                  }}
                  glow={plan.highlight}
                >
                  {plan.cta}
                  {plan.highlight && <ArrowRight className="h-5 w-5 ml-2" />}
                </Button>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* AI Gating Explanation */}
      <motion.div
        className="mt-16 p-8 rounded-2xl bg-gradient-to-br from-primary/10 to-indigo-600/10 border border-primary/30"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <div className="text-center space-y-4 mb-8">
          <h3 className="text-2xl font-bold text-foreground">
            AI Remediation Gating
          </h3>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            See what's included with each plan when viewing scan results
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              plan: 'Free Plan',
              icon: Shield,
              description: 'See scan results but AI remediation is blurred',
              visual: (
                <div className="p-4 rounded-xl bg-black/50 border border-white/10">
                  <div className="space-y-2">
                    {[...Array(4)].map((_, i) => (
                      <div
                        key={i}
                        className="h-3 bg-white/10 rounded animate-pulse"
                        style={{ width: `${80 - i * 10}%` }}
                      />
                    ))}
                  </div>
                  <div className="mt-3 text-xs text-muted-foreground text-center">
                    🔒 AI Fix Locked
                  </div>
                </div>
              ),
            },
            {
              plan: 'Plus Plan',
              icon: Sparkles,
              description: 'Full AI remediation unlocked with copy-paste code',
              visual: (
                <div className="p-4 rounded-xl bg-primary/10 border border-primary/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span className="text-xs font-semibold text-primary">AI Fix</span>
                  </div>
                  <div className="space-y-1">
                    {[...Array(3)].map((_, i) => (
                      <div
                        key={i}
                        className="h-2 bg-primary/30 rounded"
                        style={{ width: `${90 - i * 15}%` }}
                      />
                    ))}
                  </div>
                  <div className="mt-3 text-xs text-primary text-center">
                    ✓ Full Code Visible
                  </div>
                </div>
              ),
            },
            {
              plan: 'Pro Plan',
              icon: Zap,
              description: 'Everything in Plus + automated PR creation',
              visual: (
                <div className="p-4 rounded-xl bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="h-4 w-4 text-primary" />
                    <span className="text-xs font-semibold text-primary">Auto-Fix</span>
                  </div>
                  <div className="space-y-1">
                    {[...Array(3)].map((_, i) => (
                      <div
                        key={i}
                        className="h-2 bg-primary/40 rounded"
                        style={{ width: `${95 - i * 10}%` }}
                      />
                    ))}
                  </div>
                  <div className="mt-3 text-xs text-primary text-center">
                    ⚡ Auto PR Creation
                  </div>
                </div>
              ),
            },
          ].map((item, index) => {
            const Icon = item.icon
            
            return (
              <motion.div
                key={item.plan}
                className="space-y-4"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="text-center">
                  <Icon className="h-8 w-8 text-primary mx-auto mb-2" />
                  <h4 className="font-semibold text-foreground">{item.plan}</h4>
                </div>
                {item.visual}
                <p className="text-sm text-center text-muted-foreground">
                  {item.description}
                </p>
              </motion.div>
            )
          })}
        </div>
      </motion.div>
    </div>
  )
}
