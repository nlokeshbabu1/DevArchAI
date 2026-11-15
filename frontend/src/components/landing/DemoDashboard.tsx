import { motion } from 'framer-motion'
import { Shield, AlertTriangle, BarChart3, GitBranch } from 'lucide-react'
import { memo } from 'react'

import { cn } from '../../lib/utils'

interface DemoDashboardProps {
  onViewDemo: () => void
  onStartScan: () => void
}

const demoStats = [
  { label: 'Repositories Scanned', value: '10,000+', icon: GitBranch },
  { label: 'Security Rules', value: '500+', icon: Shield },
  { label: 'Security Issues Detected', value: '2,847', icon: AlertTriangle },
  { label: 'Avg. Security Score', value: '72/100', icon: BarChart3 },
]

const StatCard = memo(function StatCard({
  stat,
  index,
}: {
  stat: typeof demoStats[0]
  index: number
}) {
  const Icon = stat.icon

  return (
    <motion.div
      className="p-6 rounded-2xl bg-card/30 border border-white/[0.08] backdrop-blur-sm"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
          <Icon className="h-5 w-5 text-primary" />
        </div>
      </div>
      <p className="text-3xl font-bold text-foreground">{stat.value}</p>
      <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
    </motion.div>
  )
})

export function DemoDashboard({ onViewDemo, onStartScan }: DemoDashboardProps) {
  return (
    <div className="space-y-12">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {demoStats.map((stat, index) => (
          <StatCard key={stat.label} stat={stat} index={index} />
        ))}
      </div>

      <motion.div
        className="max-w-4xl mx-auto text-center p-12 rounded-3xl bg-card/30 border border-primary/20 backdrop-blur-sm"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div className="space-y-6">
          <div className="inline-flex p-4 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Shield className="h-12 w-12 text-primary" />
          </div>

          <h2 className="text-4xl md:text-5xl font-bold text-foreground">
            Scan Your DevOps Stack for Security Risks
          </h2>

          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Get comprehensive security analysis for your Terraform, Kubernetes, Docker, and CI/CD configurations in seconds.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <motion.button
              onClick={onStartScan}
              className="px-8 py-4 rounded-xl bg-primary text-primary-foreground font-semibold shadow-lg shadow-primary/30 hover:shadow-primary/50 transition-all duration-300"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Start Free Scan
            </motion.button>

            <motion.button
              onClick={onViewDemo}
              className="px-8 py-4 rounded-xl bg-white/5 border border-white/10 text-foreground font-semibold hover:bg-white/10 transition-all duration-300"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              View Demo Results
            </motion.button>
          </div>

          <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
              </span>
              No credit card required
            </span>
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
              </span>
              Free tier available
            </span>
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
              </span>
              Read-only access
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
