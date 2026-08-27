import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Check, Zap, Shield, Brain, Sparkles, Globe, Lock, ArrowRight, Star, Users, Building2 } from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'
import { cn } from '../../lib/utils'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth-store'
import { createCheckout, handleCheckoutResponse } from '../../lib/payment-gateway'

// Pricing data with multi-currency support
const PRICING_DATA = {
  free: {
    name: 'Free',
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
      'No team features',
    ],
    price: {
      USD: '$0',
      INR: '₹0',
      EUR: '€0',
      GBP: '£0',
      SGD: 'S$0',
      AUD: 'A$0',
    },
    cta: 'Get Started',
    popular: false,
    highlight: false,
    tier: 'free',
  },
  plus: {
    name: 'Plus',
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
      'No CI/CD integration',
    ],
    price: {
      USD: '$12',
      INR: '₹999',
      EUR: '€11',
      GBP: '£10',
      SGD: 'S$16',
      AUD: 'A$18',
    },
    cta: 'Start Free Trial',
    popular: true,
    highlight: true,
    tier: 'plus',
  },
  pro: {
    name: 'Pro',
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
    limitations: [
      'No GitHub PR automation',
      'No team collaboration',
    ],
    price: {
      USD: '$29',
      INR: '₹2,499',
      EUR: '€26',
      GBP: '£24',
      SGD: 'S$39',
      AUD: 'A$45',
    },
    cta: 'Start Free Trial',
    popular: false,
    highlight: true,
    tier: 'pro',
  },
  enterprise: {
    name: 'Enterprise',
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
    price: {
      USD: 'Custom',
      INR: 'Custom',
      EUR: 'Custom',
      GBP: 'Custom',
      SGD: 'Custom',
      AUD: 'Custom',
    },
    cta: 'Contact Sales',
    popular: false,
    highlight: false,
    enterprise: true,
    tier: 'enterprise',
  },
}

// Country to currency mapping
const COUNTRY_CURRENCY: Record<string, keyof typeof PRICING_DATA.free.price> = {
  US: 'USD',
  IN: 'INR',
  DE: 'EUR',
  FR: 'EUR',
  IT: 'EUR',
  ES: 'EUR',
  NL: 'EUR',
  GB: 'GBP',
  SG: 'SGD',
  AU: 'AUD',
  CA: 'USD',
  JP: 'USD',
  BR: 'USD',
  MX: 'USD',
}

const DEFAULT_CURRENCY: keyof typeof PRICING_DATA.free.price = 'USD'

