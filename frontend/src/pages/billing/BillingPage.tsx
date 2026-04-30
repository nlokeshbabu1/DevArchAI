import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Check, Zap, Shield, Brain, Loader2, Star, Building2 } from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import { useAuthStore } from '../../stores/auth-store'
import { useNavigate } from 'react-router-dom'
import { createCheckout, handleCheckoutResponse } from '../../lib/payment-gateway'

interface Subscription {
  id: string | null
  plan: string
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
}

const plans = [
  {
    name: 'Free',
    price: '$0',
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
    cta: 'Current Plan',
    popular: false,
    planId: 'free',
    highlight: false,
  },
  {
    name: 'Plus',
    price: '$12',
    priceInr: '₹999',
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
    planId: 'plus',
    highlight: true,
  },
  {
    name: 'Pro',
    price: '$29',
    priceInr: '₹2,499',
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
    planId: 'pro',
    highlight: true,
  },
  {
    name: 'Enterprise',
    price: '$99',
    priceInr: '₹7,999',
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
    planId: 'enterprise',
    highlight: false,
  },
]

export function BillingPage() {
  const navigate = useNavigate()
  const { user, token } = useAuthStore()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isUpgrading, setIsUpgrading] = useState<string | null>(null)
  const [currency, setCurrency] = useState<'USD' | 'INR'>('USD')

  useEffect(() => {
    fetchSubscription()
  }, [])

  const fetchSubscription = async () => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {}
      const response = await api.get('/billing/subscription', { headers })
      setSubscription(response.data)
    } catch (error) {
      console.error('Failed to fetch subscription:', error)
      setSubscription({
        id: null,
        plan: 'free',
        status: 'active',
        current_period_end: null,
        cancel_at_period_end: false,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpgrade = async (planId: string) => {
    if (planId === 'free') return

    if (!token) {
      navigate('/login')
      return
    }

    setIsUpgrading(planId)
    try {
      if (planId === 'enterprise') {
        window.open('mailto:sales@devarchai.com', '_blank')
        return
      }

      const data = await createCheckout({ plan: planId }, token)
      await handleCheckoutResponse(data)
    } catch (error) {
      console.error('Failed to create checkout session:', error)
    } finally {
      setIsUpgrading(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const currentPlan = subscription?.plan || 'free'

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        className="text-center max-w-2xl mx-auto"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-foreground">Choose Your Plan</h1>
        <p className="text-muted-foreground mt-2">
          Select the perfect plan for your DevSecOps needs
        </p>
        
        {/* Currency Toggle */}
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="text-sm text-muted-foreground">Currency:</span>
          <button
            onClick={() => setCurrency('USD')}
            className={cn(
              'px-3 py-1 rounded text-sm',
              currency === 'USD' ? 'bg-primary text-primary-foreground' : 'bg-white/5 text-muted-foreground'
            )}
          >
            USD ($)
          </button>
          <button
            onClick={() => setCurrency('INR')}
            className={cn(
              'px-3 py-1 rounded text-sm',
              currency === 'INR' ? 'bg-primary text-primary-foreground' : 'bg-white/5 text-muted-foreground'
            )}
          >
            INR (₹)
          </button>
        </div>

        {subscription && (
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30">
            <Zap className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">
              Current Plan: {subscription.plan.charAt(0).toUpperCase() + subscription.plan.slice(1)}
            </span>
          </div>
        )}
      </motion.div>

      {/* Pricing Grid */}
      <motion.div
        className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {plans.map((plan, index) => {
          const isCurrentPlan = currentPlan === plan.planId
          const isUpgradingThis = isUpgrading === plan.planId

          return (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + index * 0.1 }}
            >
              <Card
                className={cn(
                  'p-6 h-full flex flex-col relative',
                  plan.highlight && 'border-primary/50 shadow-lg shadow-primary/10',
                  plan.popular && 'ring-2 ring-primary',
                  isCurrentPlan && 'border-green-500/50 shadow-lg shadow-green-500/10'
                )}
                hover
              >
                {plan.popular && !isCurrentPlan && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium bg-primary text-primary-foreground shadow-lg">
                      <Star className="h-3 w-3 fill-current" />
                      Most Popular
                    </span>
                  </div>
                )}

                {isCurrentPlan && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium bg-green-500 text-white shadow-lg">
                      <Check className="h-3 w-3" />
                      Current Plan
                    </span>
                  </div>
                )}

                <div className="mb-6 mt-2">
                  <div className="flex items-center gap-2 mb-2">
                    {plan.planId === 'free' && <Shield className="h-5 w-5 text-muted-foreground" />}
                    {plan.planId === 'plus' && <Zap className="h-5 w-5 text-primary" />}
                    {plan.planId === 'pro' && <Brain className="h-5 w-5 text-primary" />}
                    {plan.planId === 'enterprise' && <Building2 className="h-5 w-5 text-primary" />}
                    <h3 className="text-xl font-semibold text-foreground">{plan.name}</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">{plan.description}</p>
                </div>

                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-foreground">
                      {currency === 'INR' ? plan.priceInr : plan.price}
                    </span>
                    {plan.price !== '$0' && (
                      <span className="text-muted-foreground">/month</span>
                    )}
                  </div>
                </div>

                <ul className="space-y-3 mb-6 flex-1">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                  {plan.limitations.length > 0 && (
                    <>
                      <li className="pt-3 border-t border-white/10" />
                      {plan.limitations.map((limitation) => (
                        <li key={limitation} className="flex items-start gap-2">
                          <Shield className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-muted-foreground">{limitation}</span>
                        </li>
                      ))}
                    </>
                  )}
                </ul>

                <Button
                  variant={isCurrentPlan ? 'secondary' : plan.highlight ? 'primary' : 'secondary'}
                  className="w-full"
                  glow={plan.highlight && !isCurrentPlan}
                  disabled={isCurrentPlan || isUpgradingThis}
                  onClick={() => handleUpgrade(plan.planId)}
                >
                  {isUpgradingThis ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : isCurrentPlan ? (
                    'Current Plan'
                  ) : (
                    plan.cta
                  )}
                </Button>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Enterprise CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="p-8 text-center glow-primary" hover={false}>
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600">
              <Building2 className="h-8 w-8 text-white" />
            </div>

            <div>
              <h2 className="text-2xl font-bold text-foreground">
                Need a Custom Enterprise Solution?
              </h2>
              <p className="text-muted-foreground mt-2">
                Get custom features, dedicated support, and enterprise-grade security for your organization.
              </p>
            </div>

            <Button
              variant="primary"
              size="lg"
              onClick={() => handleUpgrade('enterprise')}
              icon={<Building2 className="h-5 w-5" />}
            >
              Contact Sales
            </Button>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}
