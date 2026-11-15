/**
 * Scan journey E2E — real backend on isolated DB (port 5433 / devarchai_e2e).
 */

import { test, expect } from './fixtures'
import { dismissCookieBanner } from './helpers/ui'
import { requireGuestScan } from './helpers/state'
import { request } from '@playwright/test'

test.describe('Authenticated scan journey', () => {
  test('login, open scan form, and list scans page', async ({ authenticatedPage, e2eState }) => {
    await authenticatedPage.goto('/scan')
    await dismissCookieBanner(authenticatedPage)
    await expect(
      authenticatedPage.getByRole('heading', { name: /Analyze Your DevOps/i }),
    ).toBeVisible()
    await authenticatedPage.goto('/scans')
    await expect(authenticatedPage.getByText(/Filter:|Scan History|scans/i).first()).toBeVisible()
    expect(e2eState.database?.port).toBe(5433)
  })
})

test.describe('Guest scan lifecycle (backend-driven)', () => {
  test('scan page submits repository and navigates to progress route', async ({ page, e2eState }) => {
    test.skip(!e2eState.repositoryUrl, 'No repository fixture')

    await page.goto('/scan')
    await dismissCookieBanner(page)
    await page.getByPlaceholder(/github.com\/org\/repo/i).fill(e2eState.repositoryUrl!)
    await page.getByRole('button', { name: /Analyze Repository/i }).click()
    await page.waitForURL(/\/scans\/[0-9a-f-]{36}/i, { timeout: 60_000 })
    await expect(page.locator('body')).toBeVisible()
  })

  test('guest progress UI matches API terminal status', async ({ guestScanPage, e2eState }) => {
    test.skip(!e2eState.guestScanTerminal, 'Guest scan did not reach terminal state during seed')
    test.info().annotations.push({
      type: 'backend-note',
      description: `Seeded scan status=${e2eState.guestScanStatus}`,
    })
    const { scanId, sessionToken } = requireGuestScan(e2eState)

    const api = await request.newContext({
      extraHTTPHeaders: { 'X-Session-Token': sessionToken },
    })
    const stateRes = await api.get(`http://127.0.0.1:8000/api/v1/scan/state/${scanId}`)
    expect(stateRes.ok()).toBeTruthy()
    const apiState = await stateRes.json()
    await api.dispose()

    await expect(guestScanPage.getByText(/completed|failed|cancelled/i).first()).toBeVisible({
      timeout: 30_000,
    })
    expect(apiState.is_terminal).toBe(true)
    expect(['completed', 'failed', 'cancelled']).toContain(apiState.status)
  })

  test('completed scan shows results dashboard elements', async ({ guestScanPage, e2eState }) => {
    test.skip(e2eState.guestScanStatus !== 'completed', 'Seeded scan not completed')
    await expect(guestScanPage.getByText(/Security|Findings|Score/i).first()).toBeVisible({
      timeout: 45_000,
    })
  })
})

test.describe('Validation and errors', () => {
  test('invalid repository URL is rejected on scan form', async ({ page }) => {
    await page.goto('/scan')
    await dismissCookieBanner(page)
    const input = page.getByPlaceholder(/github.com\/org\/repo/i)
    await input.fill('not-a-valid-repo')
    await input.blur()
    await expect(page.getByText(/valid GitHub|valid/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('button', { name: /Analyze Repository/i })).toBeDisabled()
  })
})

test.describe('Responsive scan page', () => {
  test('mobile layout shows repository input and analyze button', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/scan')
    await dismissCookieBanner(page)
    await expect(page.getByPlaceholder(/github.com\/org\/repo/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Analyze Repository/i })).toBeVisible()
  })
})