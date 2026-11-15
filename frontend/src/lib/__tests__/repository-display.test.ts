import { describe, expect, it } from 'vitest'

import type { Repository } from '../../api/endpoints/repositories'
import {
  resolveRepositoryDisplayStatus,
  inferRepositoryProvider,
  repositoryStatusLabel,
} from '../repository-display'

const baseRepo = (overrides: Partial<Repository> = {}): Repository => ({
  id: '1',
  name: 'demo',
  url: 'https://github.com/org/demo',
  default_branch: 'main',
  is_private: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
})

describe('repository-display', () => {
  it('infers github provider from URL', () => {
    expect(inferRepositoryProvider('https://github.com/a/b')).toBe('github')
    expect(inferRepositoryProvider('https://gitlab.com/a/b')).toBe('gitlab')
  })

  it('maps running scan_status to scanning', () => {
    expect(resolveRepositoryDisplayStatus(baseRepo({ scan_status: 'processing' }))).toBe('scanning')
    expect(
      resolveRepositoryDisplayStatus(baseRepo({ scan_status: 'pending' }), { locallyScanning: true }),
    ).toBe('scanning')
  })

  it('maps completed scans with history to completed', () => {
    expect(
      resolveRepositoryDisplayStatus(
        baseRepo({ scan_status: 'completed', last_scan_at: '2026-01-02T00:00:00Z', scan_count: 2 }),
      ),
    ).toBe('completed')
    expect(
      resolveRepositoryDisplayStatus(baseRepo({ scan_count: 1, last_scan_at: '2026-01-02T00:00:00Z' })),
    ).toBe('completed')
  })

  it('does not mark unknown in-progress without backend status', () => {
    expect(resolveRepositoryDisplayStatus(baseRepo({ scan_count: 3 }))).toBe('completed')
    expect(resolveRepositoryDisplayStatus(baseRepo())).toBe('not_scanned')
  })

  it('labels filters for UI', () => {
    expect(repositoryStatusLabel('not_scanned')).toBe('Not Scanned')
    expect(repositoryStatusLabel('all')).toBe('All')
  })
})