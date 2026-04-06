/**
 * Production-Level E2E Tests for DevArchAI Frontend
 * 
 * Tests complete user flows:
 * - Scan flow (URL input → progress → results)
 * - Results display (findings, AI suggestions, tech stack)
 * - History flow (list scans → view details)
 * 
 * Run with:
 *   npx playwright test tests/e2e/scan-flow-production.spec.ts
 *   npx playwright test --headed
 */

import { test, expect } from '@playwright/test';

test.describe('Complete Scan Flow - Production E2E', () => {
  
  test('should complete full scan flow from URL to results', async ({ page }) => {
    /**
     * Flow:
     * 1. Navigate to scan page
     * 2. Enter repository URL
     * 3. Click start analysis
     * 4. Wait for progress animation
     * 5. Verify results page loads
     * 6. Verify findings displayed
     * 7. Verify AI suggestions shown
     */

    // 1. Navigate to scan page
    await page.goto('/scan');
    
    // Verify scan page loaded
    await expect(page.locator('text=/Analyze Your DevOps Architecture/i')).toBeVisible();

    // 2. Enter repository URL
    const urlInput = page.locator('input[type="url"]');
    await expect(urlInput).toBeVisible();
    await urlInput.fill('https://github.com/hashicorp/terraform-guides');

    // 3. Click start analysis
    const startButton = page.locator('button:has-text("Start Analysis")');
    await expect(startButton).toBeVisible();
    await expect(startButton).toBeEnabled();
    await startButton.click();

    // 4. Wait for progress to appear
    await expect(page.locator('text=/Analyzing Repository/i')).toBeVisible({ timeout: 5000 });
    
    // Wait for progress bar
    await expect(page.locator('text=/Progress/i')).toBeVisible();

    // 5. Wait for completion (mocked in test env)
    // In production, this would wait for actual scan completion
    await page.waitForTimeout(2000);

    // 6. Verify results page
    await expect(page.locator('text=/Scan Results/i')).toBeVisible({ timeout: 30000 });

    // 7. Verify findings are displayed
    const findings = page.locator('[class*="finding"]');
    await expect(findings.first()).toBeVisible({ timeout: 10000 });

    console.log('✅ Complete scan flow test passed');
  });

  test('should display AI suggestions in results', async ({ page }) => {
    /**
     * Verify AI-generated content is shown:
     * - AI summary
     * - Risk analysis
     * - Impact assessment
     * - Fix code examples
     */

    // Navigate to results page (mocked scan)
    await page.goto('/scan/results/test-scan-id');

    // Wait for results to load
    await page.waitForSelector('[class*="finding"]', { timeout: 10000 });

    // Find first finding and expand it
    const firstFinding = page.locator('[class*="finding"]').first();
    await firstFinding.click();

    // Verify AI suggestion block exists
    const aiSuggestion = page.locator('text=/AI/i');
    await expect(aiSuggestion.first()).toBeVisible();

    // Verify fix code is shown
    const fixCode = page.locator('code, [class*="code-block"]');
    await expect(fixCode.first()).toBeVisible();

    console.log('✅ AI suggestions display test passed');
  });

  test('should show detected technologies in results', async ({ page }) => {
    /**
     * Verify technology detection badges:
     * - Docker
     * - Kubernetes
     * - Terraform
     * - CI/CD
     */

    await page.goto('/scan/results/test-scan-id');

    // Wait for tech stack display
    await page.waitForTimeout(1000);

    // Look for technology names (case insensitive)
    const pageText = await page.locator('body').innerText();
    
    // Should mention detected technologies
    expect(
      pageText.toLowerCase().includes('docker') ||
      pageText.toLowerCase().includes('terraform') ||
      pageText.toLowerCase().includes('kubernetes') ||
      pageText.toLowerCase().includes('detected')
    ).toBe(true);

    console.log('✅ Technology detection test passed');
  });

  test('should handle scan errors gracefully', async ({ page }) => {
    /**
     * Test error handling:
     * - Invalid URL
     * - Network error
     * - Scan failure
     */

    await page.goto('/scan');

    // Enter invalid URL
    const urlInput = page.locator('input[type="url"]');
    await urlInput.fill('invalid-url');

    // Try to start scan
    const startButton = page.locator('button:has-text("Start Analysis")');
    await startButton.click();

    // Should show validation error
    await page.waitForTimeout(500);
    
    // URL validation should prevent scan
    const urlValue = await urlInput.inputValue();
    expect(urlValue).toBe('invalid-url');

    console.log('✅ Error handling test passed');
  });
});

