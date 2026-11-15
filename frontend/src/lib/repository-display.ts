/**
 * Single source of truth for repository card status on Dashboard + Repositories.
 */

import type { Repository } from '../api/endpoints/repositories'

export type RepositoryDisplayStatus = 'not_scanned' | 'scanning' | 'completed' | 'failed'

export type RepositoryProvider = 'github' | 'gitlab' | 'manual'

export function inferRepositoryProvider(url?: string | null): RepositoryProvider {
  if (!url) {return 'manual'}
  if (url.includes('github.com')) {return 'github'}
  if (url.includes('gitlab.com')) {return 'gitlab'}
  return 'manual'
}

export function isRunningScanStatus(status?: string | null): boolean {
  return status === 'processing' || status === 'pending' || status === 'queued' || status === 'running'
}

export function resolveRepositoryDisplayStatus(
  repo: Repository,
  options?: { locallyScanning?: boolean },
): RepositoryDisplayStatus {
  if (options?.locallyScanning || isRunningScanStatus(repo.scan_status)) {
    return 'scanning'
  }
  if (repo.scan_status === 'failed') {
    return 'failed'
  }
  if (repo.scan_status === 'completed') {
    return 'completed'
  }
  if (repo.last_scan_at || (repo.scan_count ?? 0) > 0) {
    return 'completed'
  }
  return 'not_scanned'
}

export function repositoryStatusLabel(status: RepositoryDisplayStatus | 'all'): string {
  if (status === 'all') {return 'All'}
  if (status === 'not_scanned') {return 'Not Scanned'}
  return status.charAt(0).toUpperCase() + status.slice(1)
}

export function formatRepositoryActivity(repo: Repository, displayStatus: RepositoryDisplayStatus): string {
  if (repo.last_scan_at) {
    const lastScan = new Date(repo.last_scan_at)
    if (!Number.isNaN(lastScan.getTime())) {
      return `${lastScan.toLocaleDateString()} • ${lastScan.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
    }
  }
  if (displayStatus === 'scanning') {
    return 'Scan in progress'
  }
  return 'Never scanned'
}

export function scanActionLabel(displayStatus: RepositoryDisplayStatus): string {
  if (displayStatus === 'completed') {return 'Rescan'}
  if (displayStatus === 'failed') {return 'Retry Scan'}
  return 'Scan'
}

export const REPOSITORY_STATUS_FILTERS = ['all', 'completed', 'scanning', 'not_scanned', 'failed'] as const

export function countRepositoriesByStatus(
  repos: Array<Repository & { displayStatus: RepositoryDisplayStatus }>,
): Record<(typeof REPOSITORY_STATUS_FILTERS)[number], number> {
  return {
    all: repos.length,
    completed: repos.filter((r) => r.displayStatus === 'completed').length,
    scanning: repos.filter((r) => r.displayStatus === 'scanning').length,
    not_scanned: repos.filter((r) => r.displayStatus === 'not_scanned').length,
    failed: repos.filter((r) => r.displayStatus === 'failed').length,
  }
}