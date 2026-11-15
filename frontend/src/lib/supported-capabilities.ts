/**
 * Single source of truth for customer-facing technology claims.
 * Aligns with backend scanner registry and dashboard navigation.
 */

import type { LucideIcon } from 'lucide-react'
import {
  Box,
  Cloud,
  GitBranch,
  Github,
  Hexagon,
  Layers,
  Lock,
  Radar,
  Server,
  Shield,
  Workflow,
} from 'lucide-react'

export type CapabilityKind =
  | 'scanner'
  | 'integration'
  | 'iac_detection'
  | 'scan_engine'
  | 'coming_soon'

export interface TechnologyCapability {
  id: string
  name: string
  kind: CapabilityKind
  blurb: string
}

export interface ShowcaseItem {
  id: string
  name: string
  blurb: string
  kind: CapabilityKind
  icon: LucideIcon
}

export interface ShowcaseCategory {
  id: string
  title: string
  description: string
  items: ShowcaseItem[]
}

/** Scanners and rule-engine coverage shown on marketing surfaces */
export const VERIFIED_SCAN_CAPABILITIES: TechnologyCapability[] = [
  { id: 'docker', name: 'Docker', kind: 'scanner', blurb: 'Container images & Dockerfiles' },
  { id: 'kubernetes', name: 'Kubernetes', kind: 'scanner', blurb: 'Manifests & cluster configs' },
  { id: 'terraform', name: 'Terraform', kind: 'scanner', blurb: 'Infrastructure as code' },
  { id: 'helm', name: 'Helm', kind: 'iac_detection', blurb: 'Charts via IaC policies' },
  { id: 'github-actions', name: 'GitHub Actions', kind: 'scanner', blurb: 'Workflow security' },
  { id: 'gitlab-ci', name: 'GitLab CI', kind: 'scanner', blurb: 'Pipeline configs' },
  { id: 'jenkins', name: 'Jenkins', kind: 'iac_detection', blurb: 'Pipeline file detection' },
  { id: 'trivy', name: 'Trivy', kind: 'scan_engine', blurb: 'Vulnerability & misconfig scans' },
  { id: 'checkov', name: 'Checkov', kind: 'scan_engine', blurb: 'Policy checks for IaC' },
  { id: 'gitleaks', name: 'Gitleaks', kind: 'scan_engine', blurb: 'Secret detection' },
]

export const VERIFIED_INTEGRATIONS: TechnologyCapability[] = [
  { id: 'aws', name: 'AWS', kind: 'integration', blurb: 'Cloud account security scans' },
  { id: 'github', name: 'GitHub', kind: 'integration', blurb: 'Repository & OAuth' },
  { id: 'gitlab', name: 'GitLab', kind: 'integration', blurb: 'Repository integration' },
]

export const COMING_SOON_CLOUD: TechnologyCapability[] = [
  { id: 'azure', name: 'Azure', kind: 'coming_soon', blurb: 'Cloud integration' },
  { id: 'gcp', name: 'GCP', kind: 'coming_soon', blurb: 'Cloud integration' },
]

export const TECHNOLOGY_SHOWCASE: ShowcaseCategory[] = [
  {
    id: 'iac',
    title: 'Infrastructure as Code',
    description: 'Policy and misconfiguration checks on Terraform and related IaC in your repository.',
    items: [
      { id: 'terraform', name: 'Terraform', blurb: 'Modules, providers, state posture', kind: 'scanner', icon: Layers },
      { id: 'helm', name: 'Helm', blurb: 'Chart templates via IaC scanners', kind: 'iac_detection', icon: Shield },
    ],
  },
  {
    id: 'containers',
    title: 'Containers & Kubernetes',
    description: 'Dockerfiles, images, and Kubernetes manifests evaluated against security baselines.',
    items: [
      { id: 'docker', name: 'Docker', blurb: 'Dockerfile & image risks', kind: 'scanner', icon: Box },
      { id: 'kubernetes', name: 'Kubernetes', blurb: 'Workload & cluster configs', kind: 'scanner', icon: Hexagon },
    ],
  },
  {
    id: 'cicd',
    title: 'CI/CD security',
    description: 'Pipeline definitions scanned for unsafe patterns — not third-party CI orchestration products.',
    items: [
      { id: 'github-actions', name: 'GitHub Actions', blurb: 'Workflow YAML', kind: 'scanner', icon: Github },
      { id: 'gitlab-ci', name: 'GitLab CI', blurb: '.gitlab-ci.yml', kind: 'scanner', icon: GitBranch },
      { id: 'jenkins', name: 'Jenkins', blurb: 'Jenkinsfile detection', kind: 'iac_detection', icon: Workflow },
    ],
  },
  {
    id: 'cloud',
    title: 'Cloud security',
    description: 'Live cloud posture where integrations exist; additional providers are on the roadmap.',
    items: [
      { id: 'aws', name: 'AWS', blurb: 'Account integration & IaC rules', kind: 'integration', icon: Cloud },
      { id: 'azure', name: 'Azure', blurb: 'Coming soon', kind: 'coming_soon', icon: Server },
      { id: 'gcp', name: 'GCP', blurb: 'Coming soon', kind: 'coming_soon', icon: Cloud },
    ],
  },
  {
    id: 'engines',
    title: 'Scan engines',
    description: 'Registered CLI scanners DevArchAI invokes — distinct from the technologies being analyzed.',
    items: [
      { id: 'checkov', name: 'Checkov', blurb: 'IaC policy engine', kind: 'scan_engine', icon: Layers },
      { id: 'trivy', name: 'Trivy', blurb: 'Vuln & config scanner', kind: 'scan_engine', icon: Radar },
      { id: 'gitleaks', name: 'Gitleaks', blurb: 'Secret detection', kind: 'scan_engine', icon: Lock },
    ],
  },
  {
    id: 'integrations',
    title: 'Repository integrations',
    description: 'Connect source control to clone repos, run scans, and open remediation workflows.',
    items: [
      { id: 'github', name: 'GitHub', blurb: 'OAuth & GitHub App', kind: 'integration', icon: Github },
      { id: 'gitlab', name: 'GitLab', blurb: 'OAuth & project access', kind: 'integration', icon: GitBranch },
    ],
  },
]

export const MARQUEE_TECHNOLOGIES = [
  'Docker',
  'Kubernetes',
  'Helm',
  'Terraform',
  'GitHub Actions',
  'GitLab CI',
  'Jenkins',
  'AWS',
  'Trivy',
  'Checkov',
] as const