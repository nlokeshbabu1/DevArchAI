import { useState, useEffect, useRef, useMemo, memo, type ReactNode } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  GitBranch, Shield, Brain, FileText,
  CheckCircle2, AlertTriangle, Box, Hexagon, Layers,
  ArrowRight, Zap, Search, KeyRound,
} from 'lucide-react'

// ─── Timing ───────────────────────────────────────────────
const LOOP = 10_000
const ENTER = 300
const EXIT = 250
const STAGES = [
  { start: 0,    dur: 1000, label: 'Import',    icon: GitBranch  },
  { start: 1000, dur: 1000, label: 'Detect',    icon: Search     },
  { start: 2000, dur: 1000, label: 'Docker',    icon: Box        },
  { start: 3000, dur: 1000, label: 'K8s',       icon: Hexagon    },
  { start: 4000, dur: 1000, label: 'Terraform', icon: Layers     },
  { start: 5000, dur: 1100, label: 'Secrets',   icon: KeyRound   },
  { start: 6100, dur: 1700, label: 'AI',        icon: Brain      },
  { start: 7800, dur: 1900, label: 'Report',    icon: FileText   },
] as const
const TIMELINE = ['Import', 'Detect', 'Docker', 'K8s', 'TF', 'Secrets', 'AI', 'Report'] as const

// ─── Easing ───────────────────────────────────────────────
const EASE_OUT = [0.16, 1, 0.3, 1] as const
const EASE_SNAP = [0.22, 1, 0.36, 1] as const

// ─── Hooks ────────────────────────────────────────────────
function useTimer(enabled: boolean) {
  const [t, setT] = useState(0)
  const start = useRef(0)
  const raf = useRef(0)

  useEffect(() => {
    if (!enabled) {
      return
    }
    start.current = performance.now()
    const tick = (now: number) => {
      setT((now - start.current) % LOOP)
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [enabled])

  return t
}

// ─── Animation math ───────────────────────────────────────
function stageOpacity(t: number, s: typeof STAGES[number]) {
  const e = t - s.start
  if (e < 0 || e > s.dur) {
    return 0
  }
  const fadeIn = Math.min(e / ENTER, 1)
  const fadeOut = Math.min((s.dur - e) / EXIT, 1)
  return Math.min(fadeIn, fadeOut)
}

// Stage index maps 1:1 to the timeline (8 stages → 8 steps)
function activeIdx(t: number) {
  for (let i = STAGES.length - 1; i >= 0; i--) {
    if (t >= STAGES[i].start) {
      return i
    }
  }
  return 0
}

function easeOutQuart(x: number) {
  return 1 - Math.pow(1 - x, 4)
}

// ─── StageCard ────────────────────────────────────────────
function StageCard({ opacity, children }: { opacity: number; children: ReactNode }) {
  if (opacity <= 0) {
    return null
  }
  return (
    <div
      className="absolute inset-0 flex items-center justify-center p-4 sm:p-6"
      style={{ opacity, willChange: 'opacity' }}
    >
      {children}
    </div>
  )
}

// ─── GlassCard ────────────────────────────────────────────
function GlassCard({
  children, className = '', glow = false,
}: {
  children: ReactNode; className?: string; glow?: boolean
}) {
  return (
    <div className={`relative rounded-xl border border-white/[0.08] bg-[#0f1729]/95 backdrop-blur-sm ${className}`}>
      {glow && (
        <div className="absolute -inset-px rounded-xl bg-gradient-to-b from-primary/[0.06] to-transparent pointer-events-none" />
      )}
      {children}
    </div>
  )
}

// ─── ProgressBar ──────────────────────────────────────────
const ProgressBar = memo(function ProgressBar({
  label, progress, color, delay = 0,
}: {
  label: string; progress: number; color: string; delay?: number
}) {
  const adjusted = Math.max(0, Math.min(1, (progress - delay) / (1 - delay)))
  const pct = easeOutQuart(adjusted) * 100

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-slate-400 font-medium">{label}</span>
        <span className="text-[10px] text-slate-500 tabular-nums">{Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.15, ease: 'linear' }}
        />
      </div>
    </div>
  )
})

