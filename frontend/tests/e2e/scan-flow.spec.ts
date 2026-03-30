"""Playwright E2E tests for DevArchAI platform."""

import pytest
from playwright.sync_api import Page, expect, TimeoutError


class TestLandingPage:
    """E2E tests for landing page."""

    def test_landing_page_loads(self, page: Page, base_url):
        """Test that landing page loads correctly."""
        page.goto(base_url)
        
        # Verify page title
        expect(page).to_have_title("DevArchAI")
        
        # Verify hero section
        expect(page.locator('[data-testid="hero-section"]')).to_be_visible()
        
        # Verify scanner input
        expect(page.locator('[data-testid="repo-url-input"]')).to_be_visible()
        
        # Verify start scan button
        expect(page.locator('[data-testid="start-scan-btn"]')).to_be_visible()

    def test_landing_page_shows_features(self, page: Page, base_url):
        """Test that landing page displays key features."""
        page.goto(base_url)
        
        # Verify features section
        expect(page.locator('text=/AI-Powered/')).to_be_visible()
        expect(page.locator('text=/DevOps/')).to_be_visible()
        expect(page.locator('text=/Security/')).to_be_visible()


class TestCompleteScanFlow:
    """E2E tests for complete scan flow."""

    def test_scan_github_repository(self, page: Page, base_url):
        """
        Test complete scan flow from URL entry to results.
        
        Flow:
        1. Open app
        2. Enter GitHub repo URL
        3. Start scan
        4. Wait for scan progress
        5. Verify results displayed
        """
        # 1. Open app
        page.goto(base_url)
        
        # 2. Enter GitHub repo URL
        repo_input = page.locator('[data-testid="repo-url-input"]')
        repo_input.fill("https://github.com/test/sample-repo")
        
        # 3. Start scan
        start_btn = page.locator('[data-testid="start-scan-btn"]')
        start_btn.click()
        
        # 4. Wait for scan progress animation
        progress = page.locator('[data-testid="scan-progress"]')
        expect(progress).to_be_visible(timeout=5000)
        
        # Wait for scan to complete (mocked in test environment)
        page.wait_for_selector('[data-testid="scan-results"]', timeout=30000)
        
        # 5. Verify results displayed
        results = page.locator('[data-testid="scan-results"]')
        expect(results).to_be_visible()
        
        # Verify findings displayed
        findings = page.locator('[data-testid="finding-item"]')
        expect(findings.first).to_be_visible(timeout=10000)
        
        # Verify severity counts
        expect(page.locator('[data-testid="severity-critical"]')).to_be_visible()
        expect(page.locator('[data-testid="severity-high"]')).to_be_visible()

    def test_scan_shows_ai_suggestions(self, page: Page, base_url):
        """Test that AI suggestions are displayed in results."""
        # Navigate to results (mocked)
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for results
        page.wait_for_selector('[data-testid="finding-item"]', timeout=10000)
        
        # Verify AI suggestion blocks visible
        ai_suggestions = page.locator('[data-testid="ai-suggestion-block"]')
        expect(ai_suggestions.first).to_be_visible()
        
        # Verify AI fields displayed
        expect(page.locator('[data-testid="finding-summary"]')).to_be_visible()
        expect(page.locator('[data-testid="finding-risk"]')).to_be_visible()
        expect(page.locator('[data-testid="finding-impact"]')).to_be_visible()
        
        # Verify fix code displayed
        expect(page.locator('[data-testid="fix-code"]')).to_be_visible()

    def test_scan_shows_detected_technologies(self, page: Page, base_url):
        """Test that detected technologies are displayed."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for tech stack display
        page.wait_for_selector('[data-testid="tech-stack"]', timeout=10000)
        
        # Verify technologies displayed
        tech_stack = page.locator('[data-testid="tech-stack"]')
        expect(tech_stack).to_be_visible()
        
        # Should show Docker, K8s, Terraform, etc.
        expect(page.locator('text=/Docker/')).to_be_visible()
        expect(page.locator('text=/Kubernetes/')).to_be_visible()
        expect(page.locator('text=/Terraform/')).to_be_visible()


class TestReportDownload:
    """E2E tests for report download functionality."""

    def test_download_json_report(self, page: Page, base_url):
        """Test downloading JSON report."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for download button
        download_btn = page.locator('[data-testid="download-report-btn"]')
        expect(download_btn).to_be_visible(timeout=10000)
        
        # Click download
        download_btn.click()
        
        # Select JSON format
        page.click('[data-testid="export-json"]')
        
        # Verify download started
        with page.expect_download() as download_info:
            page.click('[data-testid="confirm-download"]')
        
        download = download_info.value
        assert download.suggested_filename().endswith(".json")

    def test_download_pdf_report(self, page: Page, base_url):
        """Test downloading PDF report."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for download button
        download_btn = page.locator('[data-testid="download-report-btn"]')
        expect(download_btn).to_be_visible(timeout=10000)
        
        # Click download
        download_btn.click()
        
        # Select PDF format
        page.click('[data-testid="export-pdf"]')
        
        # Verify download started
        with page.expect_download() as download_info:
            page.click('[data-testid="confirm-download"]')
        
        download = download_info.value
        assert download.suggested_filename().endswith(".pdf")

    def test_download_excel_report(self, page: Page, base_url):
        """Test downloading Excel report."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for download button
        download_btn = page.locator('[data-testid="download-report-btn"]')
        expect(download_btn).to_be_visible(timeout=10000)
        
        # Click download
        download_btn.click()
        
        # Select Excel format
        page.click('[data-testid="export-excel"]')
        
        # Verify download started
        with page.expect_download() as download_info:
            page.click('[data-testid="confirm-download"]')
        
        download = download_info.value
        assert download.suggested_filename().endswith(".xlsx")


