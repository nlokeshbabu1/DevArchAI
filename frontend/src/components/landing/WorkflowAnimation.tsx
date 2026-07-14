import { useEffect, useState, useCallback, memo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  Github, Download, Layers, Box, Hexagon, GitBranch,
  Shield, Sparkles, CheckCircle, FileText, FileDown
} from 'lucide-react'

const steps = [
  { icon: Github, label: 'Repository' },
  { icon: Download, label: 'Clone' },
  { icon: Layers, label: 'Terraform' },
  { icon: Box, label: 'Docker' },
  { icon: Hexagon, label: 'Kubernetes' },
  { icon: GitBranch, label: 'Actions' },
  { icon: Shield, label: 'Security' },
  { icon: Sparkles, label: 'AI Review' },
  { icon: CheckCircle, label: 'Compliance' },
  { icon: FileText, label: 'Report' },
  { icon: FileDown, label: 'Download' },
]

const StepIcon = memo(function StepIcon({
  Icon,
  label,
  isActive,
  isCurrent,
}: {
  Icon: React.ElementType
  label: string
  isActive: boolean
  isCurrent: boolean
}) {
  return (
    <motion.div
      className="flex flex-col items-center gap-1.5"
      animate={{
        opacity: isActive ? 1 : 0.2,
        scale: isCurrent ? 1.06 : 1,
      }}
      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div
        className={`p-2 sm:p-2.5 rounded-xl border transition-all duration-300 ${
          isCurrent
            ? 'bg-primary/15 border-primary/40 text-primary shadow-lg shadow-primary/15'
            : isActive
              ? 'bg-primary/[0.07] border-primary/20 text-primary/80'
              : 'bg-white/[0.03] border-white/[0.06] text-muted-foreground/40'
        }`}
      >
        <Icon className="h-4 w-4 sm:h-[18px] sm:w-[18px]" />
      </div>
      <span
        className={`text-[9px] sm:text-[10px] whitespace-nowrap transition-colors duration-300 ${
          isActive ? 'text-foreground/70' : 'text-muted-foreground/30'
        }`}
      >
        {label}
      </span>
    </motion.div>
  )
})

const Connector = memo(function Connector({ isActive }: { isActive: boolean }) {
  return (
    <div className="mx-1 sm:mx-1.5 md:mx-2.5">
      <motion.div
        className={`h-px transition-colors duration-300 ${
          isActive ? 'bg-primary/30' : 'bg-white/[0.06]'
        }`}
        style={{ width: 'clamp(6px, 1.5vw, 24px)' }}
        animate={{ scaleX: isActive ? 1 : 0.3 }}
        transition={{ duration: 0.25 }}
      />
    </div>
  )
})

export function WorkflowAnimation() {
  const [activeIndex, setActiveIndex] = useState(-1)
  const prefersReducedMotion = useReducedMotion()

  useEffect(() => {
    if (prefersReducedMotion) {
      setActiveIndex(steps.length - 1)
      return
    }

    let isCancelled = false

    const runCycle = async () => {
      setActiveIndex(-1)
      await new Promise((r) => setTimeout(r, 1000))
      if (isCancelled) return

      for (let i = 0; i < steps.length; i++) {
        if (isCancelled) return
        setActiveIndex(i)
        await new Promise((r) => setTimeout(r, 450))
      }

      if (isCancelled) return
      await new Promise((r) => setTimeout(r, 3000))

      if (!isCancelled) {
        runCycle()
      }
    }

    runCycle()

    return () => {
      isCancelled = true
    }
  }, [prefersReducedMotion])

  return (
    <div className="relative py-4 md:py-6 overflow-hidden rounded-2xl border border-white/[0.04] bg-white/[0.02] backdrop-blur-sm">
      <div className="flex items-center justify-center gap-0.5 sm:gap-1 px-3 sm:px-6" role="img" aria-label="DevArchAI workflow: Repository, Clone, Terraform, Docker, Kubernetes, Actions, Security, AI Review, Compliance, Report, Download">
        {steps.map((step, index) => {
          const Icon = step.icon
          const isActive = index <= activeIndex
          const isCurrent = index === activeIndex

          return (
            <div key={step.label} className="flex items-center">
              <StepIcon
                Icon={Icon}
                label={step.label}
                isActive={isActive}
                isCurrent={isCurrent}
              />
              {index < steps.length - 1 && <Connector isActive={isActive} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