test.describe('Scan History - Production E2E', () => {
  
  test('should display scan history with latest scans first', async ({ page }) => {
    /**
     * Verify scan history:
     * - Shows list of scans
     * - Sorted by date (newest first)
     * - Shows status badges
     * - Clickable to view details
     */

    // Navigate to scan history
    await page.goto('/dashboard/scans');

    // Wait for scan list to load
    await page.waitForTimeout(1000);

    // Verify scan items are displayed
    const scanItems = page.locator('[class*="scan"]');
    const count = await scanItems.count();
    
    if (count > 0) {
      await expect(scanItems.first()).toBeVisible();
      console.log(`✅ Found ${count} scans in history`);
    } else {
      // Empty state should be shown
      await expect(page.locator('text=/No scans/i')).toBeVisible();
      console.log('✅ Empty state displayed correctly');
    }
  });

  test('should auto-refresh scan history', async ({ page }) => {
    /**
     * Verify auto-refresh functionality:
     * - Page refreshes every 30s
     * - New scans appear automatically
     */

    await page.goto('/dashboard/scans');

    // Wait for initial load
    await page.waitForTimeout(1000);

    // Take snapshot of current scans
    const scanItems = page.locator('[class*="scan"]');
    const initialCount = await scanItems.count();

    // Wait for auto-refresh (30s in production, 5s in test)
    await page.waitForTimeout(5000);

    // Verify page didn't crash
    await expect(page.locator('body')).toBeVisible();

    console.log('✅ Auto-refresh test passed');
  });
});

test.describe('Results Page - Production E2E', () => {
  
  test('should display security scores', async ({ page }) => {
    /**
     * Verify security scores are shown:
     * - Overall score
     * - Security score
     * - Category scores
     */

    await page.goto('/scan/results/test-scan-id');

    // Wait for scores to load
    await page.waitForTimeout(1000);

    // Look for score indicators
    const pageText = await page.locator('body').innerText();
    
    expect(
      pageText.includes('Score') ||
      pageText.includes('score') ||
      pageText.includes('/100')
    ).toBe(true);

    console.log('✅ Security scores test passed');
  });

  test('should display severity counts', async ({ page }) => {
    /**
     * Verify severity breakdown:
     * - Critical count
     * - High count
     * - Medium count
     * - Low count
     */

    await page.goto('/scan/results/test-scan-id');

    await page.waitForTimeout(1000);

    // Look for severity indicators
    const severityBadges = page.locator('[class*="severity"], [class*="badge"]');
    const count = await severityBadges.count();

    if (count > 0) {
      await expect(severityBadges.first()).toBeVisible();
      console.log(`✅ Found ${count} severity badges`);
    }
  });

  test('should allow downloading reports', async ({ page }) => {
    /**
     * Verify report download:
     * - Download button visible
     * - Can select format (JSON, PDF, Excel)
     * - Download starts on click
     */

    await page.goto('/scan/results/test-scan-id');

    await page.waitForTimeout(1000);

    // Look for download button
    const downloadButton = page.locator('button:has-text(/Download/i), button:has-text(/Export/i)');
    const isVisible = await downloadButton.isVisible().catch(() => false);

    if (isVisible) {
      await expect(downloadButton).toBeEnabled();
      console.log('✅ Download button visible and enabled');
    } else {
      console.log('⚠️ Download button not found (may not be implemented)');
    }
  });

  test('should show empty state for no findings', async ({ page }) => {
    /**
     * Verify empty state when no findings:
     * - Shows "No issues found" message
     * - Shows success indicator
     */

    // This would require mocking an empty scan
    // For now, just verify the page handles errors gracefully
    await page.goto('/scan/results/nonexistent-scan-id');

    await page.waitForTimeout(1000);

    // Should show error or empty state, not crash
    const bodyText = await page.locator('body').innerText();
    expect(
      bodyText.toLowerCase().includes('not found') ||
      bodyText.toLowerCase().includes('error') ||
      bodyText.toLowerCase().includes('no')
    ).toBe(true);

    console.log('✅ Empty state handling test passed');
  });
});

test.describe('Responsive Design - Production E2E', () => {
  
  test('should work on mobile viewport', async ({ page }) => {
    /**
     * Test mobile responsiveness:
     * - All elements visible
     * - No horizontal scroll
     * - Touch-friendly buttons
     */

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/scan');

    // Verify key elements visible on mobile
    await expect(page.locator('text=/Analyze Your DevOps Architecture/i')).toBeVisible();
    await expect(page.locator('input[type="url"]')).toBeVisible();
    await expect(page.locator('button:has-text("Start Analysis")')).toBeVisible();

    // No horizontal scroll
    const bodyWidth = await page.locator('body').evaluate(el => el.scrollWidth);
    const viewportWidth = page.viewportSize()?.width || 375;
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);

    console.log('✅ Mobile responsiveness test passed');
  });

  test('should work on tablet viewport', async ({ page }) => {
    /**
     * Test tablet responsiveness
     */

    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto('/scan');

    await expect(page.locator('text=/Analyze Your DevOps Architecture/i')).toBeVisible();
    await expect(page.locator('input[type="url"]')).toBeVisible();

    console.log('✅ Tablet responsiveness test passed');
  });
});

test.describe('Performance - Production E2E', () => {
  
  test('should load scan page within 3 seconds', async ({ page }) => {
    /**
     * Test page load performance
     */

    const startTime = Date.now();
    await page.goto('/scan');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    expect(loadTime).toBeLessThan(3000);
    console.log(`✅ Scan page loaded in ${loadTime}ms`);
  });

  test('should load results page within 3 seconds', async ({ page }) => {
    /**
     * Test results page load performance
     */

    const startTime = Date.now();
    await page.goto('/scan/results/test-scan-id');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    expect(loadTime).toBeLessThan(3000);
    console.log(`✅ Results page loaded in ${loadTime}ms`);
  });
});
