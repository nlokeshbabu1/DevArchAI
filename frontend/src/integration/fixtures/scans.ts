import type { Scan, UnifiedScanStartResponse } from '../../api/endpoints/scans'

export const FIXTURE_SCAN_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'

export const sampleScanList: Scan[] = [
  {
    id: FIXTURE_SCAN_ID,
    status: 'completed',
    progress: 100,
    branch: 'main',
    repository_url: 'https://github.com/org/sample-repo',
    repository_id: '11111111-2222-3333-4444-555555555555',
    overall_score: 82,
    security_score: 78,
    created_at: '2026-01-01T12:00:00.000Z',
    completed_at: '2026-01-01T12:05:00.000Z',
  },
]

export const sampleScanStartResponse: UnifiedScanStartResponse = {
  scan_id: 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
  status: 'running',
  repository_url: 'https://github.com/org/sample-repo',
  branch: 'main',
  message: 'Scan started',
}