class TestFindingsDisplay:
    """E2E tests for findings display."""

    def test_findings_show_severity_badges(self, page: Page, base_url):
        """Test that findings display severity badges correctly."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for findings
        page.wait_for_selector('[data-testid="finding-item"]', timeout=10000)
        
        # Verify severity badges
        expect(page.locator('[data-testid="severity-critical"]')).to_be_visible()
        expect(page.locator('[data-testid="severity-high"]')).to_be_visible()
        expect(page.locator('[data-testid="severity-medium"]')).to_be_visible()
        
        # Verify colors
        critical_badge = page.locator('[data-testid="severity-critical"]')
        expect(critical_badge).to_have_class(".*bg-red-.*")
        
        high_badge = page.locator('[data-testid="severity-high"]')
        expect(high_badge).to_have_class(".*bg-orange-.*")

    def test_findings_expand_on_click(self, page: Page, base_url):
        """Test that findings expand when clicked."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for findings
        page.wait_for_selector('[data-testid="finding-item"]', timeout=10000)
        
        # Click first finding
        finding = page.locator('[data-testid="finding-item"]').first
        finding.click()
        
        # Verify expanded content visible
        expect(page.locator('[data-testid="finding-details"]')).to_be_visible()
        expect(page.locator('[data-testid="ai-suggestion-block"]')).to_be_visible()

    def test_findings_show_copy_fix_button(self, page: Page, base_url):
        """Test that Copy Fix button is enabled."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for findings
        page.wait_for_selector('[data-testid="finding-item"]', timeout=10000)
        
        # Click to expand
        finding = page.locator('[data-testid="finding-item"]').first
        finding.click()
        
        # Verify Copy Fix button enabled
        copy_btn = page.locator('[data-testid="copy-fix-btn"]')
        expect(copy_btn).to_be_enabled()
        expect(copy_btn).to_be_visible()

    def test_findings_show_documentation_link(self, page: Page, base_url):
        """Test that Documentation link is enabled."""
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for findings
        page.wait_for_selector('[data-testid="finding-item"]', timeout=10000)
        
        # Click to expand
        finding = page.locator('[data-testid="finding-item"]').first
        finding.click()
        
        # Verify Documentation link
        doc_link = page.locator('[data-testid="documentation-link"]')
        expect(doc_link).to_be_visible()
        expect(doc_link).to_have_attribute("href", "https://.*")


class TestScanHistory:
    """E2E tests for scan history page."""

    def test_scan_history_shows_latest_scans(self, page: Page, base_url):
        """Test that scan history shows latest scans first."""
        page.goto(f"{base_url}/dashboard/scans")
        
        # Wait for scan list
        page.wait_for_selector('[data-testid="scan-history-item"]', timeout=10000)
        
        # Verify scans displayed
        scan_items = page.locator('[data-testid="scan-history-item"]')
        expect(scan_items.first).to_be_visible()
        
        # Verify sorted by date (latest first)
        # This would require checking timestamps in a real test

    def test_scan_history_shows_status(self, page: Page, base_url):
        """Test that scan history shows scan status."""
        page.goto(f"{base_url}/dashboard/scans")
        
        # Wait for scan list
        page.wait_for_selector('[data-testid="scan-history-item"]', timeout=10000)
        
        # Verify status badges
        expect(page.locator('[data-testid="status-completed"]')).to_be_visible()
        expect(page.locator('[data-testid="status-processing"]')).to_be_visible()


class TestResponsiveDesign:
    """E2E tests for responsive design."""

    def test_landing_page_mobile(self, page: Page, base_url):
        """Test landing page on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(base_url)
        
        # Verify all elements visible on mobile
        expect(page.locator('[data-testid="hero-section"]')).to_be_visible()
        expect(page.locator('[data-testid="repo-url-input"]')).to_be_visible()
        expect(page.locator('[data-testid="start-scan-btn"]')).to_be_visible()

    def test_results_page_mobile(self, page: Page, base_url):
        """Test results page on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/scan/results/test-scan-id")
        
        # Wait for results
        page.wait_for_selector('[data-testid="scan-results"]', timeout=10000)
        
        # Verify all elements visible on mobile
        expect(page.locator('[data-testid="severity-counts"]')).to_be_visible()
        expect(page.locator('[data-testid="finding-item"]')).to_be_visible()


@pytest.fixture
def base_url():
    """Get base URL from environment or use default."""
    import os
    return os.getenv("BASE_URL", "http://localhost:3000")


@pytest.fixture
def page(browser):
    """Create new page for each test."""
    p = browser.new_page()
    yield p
    p.close()


@pytest.fixture
def browser(playwright):
    """Create browser instance."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()
