import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import { request, type FullConfig } from '@playwright/test'

const statePath = path.join(path.dirname(fileURLToPath(import.meta.url)), '.e2e-state.json')

export default async function globalSetup(_config: FullConfig): Promise<void> {
  if (!fs.existsSync(statePath)) {
    throw new Error(
      'Missing frontend/tests/e2e/.e2e-state.json — run scripts/e2e-run-playwright.sh or seed-only after backend start',
    )
  }
  const ctx = await request.newContext()
  const res = await ctx.get('http://127.0.0.1:8000/health').catch(() => null)
  await ctx.dispose()
  if (!res?.ok()) {
    throw new Error('E2E backend not healthy at http://127.0.0.1:8000/health')
  }
}