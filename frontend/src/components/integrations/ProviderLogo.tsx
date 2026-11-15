import {
  Github,
  Gitlab,
  Cloud,
  Server,
  Container,
  Boxes,
  Webhook,
  Bell,
  Cog,
  Box,
  CircleDot,
  Hexagon,
  Triangle,
  SquareStack,
  Radio,
  Cpu,
  Network,
  Shield,
  Lock,
  FileCode,
  Workflow,
  GitBranch,
} from 'lucide-react'

import { cn } from '@/lib/utils'

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  github: Github,
  gitlab: Gitlab,
  bitbucket: Boxes,
  aws: Cloud,
  azure: Server,
  gcp: Cloud,
  jenkins: Cog,
  circleci: CircleDot,
  kubernetes: Container,
  openshift: Hexagon,
  rancher: Box,
  terraform: Triangle,
  opentofu: Triangle,
  pulumi: SquareStack,
  slack: Webhook,
  teams: Server,
  discord: Bell,
  pagerduty: Radio,
}

const COLOR_MAP: Record<string, string> = {
  github: 'text-white',
  gitlab: 'text-orange-400',
  bitbucket: 'text-blue-400',
  aws: 'text-amber-400',
  azure: 'text-blue-400',
  gcp: 'text-red-400',
  jenkins: 'text-red-400',
  circleci: 'text-green-400',
  kubernetes: 'text-blue-400',
  openshift: 'text-red-400',
  rancher: 'text-green-400',
  terraform: 'text-purple-400',
  opentofu: 'text-purple-400',
  pulumi: 'text-yellow-400',
  slack: 'text-green-400',
  teams: 'text-blue-400',
  discord: 'text-indigo-400',
  pagerduty: 'text-green-400',
}

const BG_MAP: Record<string, string> = {
  github: 'bg-white/10',
  gitlab: 'bg-orange-500/10',
  bitbucket: 'bg-blue-500/10',
  aws: 'bg-amber-500/10',
  azure: 'bg-blue-500/10',
  gcp: 'bg-red-500/10',
  jenkins: 'bg-red-500/10',
  circleci: 'bg-green-500/10',
  kubernetes: 'bg-blue-500/10',
  openshift: 'bg-red-500/10',
  rancher: 'bg-green-500/10',
  terraform: 'bg-purple-500/10',
  opentofu: 'bg-purple-500/10',
  pulumi: 'bg-yellow-500/10',
  slack: 'bg-green-500/10',
  teams: 'bg-blue-500/10',
  discord: 'bg-indigo-500/10',
  pagerduty: 'bg-green-500/10',
}

interface ProviderLogoProps {
  icon: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE_MAP = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
}

export function ProviderLogo({ icon, size = 'md', className }: ProviderLogoProps) {
  const Icon = ICON_MAP[icon] || Cpu
  const color = COLOR_MAP[icon] || 'text-muted-foreground'
  const bg = BG_MAP[icon] || 'bg-white/5'

  return (
    <div className={cn('flex items-center justify-center rounded-lg', bg, className)}>
      <Icon className={cn(SIZE_MAP[size], color)} />
    </div>
  )
}
