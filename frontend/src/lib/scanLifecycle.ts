import type { ScanStage, StageMetadata, TechnologyResult } from '../types'

const LEGACY_STAGE_MAP: Record<string, ScanStage> = {
  repository_connection: 'connecting_repository',
  clone: 'cloning',
  security_scan: 'scanning',
  detect_technologies: 'detecting_technologies',
  analyze_findings: 'analyzing',
  connecting: 'connecting_repository',
  cloning: 'cloning',
  technology_detection: 'detecting_technologies',
  scanner_selection: 'scanning',
  scanning: 'scanning',
  normalization: 'analyzing',
  deduplication: 'analyzing',
  report_generation: 'analyzing',
  ai_generation: 'analyzing',
}

export function normalizeLifecycleStage(stage: string | null | undefined): ScanStage | null {
  if (!stage) {return null}
  const mapped = LEGACY_STAGE_MAP[stage]
  if (mapped) {return mapped}
  return stage as ScanStage
}

export function buildDynamicScanSteps(
  baseStages: StageMetadata[],
  technologies: Record<string, TechnologyResult>,
): StageMetadata[] {
  const bases = [...baseStages]
    .filter(s => s.kind !== 'technology')
    .sort((a, b) => a.order - b.order)

  const beforeScan = bases.filter(s =>
    ['queued', 'connecting_repository', 'cloning', 'cloned', 'detecting_technologies'].includes(s.id as string),
  )
  const scanStage = bases.find(s => s.id === 'scanning') || {
    id: 'scanning' as ScanStage,
    label: 'Security scan',
    icon: 'shield',
    order: 5,
    kind: 'base',
  }
  const afterScan = bases.filter(s =>
    ['analyzing', 'scan_completed'].includes(s.id as string),
  )

  const techSteps: StageMetadata[] = Object.values(technologies).map((tech, index) => ({
    id: `tech:${tech.id || tech.technology}` as ScanStage,
    label: tech.name || tech.technology,
    icon: tech.icon || 'cpu',
    order: 50 + index,
    kind: 'technology',
    technology_id: tech.id || tech.technology,
  }))

  return [...beforeScan, scanStage, ...techSteps, ...afterScan]
}

export function technologyStepId(tech: TechnologyResult): string {
  return `tech:${tech.id || tech.technology}`
}
