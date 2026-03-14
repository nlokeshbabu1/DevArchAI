import { motion } from 'framer-motion'
import { Lock, Sparkles, ArrowRight, Zap } from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { cn } from '../../lib/utils'

interface AISuggestionBlurProps {
  isBlurred: boolean
  suggestion?: string | null
  codeFix?: string | null
  onUpgrade?: () => void
  upgradePlan?: string
  className?: string
}

export function AISuggestionBlur({
  isBlurred,
  suggestion,
  codeFix,
  onUpgrade,
  upgradePlan = 'plus',
  className,
}: AISuggestionBlurProps) {
  if (!isBlurred) {
    // Show full AI suggestion
    return (
      <div className={cn('space-y-4', className)}>
        {suggestion && (
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/30">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h4 className="font-semibold text-primary">AI Recommendation</h4>
            </div>
            <p className="text-sm text-muted-foreground">{suggestion}</p>
          </div>
        )}
        
        {codeFix && (
          <div className="relative group">
            <pre className="p-4 rounded-xl bg-black/50 border border-white/10 overflow-x-auto text-sm font-mono">
              <code>{codeFix}</code>
            </pre>
          </div>
        )}
      </div>
    )
  }

  // Show blurred AI suggestion with upgrade prompt
  return (
    <motion.div
      className={cn('relative overflow-hidden rounded-xl border border-white/10 bg-gradient-to-br from-primary/5 to-indigo-600/5', className)}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Blurred Content */}
      <div className="p-6 space-y-4">
        {/* Header with Lock Icon */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-primary/20">
            <Lock className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h4 className="font-semibold text-foreground">AI Fix Suggestion</h4>
            <p className="text-sm text-muted-foreground">
              Upgrade to unlock AI-powered remediation
            </p>
          </div>
        </div>

        {/* Blurred Code Block */}
        <div className="relative">
          <div className="p-4 rounded-xl bg-black/50 border border-white/10 overflow-hidden">
            <div className="space-y-2">
              {/* Generate blurred lines */}
              {[...Array(6)].map((_, i) => (
                <motion.div
                  key={i}
                  className="h-4 bg-gradient-to-r from-primary/30 via-primary/20 to-primary/30 rounded animate-pulse"
                  style={{
                    width: `${Math.random() * 40 + 60}%`,
                    animationDelay: `${i * 0.1}s`,
                  }}
                  initial={{ opacity: 0.5 }}
                  animate={{ opacity: [0.5, 0.8, 0.5] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.1,
                  }}
                />
              ))}
            </div>
          </div>

          {/* Lock Overlay */}
          <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="text-center p-6">
              <Lock className="h-12 w-12 text-primary mx-auto mb-3" />
              <p className="text-sm font-medium text-foreground mb-1">
                AI Remediation Locked
              </p>
              <p className="text-xs text-muted-foreground">
                Upgrade to {upgradePlan === 'plus' ? 'Plus' : 'Pro'} to view
              </p>
            </div>
          </div>
        </div>

        {/* Upgrade CTA */}
        <div className="pt-4">
          <div className="p-4 rounded-xl bg-gradient-to-r from-primary/15 to-indigo-600/15 border border-primary/30">
            <div className="flex items-start gap-3">
              <Zap className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground mb-2">
                  Unlock AI-powered DevOps remediation
                </p>
                <ul className="text-xs text-muted-foreground space-y-1 mb-3">
                  <li className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-primary" />
                    Get instant fix recommendations
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-primary" />
                    Copy-paste ready code fixes
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-primary" />
                    Auto-create GitHub pull requests
                  </li>
                </ul>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={onUpgrade}
                  className="w-full"
                  glow
                >
                  Upgrade to {upgradePlan === 'plus' ? 'Plus' : 'Pro'}
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

interface UpgradePromptProps {
  currentPlan: string
  feature: string
  requiredPlan: string
  onUpgrade?: () => void
  message?: string
}

export function UpgradePrompt({
  currentPlan,
  feature,
  requiredPlan,
  onUpgrade,
  message,
}: UpgradePromptProps) {
  return (
    <Card className="p-6 glow-primary" hover={false}>
      <div className="text-center space-y-4">
        <div className="inline-flex p-3 rounded-xl bg-gradient-to-br from-primary to-indigo-600">
          <Lock className="h-6 w-6 text-white" />
        </div>

        <div>
          <h3 className="text-lg font-semibold text-foreground">
            {message || `${feature} is not available in your plan`}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Current plan: <span className="font-medium text-foreground capitalize">{currentPlan}</span>
          </p>
        </div>

        <div className="p-4 rounded-xl bg-primary/10 border border-primary/30">
          <p className="text-sm text-foreground">
            Upgrade to <span className="font-bold text-primary capitalize">{requiredPlan}</span> to unlock this feature
          </p>
        </div>

        <div className="flex gap-3">
          <Button
            variant="primary"
            onClick={onUpgrade}
            className="flex-1"
            glow
          >
            Upgrade Now
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
          <Button variant="secondary" onClick={() => {}}>
            Learn More
          </Button>
        </div>
      </div>
    </Card>
  )
}

interface FeatureLockedOverlayProps {
  feature: string
  requiredPlan: string
  onUpgrade: () => void
}

export function FeatureLockedOverlay({
  feature,
  requiredPlan,
  onUpgrade,
}: FeatureLockedOverlayProps) {
  return (
    <motion.div
      className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-xl"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        className="text-center p-8 max-w-md"
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 mb-4">
          <Lock className="h-8 w-8 text-white" />
        </div>

        <h3 className="text-xl font-bold text-foreground mb-2">
          Feature Locked
        </h3>
        <p className="text-muted-foreground mb-6">
          {feature} requires {requiredPlan} plan
        </p>

        <Button
          variant="primary"
          size="lg"
          onClick={onUpgrade}
          className="w-full"
          glow
        >
          Upgrade to {requiredPlan}
          <ArrowRight className="h-5 w-5 ml-2" />
        </Button>
      </motion.div>
    </motion.div>
  )
}
