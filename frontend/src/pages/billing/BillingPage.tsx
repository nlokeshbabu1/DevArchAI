import { motion } from 'framer-motion'
import { Check, Zap, Shield, Brain } from 'lucide-react'
import { Button, Card } from '../../components/ui-animated'

const plans = [
  {
    name: 'Free',
    price: '$0',
    description: 'Perfect for getting started',
    features: [
      '5 repositories',
      '10 scans per month',
      'Basic security rules',
      'Email support',
    ],
    cta: 'Get Started',
    popular: false,
  },
  {
    name: 'Pro',
    price: '$29',
    description: 'For professional developers',
    features: [
      'Unlimited repositories',
      'Unlimited scans',
      'Advanced security rules',
      'AI suggestions',
      'Priority support',
      'API access',
    ],
    cta: 'Upgrade to Pro',
    popular: true,
  },
  {
    name: 'Team',
    price: '$99',
    description: 'For growing teams',
    features: [
      'Everything in Pro',
      'Team collaboration',
      'Shared reports',
      'SSO integration',
      'Dedicated support',
      'Custom rules',
    ],
    cta: 'Contact Sales',
    popular: false,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    description: 'For large organizations',
    features: [
      'Everything in Team',
      'On-premise deployment',
      'Custom integrations',
      'SLA guarantee',
      '24/7 support',
      'Training sessions',
    ],
    cta: 'Contact Sales',
    popular: false,
  },
]

export function BillingPage() {
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
          Select the perfect plan for your DevOps security needs
        </p>
      </motion.div>

      {/* Pricing Grid */}
      <motion.div
        className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {plans.map((plan, index) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + index * 0.1 }}
          >
            <Card 
              className={cn(
                'p-6 h-full flex flex-col',
                plan.popular && 'border-primary/50 shadow-lg shadow-primary/10'
              )} 
              hover={false}
            >
              {plan.popular && (
                <div className="mb-4">
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-primary/15 text-primary border border-primary/30">
                    <Zap className="h-3 w-3" />
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
                {plan.price !== 'Custom' && (
                  <span className="text-muted-foreground">/month</span>
                )}
              </div>

              <ul className="space-y-3 mb-6 flex-1">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <Check className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-muted-foreground">{feature}</span>
                  </li>
                ))}
              </ul>

              <Button
                variant={plan.popular ? 'primary' : 'secondary'}
                className="w-full"
                glow={plan.popular}
              >
                {plan.cta}
              </Button>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* Enterprise CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="p-8 text-center glow-primary" hover={false}>
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="inline-flex p-3 rounded-xl bg-gradient-to-br from-primary to-indigo-600">
              <Shield className="h-8 w-8 text-white" />
            </div>
            
            <div>
              <h2 className="text-2xl font-bold text-foreground">
                Need a Custom Solution?
              </h2>
              <p className="text-muted-foreground mt-2">
                Our enterprise plan offers custom features tailored to your organization's needs.
              </p>
            </div>

            <Button variant="primary" size="lg" icon={<Brain className="h-4 w-4" />}>
              Contact Sales
            </Button>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ')
}
