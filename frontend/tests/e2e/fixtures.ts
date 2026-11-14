import { test as base, expect } from '@playwright/test'

import { attachGuestSession, dismissCookieBanner, loginThroughUi } from './helpers/ui'
import { loadE2eState, requireGuestScan } from './helpers/state'

export const test = base.extend<{
  e2eState: ReturnType<typeof loadE2eState>
  authenticatedPage: import('@playwright/test').Page
  guestScanPage: import('@playwright/test').Page
}>({
  e2eState: async ({}, use) => {
    await use(loadE2eState())
  },
  authenticatedPage: async ({ page, e2eState }, use) => {
    test.skip(!e2eState.email || !e2eState.password, 'E2E user not seeded')
    await loginThroughUi(page, { email: e2eState.email!, password: e2eState.password! })
    await use(page)
  },
  guestScanPage: async ({ page, e2eState }, use) => {
    const { scanId, sessionToken } = requireGuestScan(e2eState)
    await attachGuestSession(page, scanId, sessionToken)
    await page.goto(`/scans/${scanId}`)
    await dismissCookieBanner(page)
    await use(page)
  },
})

export { expect }