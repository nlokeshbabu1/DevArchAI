import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Play, GitBranch, FolderGit2, Search, FileText,
  Shield, Eye, Package, Box, Grid3x3, FileCode,
  Terminal, Users, Globe, Server, Database, Cloud,
  Gauge, AlertTriangle, Lock, ExternalLink, Check,
  ArrowRight, Sparkles, Zap, Layers, Cpu, Rocket,
  ChevronRight
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { Button, Card, SeverityBadge, CodeBlock } from '../ui-animated'
import { useState, useEffect } from 'react'

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 }
  }
}

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 }
}

// ===== Welcome Hero =====
function WelcomeHero({ onStartScan }: { onStartScan: () => void }) {
  const navigate = useNavigate()

  return (
    <motion.div
      variants={item}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-900/40 via-purple-900/20 to-background border border-white/10 shadow-2xl shadow-black/30"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,hsl(243_75%_59%/0.12),transparent_50%),radial-gradient(ellipse_at_bottom_left,hsl(190_75%_59%/0.08),transparent_50%)] pointer-events-none" />
      <div className="relative p-8 md:p-12">
        <div className="max-w-2xl">
          <motion.div className="flex items-center gap-2 mb-4" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
            <div className="p-1.5 rounded-lg bg-primary/20 border border-primary/40">
              <Shield className="h-4 w-4 text-primary" />
            </div>
            <span className="text-xs font-medium text-primary uppercase tracking-wider">DevSecOps Security Platform</span>
          </motion.div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground leading-tight mb-4">
            Secure Your DevOps Stack<br />
            <span className="bg-gradient-to-r from-primary via-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Before Production
            </span>
          </h1>
          <p className="text-sm md:text-base text-muted-foreground leading-relaxed mb-8 max-w-xl">
            Analyze repositories for Terraform, Kubernetes, Docker, CI/CD, secrets, dependencies,
            cloud security, and AI-powered remediation — all in one platform.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={onStartScan}
              icon={<Play className="h-4 w-4" />}
              glow
            >
              Start First Scan
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => navigate('/repositories')}
              icon={<FolderGit2 className="h-4 w-4" />}
            >
              Import Repository
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ===== Quick Start Checklist =====
const checklistItems = [
  { key: 'connect', label: 'Connect Git Provider', icon: GitBranch, duration: '2 min' },
  { key: 'import', label: 'Import Repository', icon: FolderGit2, duration: '1 min' },
  { key: 'scan', label: 'Run First Scan', icon: Search, duration: '5 min' },
  { key: 'review', label: 'Review Findings', icon: FileText, duration: '3 min' },
  { key: 'export', label: 'Export Report', icon: FileCode, duration: '1 min' },
]

function QuickStartChecklist() {
  const navigate = useNavigate()
  const [completed, setCompleted] = useState<Set<string>>(new Set())
  const [hoveredStep, setHoveredStep] = useState<string | null>(null)

  const toggleStep = (key: string) => {
    setCompleted((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const progress = Math.round((completed.size / checklistItems.length) * 100)

  return (
    <motion.div variants={item} className="rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Quick Start</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Get started with DevArchAI</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">{progress}%</span>
          <div className="h-1.5 w-20 rounded-full bg-white/5 overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-primary to-indigo-400"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>
        </div>
      </div>
      <div className="space-y-1.5">
        {checklistItems.map((step, i) => {
          const isDone = completed.has(step.key)
          const isHovered = hoveredStep === step.key

          return (
            <motion.div
              key={step.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className={cn(
                'flex items-center gap-3 p-2.5 rounded-xl cursor-pointer transition-all duration-200',
                isDone ? 'bg-primary/10 border border-primary/20' : 'bg-white/5 border border-white/5',
                isHovered && !isDone && 'bg-white/[0.08] border-white/10'
              )}
              onClick={() => toggleStep(step.key)}
              onMouseEnter={() => setHoveredStep(step.key)}
              onMouseLeave={() => setHoveredStep(null)}
            >
              <div className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center transition-all duration-300',
                isDone
                  ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/30'
                  : 'bg-white/10 text-muted-foreground border border-white/20'
              )}>
                {isDone ? (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  >
                    <Check className="h-3.5 w-3.5" />
                  </motion.div>
                ) : (
                  <span className="text-[10px] font-bold">{i + 1}</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className={cn(
                  'text-sm font-medium transition-colors duration-200',
                  isDone ? 'text-primary' : 'text-foreground'
                )}>
                  {step.label}
                </p>
              </div>
              <span className="text-[10px] text-muted-foreground">{step.duration}</span>
            </motion.div>
          )
        })}
      </div>
      <button
        onClick={() => navigate('/integrations')}
        className="mt-3 w-full py-2 rounded-xl text-xs font-medium text-primary bg-primary/10 border border-primary/20 hover:bg-primary/20 transition-colors duration-200"
      >
        {completed.size === checklistItems.length ? 'All Complete — Explore Dashboard' : 'Connect Git Provider →'}
      </button>
    </motion.div>
  )
}

// ===== Scan Coverage Grid =====
const coverageItems = [
  { icon: Shield, title: 'Repository Security', desc: 'Comprehensive code and config analysis', color: 'from-blue-500/20 to-blue-600/10', border: 'border-blue-500/30', iconBg: 'bg-blue-500/20', textColor: 'text-blue-400' },
  { icon: Eye, title: 'Secrets Detection', desc: 'Find leaked credentials and tokens', color: 'from-red-500/20 to-red-600/10', border: 'border-red-500/30', iconBg: 'bg-red-500/20', textColor: 'text-red-400' },
  { icon: Package, title: 'Dependency Security', desc: 'SCA for vulnerable packages', color: 'from-purple-500/20 to-purple-600/10', border: 'border-purple-500/30', iconBg: 'bg-purple-500/20', textColor: 'text-purple-400' },
  { icon: Box, title: 'Docker Security', desc: 'Container image and config scanning', color: 'from-cyan-500/20 to-cyan-600/10', border: 'border-cyan-500/30', iconBg: 'bg-cyan-500/20', textColor: 'text-cyan-400' },
  { icon: Grid3x3, title: 'Kubernetes Security', desc: 'K8s manifest and admission audit', color: 'from-indigo-500/20 to-indigo-600/10', border: 'border-indigo-500/30', iconBg: 'bg-indigo-500/20', textColor: 'text-indigo-400' },
  { icon: Terminal, title: 'Terraform Security', desc: 'IaC misconfiguration detection', color: 'from-violet-500/20 to-violet-600/10', border: 'border-violet-500/30', iconBg: 'bg-violet-500/20', textColor: 'text-violet-400' },
  { icon: Cpu, title: 'CI/CD Security', desc: 'Pipeline integrity and secret exposure', color: 'from-orange-500/20 to-orange-600/10', border: 'border-orange-500/30', iconBg: 'bg-orange-500/20', textColor: 'text-orange-400' },
  { icon: Cloud, title: 'Cloud Security', desc: 'AWS/GCP/Azure posture assessment', color: 'from-sky-500/20 to-sky-600/10', border: 'border-sky-500/30', iconBg: 'bg-sky-500/20', textColor: 'text-sky-400' },
  { icon: Sparkles, title: 'AI Remediation', desc: 'Automated fix suggestions with code', color: 'from-emerald-500/20 to-emerald-600/10', border: 'border-emerald-500/30', iconBg: 'bg-emerald-500/20', textColor: 'text-emerald-400' },
]

function CoverageGrid() {
  return (
    <motion.div variants={item}>
      <h3 className="text-sm font-semibold text-foreground mb-3">Scan Coverage</h3>
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-3">
        {coverageItems.map((c, i) => {
          const Icon = c.icon
          return (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.03 }}
              className={cn(
                'p-3.5 rounded-xl border bg-gradient-to-br transition-all duration-200',
                c.color, c.border,
                'hover:border-white/30 hover:shadow-lg hover:-translate-y-0.5 cursor-default'
              )}
            >
              <div className={cn('p-2 rounded-lg w-fit border border-white/10 mb-2.5', c.iconBg)}>
                <Icon className={cn('h-4 w-4', c.textColor)} />
              </div>
              <h4 className="text-xs font-semibold text-foreground">{c.title}</h4>
              <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{c.desc}</p>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

// ===== Example Findings =====
const demoFindings = [
  { severity: 'critical' as const, title: 'AWS Security Group Open To Internet', file: 'main.tf', line: 24 },
  { severity: 'high' as const, title: 'Docker Container Running As Root', file: 'Dockerfile', line: 8 },
  { severity: 'high' as const, title: 'Terraform Public S3 Bucket', file: 's3.tf', line: 15 },
  { severity: 'medium' as const, title: 'Missing Kubernetes Resource Limits', file: 'deployment.yaml', line: 32 },
  { severity: 'low' as const, title: 'Missing CI/CD Caching', file: '.gitlab-ci.yml', line: 5 },
]

function ExampleFindings() {
  return (
    <motion.div variants={item}>
      <h3 className="text-sm font-semibold text-foreground mb-3">Example Findings</h3>
      <div className="rounded-xl border border-white/10 overflow-hidden">
        <div className="divide-y divide-white/5">
          {demoFindings.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.04 }}
              className="flex items-center gap-3 p-3 hover:bg-white/[0.04] transition-colors"
            >
              <SeverityBadge severity={f.severity} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{f.title}</p>
                <p className="text-[10px] text-muted-foreground">{f.file}:{f.line}</p>
              </div>
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}

// ===== AI Remediation Preview =====
function AiRemediationPreview() {
  return (
    <motion.div variants={item}>
      <h3 className="text-sm font-semibold text-foreground mb-3">AI Remediation Preview</h3>
      <div className="rounded-xl border border-white/10 overflow-hidden">
        <div className="p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex-shrink-0 mt-0.5">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <div className="space-y-1.5 min-w-0">
              <div className="flex items-center gap-2">
                <span className="badge badge-critical text-[10px]">Critical</span>
                <span className="text-xs font-medium text-foreground">AWS S3 Bucket Publicly Accessible</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                The S3 bucket <code className="text-primary bg-primary/10 px-1 rounded text-[10px]">devops-artifacts</code> has <code className="text-red-400 bg-red-500/10 px-1 rounded text-[10px]">public-read</code> ACL enabled, exposing sensitive artifacts.
              </p>
              <div className="bg-black/30 rounded-lg p-3 border border-white/5">
                <div className="flex items-center gap-2 mb-1.5">
                  <FileCode className="h-3 w-3 text-muted-foreground" />
                  <span className="text-[10px] font-mono text-muted-foreground">s3.tf:15</span>
                </div>
                <pre className="text-[10px] font-mono leading-relaxed">
                  <span className="text-red-400">- acl = "public-read"</span>
                  {'\n'}
                  <span className="text-green-400">+ acl = "private"</span>
                </pre>
              </div>
              <p className="text-[10px] text-muted-foreground flex items-center gap-1.5">
                <span className="text-green-400">Expected Impact:</span> Prevents data exposure, <span className="text-primary">93% confidence</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ===== Scan Workflow =====
const workflowSteps = [
  { icon: FolderGit2, label: 'Repository' },
  { icon: Eye, label: 'Secret Scan' },
  { icon: Package, label: 'Dependency Scan' },
  { icon: Box, label: 'Docker Scan' },
  { icon: Grid3x3, label: 'Kubernetes Scan' },
  { icon: Terminal, label: 'Terraform Scan' },
  { icon: Cpu, label: 'CI/CD Scan' },
  { icon: Cloud, label: 'Cloud Analysis' },
  { icon: Sparkles, label: 'AI Remediation' },
  { icon: FileText, label: 'Reports' },
]

function ScanWorkflow() {
  return (
    <motion.div variants={item}>
      <h3 className="text-sm font-semibold text-foreground mb-3">Scan Pipeline</h3>
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-2 min-w-max">
          {workflowSteps.map((step, i) => {
            const Icon = step.icon
            return (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.03 }}
                className="flex items-center gap-2"
              >
                <div className="flex flex-col items-center gap-1.5">
                  <div className={cn(
                    'p-2 rounded-xl border transition-all duration-300',
                    i === workflowSteps.length - 1
                      ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400 shadow-lg shadow-emerald-500/20'
                      : 'bg-white/10 border-white/20 text-muted-foreground'
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className={cn(
                    'text-[9px] font-medium whitespace-nowrap',
                    i === workflowSteps.length - 1 ? 'text-emerald-400' : 'text-muted-foreground'
                  )}>
                    {step.label}
                  </span>
                </div>
                {i < workflowSteps.length - 1 && (
                  <div className="flex items-center mb-5">
                    <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}

// ===== Main Onboarding View =====
interface OnboardingViewProps {
  onStartScan: () => void
}

export function OnboardingView({ onStartScan }: OnboardingViewProps) {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <WelcomeHero onStartScan={onStartScan} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <QuickStartChecklist />
        </div>
        <div className="lg:col-span-2 space-y-6">
          <CoverageGrid />
          <div className="grid gap-6 sm:grid-cols-2">
            <ExampleFindings />
            <AiRemediationPreview />
          </div>
          <ScanWorkflow />
        </div>
      </div>
    </motion.div>
  )
}
