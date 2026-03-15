import { motion } from 'framer-motion'
import { Shield, Award, FileCheck, Lock, CheckCircle, Globe, Zap } from 'lucide-react'
import { cn } from '../../lib/utils'

interface TrustBadge {
  name: string
  icon: React.ElementType
  description: string
  color: string
}

const trustBadges: TrustBadge[] = [
  {
    name: 'CIS Kubernetes Benchmark',
    icon: Shield,
    description: '200+ CIS compliance checks',
    color: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
  },
  {
    name: 'AWS Security Best Practices',
    icon: Award,
    description: 'AWS Well-Architected Framework',
    color: 'from-orange-500/20 to-amber-500/20 border-orange-500/30',
  },
  {
    name: 'OWASP DevSecOps',
    icon: FileCheck,
    description: 'OWASP Top 10 coverage',
    color: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
  },
  {
    name: 'Terraform Security',
    icon: Lock,
    description: 'Terraform Security Rules',
    color: 'from-purple-500/20 to-indigo-500/20 border-purple-500/30',
  },
]

export function TrustSection() {
  return (
    <div className="w-full max-w-6xl mx-auto">
      <div className="text-center mb-12 space-y-4">
        <h2 className="text-4xl font-bold gradient-text">
          Trusted Security Frameworks
        </h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Industry-standard security rules and compliance checks
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
        {trustBadges.map((badge, index) => {
          const Icon = badge.icon
          
          return (
            <motion.div
              key={badge.name}
              className={cn(
                'relative p-6 rounded-2xl bg-gradient-to-br border backdrop-blur-sm',
                'hover:shadow-xl transition-all duration-300',
                badge.color
              )}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.05, y: -5 }}
            >
              <div className="space-y-4">
                <div className={cn(
                  'p-3 rounded-xl w-fit bg-gradient-to-br border border-white/10',
                  badge.color
                )}>
                  <Icon className="h-8 w-8 text-foreground" />
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {badge.name}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {badge.description}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-xs text-green-400">
                  <CheckCircle className="h-4 w-4" />
                  <span>Active</span>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Stats */}
      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-6 p-8 rounded-2xl bg-white/5 border border-white/10"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        {[
          { label: 'Security Rules', value: '500+', icon: Shield },
          { label: 'Compliance Checks', value: '200+', icon: FileCheck },
          { label: 'Avg. Analysis Time', value: '< 30s', icon: Zap },
          { label: 'Accuracy Rate', value: '99.9%', icon: Award },
        ].map((stat, index) => {
          const Icon = stat.icon
          
          return (
            <div key={stat.label} className="text-center space-y-2">
              <Icon className="h-8 w-8 text-primary mx-auto" />
              <p className="text-3xl font-bold gradient-text">{stat.value}</p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </div>
          )
        })}
      </motion.div>
    </div>
  )
}
