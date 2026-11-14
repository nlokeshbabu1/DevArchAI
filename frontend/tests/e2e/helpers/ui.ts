import type { Page } from '@playwright/test'

export async function dismissCookieBanner(page: Page): Promise<void> {
  const accept = page.getByRole('button', { name: /accept all/i })
  if (await accept.isVisible().catch(() => false)) {
    await accept.click()
  }
}

export async function loginThroughUi(
  page: Page,
  credentials: { email: string; password: string },
): Promise<void> {
  await page.goto('/login')
  await dismissCookieBanner(page)
  await page.getByPlaceholder('you@company.com').fill(credentials.email)
  await page.getByPlaceholder('Enter your password').fill(credentials.password)
  await page.getByRole('button', { name: /^sign in$/i }).click()
  await page.waitForURL(/\/dashboard/, { timeout: 30_000 })
}

export function attachGuestSession(
  page: Page,
  scanId: string,
  sessionToken: string,
): Promise<void> {
  return page.addInitScript(
    ({ id, token }) => {
      sessionStorage.setItem(`devarchai:scan-session:${id}`, token)
    },
    { id: scanId, token: sessionToken },
  )
}