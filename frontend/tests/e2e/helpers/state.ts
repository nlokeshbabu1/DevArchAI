import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

export interface E2eState {
  apiBase?: string
  email?: string
  password?: string
  accessToken?: string
  guestScanId?: string
  guestSessionToken?: string
  guestScanStatus?: string
  guestScanTerminal?: boolean
  guestFindingsCount?: number
  repositoryUrl?: string
  database?: { host: string; port: number; name: string }
  error?: string
}

const statePath = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '.e2e-state.json')

export function loadE2eState(): E2eState {
  if (!fs.existsSync(statePath)) {
    return { error: 'missing_state_file' }
  }
  return JSON.parse(fs.readFileSync(statePath, 'utf-8')) as E2eState
}

export function requireGuestScan(state: E2eState): { scanId: string; sessionToken: string } {
  if (!state.guestScanId || !state.guestSessionToken) {
    throw new Error('E2E guest scan not seeded — run scripts/e2e-prepare-and-seed.py with API up')
  }
  return { scanId: state.guestScanId, sessionToken: state.guestSessionToken }
}