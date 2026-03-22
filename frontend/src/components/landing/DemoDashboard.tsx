import { motion } from 'framer-motion'
import { Shield, AlertTriangle, CheckCircle, BarChart3, GitBranch, Lock } from 'lucide-react'
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

export function DemoDashboard({ onViewDemo, onStartScan }: DemoDashboardProps) {
  return (
    <div className="space-y-12">
      {/* Hero Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {demoStats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.label}
              className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10 backdrop-blur-sm"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.05, borderColor: 'rgba(124, 58, 237, 0.5)' }}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/30">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
              </div>
              <p className="text-3xl font-bold gradient-text">{stat.value}</p>
              <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
            </motion.div>
          )
        })}
      </div>

      {/* CTA Section */}
      <motion.div
        className="max-w-4xl mx-auto text-center p-12 rounded-3xl bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30 backdrop-blur-sm"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <div className="space-y-6">
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-4">
            <Shield className="h-12 w-12 text-white" />
          </div>

          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            Scan Your DevOps Stack for Security Risks
          </h2>

          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Get comprehensive security analysis for your Terraform, Kubernetes, Docker, and CI/CD configurations in seconds.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <motion.button
              onClick={onStartScan}
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-primary to-indigo-600 text-white font-semibold shadow-lg shadow-primary/30 hover:shadow-primary/50 transition-all duration-300 hover:scale-105"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Start Free Scan
            </motion.button>

            <motion.button
              onClick={onViewDemo}
              className="px-8 py-4 rounded-xl bg-white/10 border border-white/20 text-white font-semibold hover:bg-white/20 transition-all duration-300"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              View Demo Results
            </motion.button>
          </div>

          <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-400" />
              <span>No credit card required</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-400" />
              <span>Free tier available</span>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-green-400" />
              <span>Read-only access</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
