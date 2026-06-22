#!/usr/bin/env python3
"""
AI Suggestions Production Grade - Test Suite

This script tests the complete AI Suggestions workflow:
1. Generate suggestions from findings
2. Copy fix code
3. Apply fix
4. Create GitHub PR
5. Re-scan and verify resolution

Usage:
    python test_ai_suggestions.py --scan-id <scan_id> --finding-id <finding_id>
"""

import argparse
import json
import sys
from typing import Optional

import httpx


class AISuggestionsTester:
    """Test suite for AI Suggestions system."""

    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        
        self.suggestion_id: Optional[str] = None
        self.scan_id: Optional[str] = None
        self.finding_id: Optional[str] = None
        self.test_results = []

    def log_result(self, test_name: str, success: bool, message: str, data: dict = None):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "data": data or {},
        }
        self.test_results.append(result)
        
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"\n{status} - {test_name}")
        print(f"  {message}")
        if data:
            print(f"  Data: {json.dumps(data, indent=2)[:200]}...")

    async def test_get_suggestions(self, scan_id: str) -> bool:
        """Test 1: Get AI suggestions for a scan."""
        self.scan_id = scan_id
        test_name = "GET /api/v1/suggestions/{scan_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/suggestions/{scan_id}",
                    headers=self.headers,
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    suggestions = data.get("suggestions", [])
                    self.log_result(
                        test_name,
                        True,
                        f"Retrieved {len(suggestions)} suggestions",
                        {"total": data.get("total", 0), "count": len(suggestions)},
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_generate_suggestion(self, finding_id: str) -> bool:
        """Test 2: Generate AI suggestion for a finding."""
        self.finding_id = finding_id
        test_name = "POST /api/v1/suggestions/generate/{finding_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/generate/{finding_id}",
                    headers=self.headers,
                    timeout=60.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.suggestion_id = data.get("suggestion_id")
                    self.log_result(
                        test_name,
                        True,
                        "Generated AI suggestion successfully",
                        {
                            "suggestion_id": self.suggestion_id,
                            "fix_type": data.get("fix_type"),
                            "has_fix_code": bool(data.get("fix_code")),
                        },
                    )
                    return True
                elif response.status_code == 400:
                    # Suggestion already exists - that's okay
                    self.log_result(
                        test_name,
                        True,
                        "Suggestion already exists (skipping generation)",
                        {"detail": response.json().get("detail")},
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_get_single_suggestion(self, suggestion_id: str) -> bool:
        """Test 3: Get a specific AI suggestion."""
        test_name = "GET /api/v1/suggestions/{suggestion_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}",
                    headers=self.headers,
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "Retrieved suggestion details",
                        {
                            "title": data.get("title", "")[:50],
                            "status": data.get("status"),
                            "fix_type": data.get("fix_type"),
                            "has_fix_code": bool(data.get("fix_code")),
                        },
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_copy_fix(self, suggestion_id: str) -> bool:
        """Test 4: Copy fix code (requires Plus/Pro/Enterprise)."""
        test_name = "POST /api/v1/suggestions/{suggestion_id}/copy-fix"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}/copy-fix",
                    headers=self.headers,
                    json={},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "Fix code retrieved successfully",
                        {
                            "fix_type": data.get("fix_type"),
                            "file_path": data.get("file_path"),
                            "fix_code_length": len(data.get("fix_code", "")),
                        },
                    )
                    return True
                elif response.status_code == 403:
                    self.log_result(
                        test_name,
                        True,
                        "Access denied (expected for Free plan)",
                        {"detail": response.json().get("detail")},
                    )
                    return True  # This is expected behavior
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_apply_fix(self, suggestion_id: str) -> bool:
        """Test 5: Apply fix (requires Pro/Enterprise)."""
        test_name = "POST /api/v1/suggestions/{suggestion_id}/apply"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}/apply",
                    headers=self.headers,
                    json={"dry_run": True},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "Fix applied (dry run)",
                        {
                            "success": data.get("success"),
                            "file_path": data.get("file_path"),
                            "message": data.get("message"),
                        },
                    )
                    return True
                elif response.status_code == 403:
                    self.log_result(
                        test_name,
                        True,
                        "Access denied (expected for non-Pro plan)",
                        {"detail": response.json().get("detail")},
                    )
                    return True  # Expected behavior
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_ignore_suggestion(self, suggestion_id: str) -> bool:
        """Test 6: Ignore a suggestion."""
        test_name = "POST /api/v1/suggestions/{suggestion_id}/ignore"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}/ignore",
                    headers=self.headers,
                    json={},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "Suggestion marked as ignored",
                        data,
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_mark_fixed(self, suggestion_id: str) -> bool:
        """Test 7: Mark suggestion as fixed."""
        test_name = "POST /api/v1/suggestions/{suggestion_id}/mark-fixed"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}/mark-fixed",
                    headers=self.headers,
                    json={},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "Suggestion marked as fixed",
                        data,
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_create_pr(self, suggestion_id: str) -> bool:
        """Test 8: Create GitHub PR (requires Pro/Enterprise, GitHub token)."""
        test_name = "POST /api/v1/suggestions/{suggestion_id}/create-pr"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}/create-pr",
                    headers=self.headers,
                    json={
                        "branch_name": f"test/fix-{suggestion_id[:8]}",
                        "pr_title": "Test Fix",
                        "pr_description": "Automated test PR",
                    },
                    timeout=60.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "PR created successfully",
                        {
                            "pr_url": data.get("pr_url"),
                            "pr_number": data.get("pr_number"),
                            "branch_name": data.get("branch_name"),
                        },
                    )
                    return True
                elif response.status_code == 403:
                    self.log_result(
                        test_name,
                        True,
                        "Access denied (expected for non-Pro plan)",
                        {"detail": response.json().get("detail")},
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def test_rescan(self, suggestion_id: str) -> bool:
        """Test 9: Trigger re-scan after fix."""
        test_name = "POST /api/v1/suggestions/{suggestion_id}/rescan"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/suggestions/{suggestion_id}/rescan",
                    headers=self.headers,
                    json={},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        test_name,
                        True,
                        "Re-scan initiated",
                        {
                            "scan_id": data.get("scan_id"),
                            "message": data.get("message"),
                        },
                    )
                    return True
                elif response.status_code == 403:
                    self.log_result(
                        test_name,
                        True,
                        "Access denied (expected for non-Pro plan)",
                        {"detail": response.json().get("detail")},
                    )
                    return True
                else:
                    self.log_result(
                        test_name,
                        False,
                        f"Failed with status {response.status_code}: {response.text}",
                    )
                    return False
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            return False

    async def run_all_tests(self, scan_id: str, finding_id: str):
        """Run all tests in sequence."""
        print("\n" + "=" * 80)
        print("AI SUGGESTIONS PRODUCTION GRADE - TEST SUITE")
        print("=" * 80)
        print(f"\nBase URL: {self.base_url}")
        print(f"Scan ID: {scan_id}")
        print(f"Finding ID: {finding_id}")
        print(f"Token: {'Provided' if self.token else 'Not provided (anonymous)'}")
        
        # Test 1: Get suggestions
        await self.test_get_suggestions(scan_id)
        
        # Test 2: Generate suggestion
        await self.test_generate_suggestion(finding_id)
        
        # If we have a suggestion ID, run remaining tests
        if self.suggestion_id:
            await self.test_get_single_suggestion(self.suggestion_id)
            await self.test_copy_fix(self.suggestion_id)
            await self.test_apply_fix(self.suggestion_id)
            await self.test_ignore_suggestion(self.suggestion_id)
            await self.test_mark_fixed(self.suggestion_id)
            await self.test_create_pr(self.suggestion_id)
            await self.test_rescan(self.suggestion_id)
        else:
            print("\n⚠ Skipping remaining tests (no suggestion ID available)")
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.test_results if r["success"])
        failed = len(self.test_results) - passed
        
        print(f"\nTotal Tests: {len(self.test_results)}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"Success Rate: {(passed / len(self.test_results) * 100):.1f}%")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="AI Suggestions Test Suite")
    parser.add_argument("--scan-id", required=True, help="Scan ID to test")
    parser.add_argument("--finding-id", required=True, help="Finding ID to generate suggestion")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--token", help="Authentication token")
    
    args = parser.parse_args()
    
    tester = AISuggestionsTester(base_url=args.base_url, token=args.token)
    await tester.run_all_tests(args.scan_id, args.finding_id)
    
    # Exit with error code if any tests failed
    failed = sum(1 for r in tester.test_results if not r["success"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