// ─── Timeline ─────────────────────────────────────────────
function Timeline({ active }: { active: number }) {
  return (
    <div className="flex items-center justify-between px-2 pt-3 pb-1">
      {TIMELINE.map((label, i) => {
        const done = i < active
        const current = i === active
        return (
          <div key={label} className="flex items-center flex-1 last:flex-initial">
            <div className="flex flex-col items-center gap-1">
              <div className={`
                w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold
                transition-all duration-500
                ${done ? 'bg-primary/20 text-primary border border-primary/30' :
                  current ? 'bg-primary text-white border border-primary shadow-[0_0_8px_hsl(var(--primary)/0.3)]' :
                  'bg-white/[0.04] text-slate-500 border border-white/[0.06]'}
              `}>
                {done ? <CheckCircle2 className="w-2.5 h-2.5" /> : i + 1}
              </div>
              <span className={`hidden sm:inline text-[9px] font-medium transition-colors duration-300 ${
                current ? 'text-primary' : done ? 'text-slate-400' : 'text-slate-500/60'
              }`}>
                {label}
              </span>
            </div>
            {i < TIMELINE.length - 1 && (
              <div className="flex-1 mx-1 sm:mx-1.5 mt-[-14px]">
                <div className="h-px bg-white/[0.06] relative overflow-hidden">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-primary/40"
                    initial={{ width: '0%' }}
                    animate={{ width: done ? '100%' : current ? '50%' : '0%' }}
                    transition={{ duration: 0.6, ease: EASE_OUT }}
                  />
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── TitleBar ─────────────────────────────────────────────
function TitleBar() {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.06]">
      <div className="flex gap-1.5">
        <div className="w-2 h-2 rounded-full bg-red-500/60" />
        <div className="w-2 h-2 rounded-full bg-yellow-500/60" />
        <div className="w-2 h-2 rounded-full bg-green-500/60" />
      </div>
      <div className="flex-1 flex justify-center">
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-white/[0.03] border border-white/[0.04]">
          <Shield className="w-2.5 h-2.5 text-primary/60" />
          <span className="text-[10px] text-slate-400 font-medium">DevArchAI</span>
        </div>
      </div>
      <div className="w-8" />
    </div>
  )
}

// ─── Stage 1: Import ──────────────────────────────────────
function ImportStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden">
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <GitBranch className="w-3 h-3 text-primary" />
        <span className="text-[10px] font-medium text-slate-300">Repository Import</span>
      </div>
      <div className="p-3 space-y-3">
        <div className="flex items-start gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
            <GitBranch className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">devarch/infra-config</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Terraform + Docker + K8s</p>
          </div>
        </div>
        <div className="space-y-1">
          {['main.tf', 'Dockerfile', '.github/workflows/ci.yml', 'k8s/deployment.yaml'].map((f, i) => (
            <motion.div
              key={f}
              className="flex items-center gap-1.5 px-2 py-1 rounded bg-white/[0.02]"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 + i * 0.12, duration: 0.35, ease: EASE_OUT }}
            >
              <div className="w-1 h-1 rounded-full bg-green-400/70" />
              <span className="text-[10px] text-slate-400 font-mono">{f}</span>
            </motion.div>
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-primary/80">
          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          <span className="font-medium">Connected</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 2: Secrets Scan ───────────────────────────────
function SecretsScanStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden" glow>
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <KeyRound className="w-3 h-3 text-red-400" />
        <span className="text-[10px] font-medium text-slate-300">Secrets Scan</span>
      </div>
      <div className="p-3 space-y-2.5">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-red-500/[0.08] border border-red-500/20">
          <KeyRound className="w-3 h-3 text-red-400" />
          <span className="text-[10px] font-medium text-red-300">Leaked credentials detected</span>
        </div>
        <div className="space-y-1.5">
          {[
            { label: 'AWS Access Key detection', color: 'bg-red-400/70' },
            { label: 'GitHub Personal Token', color: 'bg-orange-400/70' },
            { label: 'SSH private key exposure', color: 'bg-amber-400/70' },
            { label: 'Database connection strings', color: 'bg-blue-400/70' },
          ].map((item, i) => (
            <ProgressBar key={item.label} label={item.label} progress={0.9} color={item.color} delay={i * 0.08} />
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-red-400/80">
          <AlertTriangle className="w-3 h-3" />
          <span className="font-medium">5 secrets exposed</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 3: Detect ──────────────────────────────────────
const TECHS = [
  { name: 'Terraform', icon: Layers, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
  { name: 'Docker', icon: Box, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
  { name: 'GitHub Actions', icon: GitBranch, color: 'text-slate-300', bg: 'bg-slate-500/10', border: 'border-slate-500/20' },
  { name: 'Kubernetes', icon: Hexagon, color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20' },
]

function DetectStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden">
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <Search className="w-3 h-3 text-purple-400" />
        <span className="text-[10px] font-medium text-slate-300">Technology Detection</span>
      </div>
      <div className="p-3 relative">
        {/* Connector lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
          <defs>
            <linearGradient id="conn-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(252 100% 68% / 0)" />
              <stop offset="50%" stopColor="hsl(252 100% 68% / 0.2)" />
              <stop offset="100%" stopColor="hsl(252 100% 68% / 0)" />
            </linearGradient>
          </defs>
          {/* Horizontal connector */}
          <motion.line
            x1="25%" y1="50%" x2="75%" y2="50%"
            stroke="url(#conn-grad)" strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.8, ease: EASE_OUT }}
          />
          {/* Vertical connector */}
          <motion.line
            x1="50%" y1="25%" x2="50%" y2="75%"
            stroke="url(#conn-grad)" strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ delay: 0.7, duration: 0.8, ease: EASE_OUT }}
          />
        </svg>

        <div className="grid grid-cols-2 gap-2 relative z-10">
          {TECHS.map((tech, i) => {
            const Icon = tech.icon
            return (
              <motion.div
                key={tech.name}
                className={`flex items-center gap-2 px-2.5 py-2 rounded-lg border ${tech.border} ${tech.bg} relative`}
                initial={{ opacity: 0, scale: 0.9, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.15, duration: 0.4, ease: EASE_SNAP }}
              >
                <Icon className={`w-3.5 h-3.5 ${tech.color}`} />
                <span className="text-[10px] font-medium text-slate-300">{tech.name}</span>
                <motion.div
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-green-400"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.5 + i * 0.15, duration: 0.2, ease: EASE_SNAP }}
                />
              </motion.div>
            )
          })}
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 4: Docker Scan ──────────────────────────────────
function DockerScanStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden" glow>
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <Box className="w-3 h-3 text-blue-400" />
        <span className="text-[10px] font-medium text-slate-300">Docker Security Scan</span>
      </div>
      <div className="p-3 space-y-2.5">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-blue-500/[0.08] border border-blue-500/20">
          <Box className="w-3 h-3 text-blue-400" />
          <span className="text-[10px] font-medium text-blue-300">Dockerfile</span>
        </div>
        <div className="space-y-1.5">
          {[
            { label: 'Base image vulnerabilities', color: 'bg-red-400/70' },
            { label: 'Root user detection', color: 'bg-amber-400/70' },
            { label: 'Secret exposure', color: 'bg-orange-400/70' },
            { label: 'Layer optimization', color: 'bg-green-400/70' },
          ].map((item, i) => (
            <ProgressBar key={item.label} label={item.label} progress={0.85} color={item.color} delay={i * 0.08} />
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-blue-400/80">
          <CheckCircle2 className="w-3 h-3" />
          <span className="font-medium">4 findings</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 5: Kubernetes Scan ───────────────────────────────
function KubernetesScanStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden" glow>
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <Hexagon className="w-3 h-3 text-cyan-400" />
        <span className="text-[10px] font-medium text-slate-300">Kubernetes Security Scan</span>
      </div>
      <div className="p-3 space-y-2.5">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-cyan-500/[0.08] border border-cyan-500/20">
          <Hexagon className="w-3 h-3 text-cyan-400" />
          <span className="text-[10px] font-medium text-cyan-300">deployment.yaml</span>
        </div>
        <div className="space-y-1.5">
          {[
            { label: 'Pod security policies', color: 'bg-red-400/70' },
            { label: 'Privileged container check', color: 'bg-amber-400/70' },
            { label: 'Resource limits', color: 'bg-blue-400/70' },
            { label: 'Network policies', color: 'bg-purple-400/70' },
          ].map((item, i) => (
            <ProgressBar key={item.label} label={item.label} progress={0.78} color={item.color} delay={i * 0.08} />
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-cyan-400/80">
          <CheckCircle2 className="w-3 h-3" />
          <span className="font-medium">3 findings</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 6: Terraform Scan ────────────────────────────────
function TerraformScanStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden" glow>
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <Layers className="w-3 h-3 text-purple-400" />
        <span className="text-[10px] font-medium text-slate-300">Terraform Security Scan</span>
      </div>
      <div className="p-3 space-y-2.5">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-purple-500/[0.08] border border-purple-500/20">
          <Layers className="w-3 h-3 text-purple-400" />
          <span className="text-[10px] font-medium text-purple-300">main.tf</span>
        </div>
        <div className="space-y-1.5">
          {[
            { label: 'Public S3 bucket detection', color: 'bg-red-400/70' },
            { label: 'Unencrypted storage', color: 'bg-orange-400/70' },
            { label: 'Overly permissive IAM', color: 'bg-amber-400/70' },
            { label: 'Missing logging', color: 'bg-green-400/70' },
          ].map((item, i) => (
            <ProgressBar key={item.label} label={item.label} progress={0.92} color={item.color} delay={i * 0.08} />
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-purple-400/80">
          <CheckCircle2 className="w-3 h-3" />
          <span className="font-medium">5 findings</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 8: AI Analysis ─────────────────────────────────
function AIStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden" glow>
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <Brain className="w-3 h-3 text-primary" />
        <span className="text-[10px] font-medium text-slate-300">AI Recommendation</span>
      </div>
      <div className="p-3 space-y-3">
        {/* Finding header */}
        <div className="flex items-start gap-2">
          <div className="w-5 h-5 rounded bg-red-500/15 border border-red-500/25 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertTriangle className="w-3 h-3 text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Critical Issue</span>
            </div>
            <p className="text-xs font-semibold text-white">Hardcoded AWS Secret</p>
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: 'Impact', value: 'High', color: 'text-orange-400' },
            { label: 'Risk Reduction', value: '92%', color: 'text-green-400' },
          ].map((d) => (
            <div key={d.label} className="px-2 py-1.5 rounded bg-white/[0.02] border border-white/[0.04]">
              <p className="text-[9px] text-slate-500 uppercase tracking-wider">{d.label}</p>
              <p className={`text-xs font-semibold ${d.color}`}>{d.value}</p>
            </div>
          ))}
        </div>

        {/* Root cause */}
        <div className="space-y-1">
          <p className="text-[9px] text-slate-500 uppercase tracking-wider">Root Cause</p>
          <p className="text-[11px] text-slate-300 leading-relaxed">Credential committed in repository</p>
        </div>

        {/* Fix */}
        <div className="space-y-1">
          <p className="text-[9px] text-slate-500 uppercase tracking-wider">Recommended Fix</p>
          <div className="flex items-start gap-1.5">
            <ArrowRight className="w-3 h-3 text-primary mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-slate-300 leading-relaxed">Move secret to AWS Secrets Manager</p>
          </div>
        </div>

        {/* Action indicator */}
        <div className="flex items-center gap-1.5 text-[10px] text-primary/80 pt-0.5">
          <Zap className="w-3 h-3" />
          <span className="font-medium">Auto-fix available</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Stage 6: Report ──────────────────────────────────────
function ReportStage() {
  return (
    <GlassCard className="w-full max-w-sm overflow-hidden">
      <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
        <FileText className="w-3 h-3 text-green-400" />
        <span className="text-[10px] font-medium text-slate-300">Report Generated</span>
        <CheckCircle2 className="w-3 h-3 text-green-400 ml-auto" />
      </div>
      <div className="p-3 space-y-3">
        {/* Score */}
        <div className="flex items-center gap-3">
          <div className="relative w-12 h-12">
            <svg className="w-full h-full" viewBox="0 0 48 48">
              <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="3" />
              <motion.circle
                cx="24" cy="24" r="20" fill="none" stroke="hsl(142 76% 36%)" strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={125.6}
                initial={{ strokeDashoffset: 125.6 }}
                animate={{ strokeDashoffset: 125.6 * 0.14 }}
                transition={{ duration: 1, ease: EASE_OUT, delay: 0.2 }}
                style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[11px] font-bold text-green-400">86</span>
            </div>
          </div>
          <div className="flex-1 space-y-1">
            <p className="text-xs font-semibold text-white">Security Score</p>
            <div className="flex items-center gap-3">
              {[
                { n: 3, l: 'Critical', c: 'text-red-400' },
                { n: 7, l: 'High', c: 'text-orange-400' },
                { n: 12, l: 'Medium', c: 'text-yellow-400' },
              ].map((s) => (
                <div key={s.l} className="text-center">
                  <p className={`text-xs font-bold tabular-nums ${s.c}`}>{s.n}</p>
                  <p className="text-[8px] text-slate-500">{s.l}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Export formats */}
        <div className="flex gap-1.5">
          {['PDF', 'JSON', 'SARIF'].map((fmt) => (
            <div key={fmt} className="flex-1 px-2 py-1.5 rounded bg-white/[0.03] border border-white/[0.05] text-center">
              <span className="text-[9px] font-medium text-slate-400">{fmt}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-1.5 text-[10px] text-green-400/80">
          <CheckCircle2 className="w-3 h-3" />
          <span className="font-medium">Report ready for download</span>
        </div>
      </div>
    </GlassCard>
  )
}

// ─── Main Component ───────────────────────────────────────
export function HeroVideo() {
  const prefersReducedMotion = useReducedMotion()
  const t = useTimer(!prefersReducedMotion)
  const idx = activeIdx(t)

  const stages = useMemo(() => [
    { el: <ImportStage />, ...STAGES[0] },
    { el: <DetectStage />, ...STAGES[1] },
    { el: <DockerScanStage />, ...STAGES[2] },
    { el: <KubernetesScanStage />, ...STAGES[3] },
    { el: <TerraformScanStage />, ...STAGES[4] },
    { el: <SecretsScanStage />, ...STAGES[5] },
    { el: <AIStage />, ...STAGES[6] },
    { el: <ReportStage />, ...STAGES[7] },
  ], [])

  if (prefersReducedMotion) {
    return (
      <motion.div
        className="relative w-full max-w-2xl mx-auto"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.4, ease: EASE_OUT }}
      >
        <GlassCard className="overflow-hidden" glow>
          <TitleBar />
          <div className="p-4 sm:p-6 min-h-[280px] flex items-center justify-center">
            <ImportStage />
          </div>
          <div className="border-t border-white/[0.06] px-3 py-2">
            <Timeline active={0} />
          </div>
        </GlassCard>
      </motion.div>
    )
  }

  return (
    <motion.div
      className="relative w-full max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.4, ease: EASE_OUT }}
    >
      {/* Ambient glow */}
      <div className="absolute -inset-8 bg-primary/[0.03] rounded-3xl blur-3xl pointer-events-none" />

      <GlassCard className="overflow-hidden" glow>
        <TitleBar />

        {/* Stage content area */}
        <div className="relative min-h-[260px] sm:min-h-[300px] lg:min-h-[340px]">
          {stages.map((s, i) => (
            <StageCard key={i} opacity={stageOpacity(t, s)}>
              {s.el}
            </StageCard>
          ))}

          {/* Moving glow overlay */}
          <motion.div
            className="absolute inset-0 pointer-events-none"
            animate={{
              background: [
                'radial-gradient(ellipse at 20% 50%, hsl(252 100% 68% / 0.02) 0%, transparent 60%)',
                'radial-gradient(ellipse at 80% 50%, hsl(252 100% 68% / 0.02) 0%, transparent 60%)',
                'radial-gradient(ellipse at 20% 50%, hsl(252 100% 68% / 0.02) 0%, transparent 60%)',
              ],
            }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
          />
        </div>

        {/* Timeline */}
        <div className="border-t border-white/[0.06] px-3 py-2">
          <Timeline active={idx} />
        </div>
      </GlassCard>
    </motion.div>
  )
}