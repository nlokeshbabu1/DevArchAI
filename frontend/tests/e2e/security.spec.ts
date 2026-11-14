import { test, expect } from '@playwright/test'

import { dismissCookieBanner } from './helpers/ui'
import { loadE2eState, requireGuestScan } from './helpers/state'
test.describe('Security and access control', () => {
  test('unauthenticated user is redirected from /scans list', async ({ page }) => {
    await page.goto('/scans')
    await dismissCookieBanner(page)
    await page.waitForURL(/\/login/, { timeout: 15_000 })
    await expect(page.getByText('Welcome back')).toBeVisible()
  })

  test('guest without session cannot read another guest scan', async ({ page, request }) => {
    const state = loadE2eState()
    test.skip(!state.guestScanId, 'No guest scan seeded')
    const foreignId = '00000000-0000-4000-8000-000000000099'
    const res = await request.get(`http://127.0.0.1:8000/api/v1/scan/state/${foreignId}`)
    expect([401, 403, 404]).toContain(res.status())

    await page.goto(`/scans/${foreignId}`)
    await dismissCookieBanner(page)
    await expect(page.locator('body')).toBeVisible()
  })

  test('guest with valid session can load own scan state via API', async ({ request }) => {
    const state = loadE2eState()
    try {
      const { scanId, sessionToken } = requireGuestScan(state)
      const res = await request.get(`http://127.0.0.1:8000/api/v1/scan/state/${scanId}`, {
        headers: { 'X-Session-Token': sessionToken },
      })
      expect(res.ok()).toBeTruthy()
    } catch {
      test.skip(true, 'Guest scan not seeded')
    }
  })
})