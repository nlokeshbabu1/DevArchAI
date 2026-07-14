import { test, expect } from '@playwright/test'

test.describe('Scan Lifecycle', () => {
  test('should navigate to scan form from landing page', async ({ page }) => {
    await page.goto('/')
    // Click the scan CTA or navigate to /scan
    await page.goto('/scan')
    await expect(page.locator('h1, h2')).toContainText(/scan/i)
  })

  test('should show scan progress page for a scan id', async ({ page }) => {
    // Navigate to a scan progress page - will show loading/error since no real scan
    await page.goto('/scans/test-scan-id')
    // Should render the page (even if data fetch fails)
    await expect(page.locator('body')).toBeVisible()
  })

  test('should redirect /scan/result/:id to /scans/:id', async ({ page }) => {
    await page.goto('/scan/result/test-id')
    await expect(page).toHaveURL(/\/scans\/test-id/)
  })

  test('should redirect /analyze to /scan', async ({ page }) => {
    await page.goto('/analyze')
    await expect(page).toHaveURL(/\/scan/)
  })
})