export function PricingPage() {
  const navigate = useNavigate()
  const { user, token } = useAuthStore()
  const [searchParams] = useSearchParams()
  const [currency, setCurrency] = useState<keyof typeof PRICING_DATA.free.price>(DEFAULT_CURRENCY)
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly')
  const [loading, setLoading] = useState(true)

  // Get redirect path from URL params (passed from login)
  const redirectFromUrl = searchParams.get('redirect') || ''
  const planFromUrl = searchParams.get('plan') || 'plus'

  // Detect user's country and set currency
  useEffect(() => {
    const detectCurrency = async () => {
      try {
        // Try to get country from IP
        const response = await fetch('https://ipapi.co/json/')
        const data = await response.json()
        const countryCode = data.country_code
        if (countryCode && COUNTRY_CURRENCY[countryCode]) {
          setCurrency(COUNTRY_CURRENCY[countryCode])
        }
      } catch {
        // Default to USD when geo lookup is unavailable
      } finally {
        setLoading(false)
      }
    }

    detectCurrency()
  }, [])

  const handleUpgrade = async (plan: string) => {
    if (!token) {
      // Save the intended destination before login
      // Use redirect from URL if available, otherwise use default
      const redirectPath = redirectFromUrl || sessionStorage.getItem('postLoginRedirect') || '/scan-results'
      sessionStorage.setItem('upgradeIntent', 'true')
      sessionStorage.setItem('upgradePlan', plan)
      sessionStorage.setItem('postLoginRedirect', redirectPath)
      navigate('/login')
      return
    }

    if (plan === 'enterprise') {
      window.open('mailto:sales@devarchai.com', '_blank')
      return
    }

    try {
      // Use redirect from URL if available, otherwise from session storage
      const data = await createCheckout({ plan, billing: billingPeriod }, token)
      await handleCheckoutResponse(data)
    } catch (error) {
      console.error('Failed to create checkout session:', error)
    }
  }

  const plans = Object.values(PRICING_DATA)

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="container mx-auto px-4 py-12">
        <motion.div
          className="text-center max-w-3xl mx-auto mb-12"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30 mb-6">
            <Globe className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">
              Multi-Currency Pricing
            </span>
          </div>

          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="text-foreground">Choose Your Plan</span>
          </h1>
          <p className="text-lg text-muted-foreground">
            Start free with repository scanning. Upgrade when you need AI remediation, exports, and automation.
          </p>
        </motion.div>

        {/* Currency Selector */}
        <motion.div
          className="flex items-center justify-center gap-4 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <span className="text-sm text-muted-foreground">Currency:</span>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value as typeof currency)}
            className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          >
            <option value="USD">USD ($)</option>
            <option value="INR">INR (₹)</option>
            <option value="EUR">EUR (€)</option>
            <option value="GBP">GBP (£)</option>
            <option value="SGD">SGD (S$)</option>
            <option value="AUD">AUD (A$)</option>
          </select>
        </motion.div>

        {/* Billing Period Toggle */}
        <motion.div
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <button
            onClick={() => setBillingPeriod('monthly')}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              billingPeriod === 'monthly'
                ? 'bg-primary text-primary-foreground'
                : 'bg-white/5 text-muted-foreground hover:text-foreground'
            )}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingPeriod('yearly')}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              billingPeriod === 'yearly'
                ? 'bg-primary text-primary-foreground'
                : 'bg-white/5 text-muted-foreground hover:text-foreground'
            )}
          >
            Yearly
            <span className="ml-2 px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 text-xs">
              Save 20%
            </span>
          </button>
        </motion.div>

        {/* Pricing Grid */}
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 max-w-7xl mx-auto">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.tier}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * index }}
            >
              <Card
                className={cn(
                  'p-6 h-full flex flex-col relative',
                  plan.highlight && 'border-primary/50 shadow-lg shadow-primary/10',
                  plan.popular && 'ring-2 ring-primary',
                  (plan as any).enterprise && 'border-primary/30 shadow-lg shadow-primary/5'
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
                {(plan as any).enterprise && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 px-4 py-1.5 rounded-full text-xs font-medium bg-gradient-to-r from-primary to-indigo-600 text-white shadow-lg">
                      <Building2 className="h-3 w-3" />
                      Enterprise
                    </span>
                  </div>
                )}

                {/* Plan Header */}
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-2">
                    {plan.tier === 'free' && <Shield className="h-5 w-5 text-muted-foreground" />}
                    {plan.tier === 'plus' && <Zap className="h-5 w-5 text-primary" />}
                    {plan.tier === 'pro' && <Brain className="h-5 w-5 text-primary" />}
                    {plan.tier === 'enterprise' && <Building2 className="h-5 w-5 text-primary" />}
                    <h3 className="text-xl font-semibold text-foreground">{plan.name}</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">{plan.description}</p>
                </div>

                {/* Price */}
                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-foreground">
                      {plan.price[currency] === 'Custom'
                        ? 'Custom'
                        : billingPeriod === 'yearly' && plan.price[currency] !== '$0'
                          ? `${plan.price[currency].replace(/\d+/, (m) => String(Math.floor(parseInt(m.replace(/[^0-9]/g, '')) * 0.8)))}`
                          : plan.price[currency]
                      }
                    </span>
                    {plan.price[currency] !== '$0' && plan.price[currency] !== '₹0' && plan.price[currency] !== 'Custom' && (
                      <span className="text-muted-foreground">
                        /{billingPeriod === 'yearly' ? 'year' : 'month'}
                      </span>
                    )}
                  </div>
                  {billingPeriod === 'yearly' && plan.price[currency] !== '$0' && plan.price[currency] !== 'Custom' && (
                    <p className="text-xs text-green-400 mt-1">
                      Billed annually (save 20%)
                    </p>
                  )}
                </div>

                {/* Features */}
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
                          <Lock className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-muted-foreground">{limitation}</span>
                        </li>
                      ))}
                    </>
                  )}
                </ul>

                {/* CTA Button */}
                <Button
                  variant={plan.highlight ? 'primary' : 'secondary'}
                  className="w-full"
                  glow={plan.highlight}
                  onClick={() => handleUpgrade(plan.tier)}
                >
                  {plan.cta}
                  {plan.highlight && <ArrowRight className="h-4 w-4 ml-2" />}
                </Button>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Enterprise CTA */}
        <motion.div
          className="mt-16 max-w-4xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card className="p-8 text-center" hover={false}>
            <div className="space-y-6">
              <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600">
                <Users className="h-8 w-8 text-white" />
              </div>

              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  Need a Custom Enterprise Solution?
                </h2>
                <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">
                  Get custom features, dedicated support, and enterprise-grade security for your organization.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => handleUpgrade('enterprise')}
                  icon={<Building2 className="h-5 w-5" />}
                >
                  Contact Sales
                </Button>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => navigate('/dashboard')}
                >
                  Schedule Demo
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* FAQ Section */}
        <motion.div
          className="mt-20 max-w-4xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <h2 className="text-3xl font-bold text-center text-foreground mb-8">
            Frequently Asked Questions
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            {[
              {
                q: 'Can I change plans later?',
                a: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately.',
              },
              {
                q: 'Is there a free trial?',
                a: 'Yes! All paid plans include a 14-day free trial. No credit card required to start.',
              },
              {
                q: 'What payment methods do you accept?',
                a: 'We accept all major credit cards, PayPal, and bank transfers for enterprise plans.',
              },
              {
                q: 'Can I cancel anytime?',
                a: 'Absolutely. You can cancel your subscription at any time with no questions asked.',
              },
              {
                q: 'Do you offer discounts for nonprofits?',
                a: 'Yes! We offer special pricing for nonprofits, educational institutions, and open-source projects.',
              },
              {
                q: 'How does the scan limit work?',
                a: 'Scan limits reset monthly. Unused scans do not roll over to the next month.',
              },
            ].map((faq, index) => (
              <motion.div
                key={index}
                className="p-6 rounded-xl bg-white/5 border border-white/10"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 + index * 0.1 }}
              >
                <h3 className="font-semibold text-foreground mb-2">{faq.q}</h3>
                <p className="text-sm text-muted-foreground">{faq.a}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
