import { motion } from 'framer-motion'
import { Shield, Zap, Globe, Users, Terminal, Brain, GitPullRequest } from 'lucide-react'
import { type ReactNode } from 'react'

const features = [
  { icon: Terminal, text: 'Docker & Kubernetes', color: 'text-blue-400' },
  { icon: Shield, text: 'Terraform Scanning', color: 'text-purple-400' },
  { icon: Zap, text: 'GitHub Actions CI/CD', color: 'text-orange-400' },
  { icon: Brain, text: 'AI Root Cause Analysis', color: 'text-green-400' },
  { icon: GitPullRequest, text: 'AI Fix Suggestions', color: 'text-cyan-400' },
]

const stats = [
  { value: '10,000+', label: 'Repositories' },
  { value: '500+', label: 'Security Rules' },
  { value: '<30 sec', label: 'Average Scan' },
]

const EASE_OUT = [0.16, 1, 0.3, 1] as const

interface AuthLayoutProps {
  children: ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-[#0B1020]">
      {/* Left Showcase — 40% on desktop */}
      <div className="hidden lg:flex lg:w-[40%] relative overflow-hidden items-center justify-center p-12 xl:p-16">
        {/* Ambient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.06] via-indigo-600/[0.04] to-purple-600/[0.06]" />

        {/* Dot texture */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(148,163,184,0.3) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        {/* Ambient glow orbs */}
        <div className="absolute top-1/4 left-1/3 w-64 h-64 bg-primary/[0.06] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-1/3 right-1/4 w-48 h-48 bg-blue-500/[0.04] rounded-full blur-[80px] pointer-events-none" />

        {/* Content */}
        <div className="relative z-10 max-w-md w-full">
          {/* Logo */}
          <motion.div
            className="mb-10"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE_OUT }}
          >
            <div className="inline-flex items-center gap-3 mb-6">
              <div className="p-2.5 rounded-xl bg-primary/10 border border-primary/20">
                <Shield className="h-7 w-7 text-primary" />
              </div>
              <span className="text-xl font-semibold text-white tracking-tight">DevArchAI</span>
            </div>
            <h1 className="text-3xl xl:text-[2.5rem] font-bold text-white leading-tight mb-3 tracking-tight">
              AI-Powered DevSecOps Platform
            </h1>
            <p className="text-base text-slate-400 leading-relaxed">
              Scan your infrastructure for security, reliability, and cost issues — with AI-powered fixes in under 30 seconds.
            </p>
          </motion.div>

          {/* Feature cards */}
          <div className="space-y-3 mb-10">
            {features.map((feature, i) => (
              <motion.div
                key={feature.text}
                className="group flex items-center gap-3.5 px-4 py-3 rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm transition-all duration-300 hover:border-white/[0.12] hover:bg-white/[0.04] hover:shadow-lg hover:shadow-black/20"
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.06, duration: 0.45, ease: EASE_OUT }}
              >
                <div className={`p-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] transition-colors duration-300 group-hover:border-white/[0.1] ${feature.color}`}>
                  <feature.icon className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors duration-200">
                  {feature.text}
                </span>
              </motion.div>
            ))}
          </div>

          {/* Stats */}
          <motion.div
            className="grid grid-cols-3 gap-3"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.45, ease: EASE_OUT }}
          >
            {stats.map((stat) => (
              <div key={stat.label} className="text-center p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <div className="text-xl font-bold text-white tracking-tight">{stat.value}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      {/* Right Form — 60% on desktop */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12 bg-[#0B1020] relative overflow-y-auto">
        {/* Subtle ambient on form side */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/[0.02] rounded-full blur-[120px] pointer-events-none" />

        {/* Mobile logo */}
        <div className="lg:hidden absolute top-5 left-5 flex items-center gap-2.5 z-10">
          <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
            <Shield className="h-5 w-5 text-primary" />
          </div>
          <span className="text-base font-semibold text-white tracking-tight">DevArchAI</span>
        </div>

        <motion.div
          className="w-full max-w-[420px] relative z-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_OUT }}
        >
          {children}
        </motion.div>
      </div>
    </div>
  )
}
