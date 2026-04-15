"""GitHub service for Pull Request automation."""

import os
import re
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx
import structlog
from git import Repo, GitCommandError

from app.config import settings

logger = structlog.get_logger(__name__)


class GitHubPRService:
    """Service for automated GitHub Pull Request creation."""

    def __init__(self, github_token: str, repo_url: str):
        """
        Initialize GitHub PR service.

        Args:
            github_token: GitHub personal access token, OAuth token, or GitHub App installation token
            repo_url: Full GitHub repository URL
        """
        self.github_token = github_token
        self.repo_url = repo_url
        self.owner, self.repo_name = self._extract_repo_info(repo_url)
        self.temp_dir = None
        self.local_repo = None
        self._token_type = None  # Will be determined during validation

    def _extract_repo_info(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo name from GitHub URL."""
        if not repo_url.startswith("https://github.com/"):
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        path = repo_url.replace("https://github.com/", "").rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]

        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")

        return parts[0], parts[1]

    def _get_auth_url(self) -> str:
        """Get authenticated repository URL for git operations."""
        # Validate token before creating URL
        if not self.github_token or len(self.github_token.strip()) == 0:
            raise ValueError("GitHub token is empty or invalid")

        # Log token info for debugging (not the token itself!)
        logger.info(
            "Creating auth URL",
            token_length=len(self.github_token),
            token_prefix=self.github_token[:10] if len(self.github_token) > 10 else "invalid"
        )

        # Use oauth2 as username which is the recommended approach for OAuth tokens
        # This works more reliably than x-access-token for OAuth flow tokens
        return f"https://oauth2:{self.github_token}@github.com/{self.owner}/{self.repo_name}.git"

    def _detect_token_type(self) -> str:
        """
        Detect the type of GitHub token based on its format.

        Returns:
            Token type: 'oauth', 'github_app', 'pat', or 'unknown'
        """
        if self._token_type:
            return self._token_type

        # GitHub App installation tokens start with 'ghs_'
        if self.github_token.startswith('ghs_'):
            self._token_type = 'github_app'
        # OAuth tokens and PATs typically start with 'gho_' (new format) or are random strings
        elif self.github_token.startswith('gho_'):
            self._token_type = 'oauth'
        # Personal Access Tokens (classic) don't have a prefix but are 40 chars
        elif len(self.github_token) >= 40:
            self._token_type = 'pat'
        else:
            self._token_type = 'unknown'

        logger.info("Token type detected", token_type=self._token_type)
        return self._token_type

    async def validate_token_and_access(self) -> dict:
        """
        Validate GitHub token and check repository access before attempting push.

        Returns:
            Dictionary with validation results including:
            - valid: bool
            - token_type: str
            - user: str (username or app name)
            - scopes: list (for OAuth/PAT tokens)
            - repo_access: bool (whether we can access the repo)
            - error: str (if validation failed)

        Raises:
            Exception: If token is invalid, expired, or lacks required permissions
        """
        logger.info(
            "Validating GitHub token and repository access",
            owner=self.owner,
            repo=self.repo_name
        )

        token_type = self._detect_token_type()
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        validation_result = {
            "valid": False,
            "token_type": token_type,
            "user": None,
            "scopes": [],
            "repo_access": False,
            "error": None,
        }

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Validate token by getting user/app info
                response = await client.get(
                    "https://api.github.com/user",
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 401:
                    validation_result["error"] = (
                        "GitHub token is invalid or expired. "
                        "Please logout and login with GitHub again to get a fresh token."
                    )
                    raise Exception(validation_result["error"])

                if response.status_code != 200:
                    validation_result["error"] = f"GitHub API error: {response.status_code}"
                    raise Exception(validation_result["error"])

                user_data = response.json()
                validation_result["user"] = user_data.get("login")
                validation_result["scopes"] = self._parse_scopes(response.headers.get("X-OAuth-Scopes", ""))

                logger.info(
                    "Token validated successfully",
                    user=validation_result["user"],
                    scopes=validation_result["scopes"],
                    token_type=token_type
                )

                # Step 2: Check if token has required scopes (for OAuth/PAT tokens)
                if token_type in ['oauth', 'pat', 'unknown']:
                    required_scopes = ['repo', 'public_repo']
                    has_repo_scope = any(
                        scope in validation_result["scopes"]
                        for scope in required_scopes
                    )

                    if not has_repo_scope:
                        validation_result["error"] = (
                            f"GitHub token lacks required 'repo' or 'public_repo' scope. "
                            f"Current scopes: {', '.join(validation_result['scopes'])}\n\n"
                            "To fix this:\n"
                            "1. Logout from DevArchAI\n"
                            "2. Login with GitHub again\n"
                            "3. Ensure you authorize the application with repository permissions\n"
                            "4. Try creating the PR again"
                        )
                        raise Exception(validation_result["error"])

                # Step 3: Validate repository access
                repo_api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
                repo_response = await client.get(
                    repo_api_url,
                    headers=headers,
                    timeout=10.0
                )

                if repo_response.status_code == 404:
                    validation_result["error"] = (
                        f"Repository '{self.owner}/{self.repo_name}' not found or access denied. "
                        "Please verify you have access to this repository."
                    )
                    raise Exception(validation_result["error"])

                if repo_response.status_code == 403:
                    repo_error_data = repo_response.json()
                    validation_result["error"] = (
                        f"Repository access denied: {repo_error_data.get('message', 'Forbidden')}\n\n"
                        "This usually means:\n"
                        "- The repository is private and your token doesn't have access\n"
                        "- Your GitHub App installation doesn't have access to this repository\n"
                        "- Your OAuth token doesn't have 'repo' scope"
                    )
                    raise Exception(validation_result["error"])

                if repo_response.status_code != 200:
                    validation_result["error"] = f"Repository check failed: {repo_response.status_code}"
                    raise Exception(validation_result["error"])

                repo_data = repo_response.json()
                validation_result["repo_access"] = True
                validation_result["valid"] = True

                logger.info(
                    "Repository access validated",
                    repo=repo_data.get("full_name"),
                    private=repo_data.get("private"),
                    default_branch=repo_data.get("default_branch")
                )

                return validation_result

        except httpx.TimeoutException:
            validation_result["error"] = "GitHub API request timed out. Please try again."
            raise Exception(validation_result["error"])
        except httpx.RequestError as e:
            validation_result["error"] = f"GitHub API request failed: {str(e)}"
            raise Exception(validation_result["error"])

    def _parse_scopes(self, scopes_header: str) -> list[str]:
        """Parse X-OAuth-Scopes header into a list of scopes."""
        if not scopes_header:
            return []
        return [scope.strip() for scope in scopes_header.split(",")]

    def _get_api_headers(self) -> dict:
        """Get headers for GitHub API requests."""
        return {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def clone_repository(self, branch: str = "main") -> str:
        """
        Clone repository to temporary directory.

        Args:
            branch: Branch to checkout

        Returns:
            Path to cloned repository
        """
        logger.info("Cloning repository", owner=self.owner, repo=self.repo_name, branch=branch)

        self.temp_dir = tempfile.mkdtemp(prefix=f"devarchai_pr_{self.repo_name}_")
        auth_url = self._get_auth_url()

        try:
            self.local_repo = Repo.clone_from(
                auth_url,
                self.temp_dir,
                branch=branch,
                depth=1  # Shallow clone for speed
            )
            logger.info("Repository cloned successfully", path=self.temp_dir)
            return self.temp_dir
        except GitCommandError as e:
            logger.error("Failed to clone repository", error=str(e))
            raise Exception(f"Failed to clone repository: {str(e)}")

    def cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("Temporary directory cleaned up", path=self.temp_dir)
            except Exception as e:
                logger.warning("Failed to cleanup temporary directory", error=str(e))

    def apply_fixes(self, fixes: list[dict]) -> list[str]:
        """
        Apply AI-generated fixes to files.

        Args:
            fixes: List of fix dictionaries with file_path, fix_code, etc.

        Returns:
            List of modified file paths
        """
        logger.info("Applying fixes", count=len(fixes))
        modified_files = []

        for fix in fixes:
            file_path = fix.get("file_path")
            fix_code = fix.get("fix_code") or fix.get("after_code")

            if not file_path or not fix_code:
                logger.warning("Skipping fix - missing data", file_path=file_path)
                continue

            # Try to find the file in the repository
            full_path = self._find_file_in_repo(file_path)

            if not full_path:
                logger.warning("File not found in repository, skipping", file_path=file_path)
                continue

            try:
                # Read original content
                with open(full_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                # Apply fix
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(fix_code)

                # Get relative path for logging
                rel_path = str(full_path.relative_to(self.temp_dir))
                modified_files.append(rel_path)
                logger.info("Fix applied", file_path=rel_path)

            except Exception as e:
                logger.error("Failed to apply fix", file_path=file_path, error=str(e))
                continue

        logger.info("Fixes applied successfully", modified_files=len(modified_files))
        return modified_files

    def _find_file_in_repo(self, file_path: str) -> Path | None:
        """
        Find a file in the repository by trying various path strategies.

        Args:
            file_path: The file path from findings (may be relative or cleaned)

        Returns:
            Full path to the file if found, None otherwise
        """
        temp_path = Path(self.temp_dir)

        # Strategy 1: Try the path as-is (might already be relative to repo root)
        candidate = temp_path / file_path
        if candidate.exists() and candidate.is_file():
            return candidate

        # Strategy 2: Try stripping common prefixes (e.g., repo name)
        # e.g., "myrepo/terraform/backend.tf" -> "terraform/backend.tf"
        parts = Path(file_path).parts
        if len(parts) > 1:
            # Try removing first component
            stripped_path = Path(*parts[1:])
            candidate = temp_path / stripped_path
            if candidate.exists() and candidate.is_file():
                return candidate

        # Strategy 3: Search for the file by name in the entire repo
        filename = Path(file_path).name
        for root, dirs, files in os.walk(self.temp_dir):
            # Skip hidden directories and .git
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']

            if filename in files:
                found_path = Path(root) / filename
                logger.info(
                    "Found file by name search",
                    requested=file_path,
                    found=str(found_path.relative_to(temp_path))
                )
                return found_path

        # Strategy 4: Try case-insensitive match
        file_path_lower = file_path.lower()
        for root, dirs, files in os.walk(self.temp_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']

            for f in files:
                if f.lower() == file_path_lower or f.lower() == Path(file_path).name.lower():
                    found_path = Path(root) / f
                    logger.info(
                        "Found file by case-insensitive match",
                        requested=file_path,
                        found=str(found_path.relative_to(temp_path))
                    )
                    return found_path

        logger.warning("File not found in repository", file_path=file_path)
        return None

    def create_branch(self, branch_name: str) -> str:
        """
        Create and checkout new branch.

        Args:
            branch_name: Name of the new branch

        Returns:
            Branch name
        """
        logger.info("Creating branch", branch=branch_name)

        try:
            # Create new branch from current HEAD
            new_branch = self.local_repo.create_head(branch_name)
            new_branch.checkout()
            logger.info("Branch created and checked out", branch=branch_name)
            return branch_name
        except GitCommandError as e:
            logger.error("Failed to create branch", error=str(e))
            raise Exception(f"Failed to create branch: {str(e)}")

    def commit_changes(self, commit_message: str, modified_files: list[str]) -> str:
        """
        Commit changes to repository.

        Args:
            commit_message: Commit message
            modified_files: List of modified file paths

        Returns:
            Commit hash
        """
        logger.info("Committing changes", files=len(modified_files))

        try:
            # Add modified files
            for file_path in modified_files:
                self.local_repo.index.add([file_path])

            # Commit
            commit = self.local_repo.index.commit(commit_message)
            logger.info("Changes committed", commit=commit.hexsha[:7])
            return commit.hexsha
        except GitCommandError as e:
            logger.error("Failed to commit changes", error=str(e))
            raise Exception(f"Failed to commit changes: {str(e)}")

    def push_branch(self, branch_name: str) -> bool:
        """
        Push branch to remote repository with proper authentication.

        Args:
            branch_name: Branch name to push

        Returns:
            True if successful

        Raises:
            Exception: If push fails due to authentication, permissions, or other errors
        """
        logger.info("Pushing branch", branch=branch_name)

        try:
            # Detect token type to use appropriate authentication method
            token_type = self._detect_token_type()

            # Configure git credential helper with the appropriate username
            # For GitHub App tokens (ghs_), use 'x-access-token'
            # For OAuth/PAT tokens, use 'oauth2'
            if token_type == 'github_app':
                git_username = 'x-access-token'
                logger.info("Using GitHub App token authentication")
            else:
                git_username = 'oauth2'
                logger.info("Using OAuth/PAT token authentication")

            # Create a git credential helper script
            cred_helper_script = os.path.join(self.temp_dir, 'git-cred-helper.sh')

            with open(cred_helper_script, 'w') as f:
                f.write(f'''#!/bin/bash
echo "protocol=https"
echo "host=github.com"
echo "username={git_username}"
echo "password={self.github_token}"
''')

            os.chmod(cred_helper_script, 0o755)

            # Configure git to use the credential helper
            with self.local_repo.config_writer() as writer:
                writer.set_value('credential', 'helper', f'!{cred_helper_script}')

            # Use the standard HTTPS URL (credentials will be provided by helper)
            remote_url = f"https://github.com/{self.owner}/{self.repo_name}.git"
            logger.info(
                "Pushing to repository",
                url=remote_url,
                token_type=token_type,
                git_username=git_username
            )

            # Push to origin
            remote = self.local_repo.remote('origin')
            remote.push(
                refspec=f"refs/heads/{branch_name}:refs/heads/{branch_name}",
                force=False
            )

            logger.info("Branch pushed successfully", branch=branch_name)
            return True

        except GitCommandError as e:
            error_msg = str(e)
            logger.error("Failed to push branch", error=error_msg)

            # Provide helpful error messages based on the error
            if "403" in error_msg or "Forbidden" in error_msg:
                token_type = self._detect_token_type()
                error_detail = (
                    "Failed to push: Permission denied (403).\n\n"
                    "This typically happens when:\n"
                )

                if token_type == 'github_app':
                    error_detail += (
                        "- Your GitHub App installation doesn't have write access to this repository\n"
                        "- The GitHub App doesn't have 'Contents' and 'Pull requests' permissions\n\n"
                        "To fix this:\n"
                        "1. Go to your GitHub App settings\n"
                        "2. Ensure 'Contents: Read & write' permission is granted\n"
                        "3. Ensure 'Pull requests: Read & write' permission is granted\n"
                        "4. Reinstall the GitHub App to the repository\n"
                        "5. Try creating the PR again"
                    )
                else:
                    error_detail += (
                        "- Your GitHub token doesn't have 'repo' scope permissions\n"
                        "- Your GitHub token has expired\n\n"
                        "To fix this:\n"
                        "1. Logout from DevArchAI\n"
                        "2. Login with GitHub again\n"
                        "3. Ensure you authorize the application with repository permissions\n"
                        "4. Try creating the PR again"
                    )

                raise Exception(error_detail)

            elif "401" in error_msg or "Unauthorized" in error_msg:
                raise Exception(
                    "Failed to push: Authentication failed (401).\n\n"
                    "Your GitHub token may be expired or invalid.\n\n"
                    "To fix this:\n"
                    "1. Logout from DevArchAI\n"
                    "2. Login with GitHub again\n"
                    "3. Try creating the PR again"
                )
            elif "404" in error_msg or "Not Found" in error_msg:
                raise Exception(
                    "Failed to push: Repository not found (404).\n\n"
                    "Please verify you have access to this repository."
                )
            else:
                raise Exception(f"Failed to push branch: {error_msg}")

    async def create_pull_request(
        self,
        branch_name: str,
        title: str,
        description: str,
        base_branch: str = "main",
        is_draft: bool = False
    ) -> dict:
        """
        Create Pull Request on GitHub.

        Args:
            branch_name: Source branch name
            title: PR title
            description: PR description (markdown)
            base_branch: Target branch name
            is_draft: Create as draft PR

        Returns:
            PR information dictionary
        """
        logger.info("Creating Pull Request", title=title, base=base_branch, head=branch_name)

        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/pulls"

        payload = {
            "title": title,
            "body": description,
            "head": branch_name,
            "base": base_branch,
            "draft": is_draft,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    headers=self._get_api_headers(),
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 422:
                    error_data = response.json()
                    raise Exception(f"PR creation failed: {error_data.get('message', 'Validation error')}")

                if response.status_code not in [200, 201]:
                    error_data = response.json()
                    raise Exception(f"GitHub API error: {response.status_code} - {error_data.get('message')}")

                pr_data = response.json()

                result = {
                    "pr_number": pr_data["number"],
                    "pr_url": pr_data["html_url"],
                    "pr_id": pr_data["id"],
                    "branch_name": branch_name,
                    "title": title,
                    "status": "draft" if is_draft else "open",
                    "created_at": pr_data.get("created_at"),
                }

                logger.info(
                    "Pull Request created successfully",
                    pr_number=pr_data["number"],
                    pr_url=pr_data["html_url"]
                )

                return result

        except httpx.TimeoutException:
            logger.error("GitHub API timeout")
            raise Exception("GitHub API request timed out")
        except httpx.RequestError as e:
            logger.error("GitHub API request failed", error=str(e))
            raise Exception(f"GitHub API error: {str(e)}")

    async def create_pr_with_fixes(
        self,
        fixes: list[dict],
        branch_name: str,
        base_branch: str,
        title: str,
        description: str,
        commit_message: str,
        is_draft: bool = False
    ) -> dict:
        """
        Complete PR creation workflow: validate → clone → apply fixes → commit → push → create PR.

        Args:
            fixes: List of fix dictionaries
            branch_name: Name for the new branch
            base_branch: Target branch name
            title: PR title
            description: PR description
            commit_message: Git commit message
            is_draft: Create as draft PR

        Returns:
            PR information dictionary

        Raises:
            Exception: If any step in the workflow fails
        """
        try:
            # Step 0: Validate token and repository access BEFORE attempting any operations
            logger.info("Starting PR creation workflow - validating token and access first")
            validation_result = await self.validate_token_and_access()

            logger.info(
                "Token validation successful",
                token_type=validation_result["token_type"],
                user=validation_result["user"],
                repo_access=validation_result["repo_access"]
            )

            # Step 1: Clone repository
            await self.clone_repository(branch=base_branch)

            # Step 2: Create new branch
            self.create_branch(branch_name)

            # Step 3: Apply fixes
            modified_files = self.apply_fixes(fixes)

            if not modified_files:
                raise Exception("No files were modified. Cannot create PR.")

            # Step 4: Commit changes
            self.commit_changes(commit_message, modified_files)

            # Step 5: Push branch
            self.push_branch(branch_name)

            # Step 6: Create Pull Request
            pr_info = await self.create_pull_request(
                branch_name=branch_name,
                title=title,
                description=description,
                base_branch=base_branch,
                is_draft=is_draft
            )

            return pr_info

        except Exception as e:
            # Ensure cleanup on any error
            error_msg = str(e)
            logger.error(
                "PR creation workflow failed",
                error=error_msg,
                branch=branch_name,
                stage="validation" if "validation" in error_msg.lower() else "git_operations"
            )
            raise
        finally:
            # Always cleanup temporary directory
            self.cleanup()


def generate_pr_title(findings_count: int, severity_counts: dict) -> str:
    """Generate PR title based on findings."""
    critical = severity_counts.get("critical", 0)
    high = severity_counts.get("high", 0)

    if critical > 0:
        return f"🔒 Fix {critical} critical and {high} high severity issues (DevArchAI)"
    elif high > 0:
        return f"🔒 Fix {high} high severity issues (DevArchAI)"
    else:
        return f"🔒 Fix {findings_count} security issues (DevArchAI)"


def generate_pr_description(
    scan_id: str,
    findings: list[dict],
    score_before: float,
    score_after: float,
    app_url: str = "https://app.devarchai.com"
) -> str:
    """Generate comprehensive PR description."""

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        severity = finding.get("severity", "info")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    description = f"""## 🔒 DevArchAI Security Fix

This Pull Request was automatically generated by DevArchAI to address security and production readiness issues detected in your infrastructure code.

### 📊 Scan Summary

- **Scan ID**: `{scan_id}`
- **Score Before**: {score_before:.1f}/100
- **Expected Score After**: {score_after:.1f}/100
- **Improvement**: +{score_after - score_before:.1f} points
- **Issues Fixed**: {len(findings)}

### 🚨 Issues Fixed

"""

    # Group findings by severity
    findings_by_severity = {}
    for finding in findings:
        severity = finding.get("severity", "info")
        if severity not in findings_by_severity:
            findings_by_severity[severity] = []
        findings_by_severity[severity].append(finding)

    # Add findings to description
    for severity in ["critical", "high", "medium", "low"]:
        severity_findings = findings_by_severity.get(severity, [])
        if not severity_findings:
            continue

        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
        description += f"#### {emoji.get(severity, '⚪')} {severity.upper()} Severity ({len(severity_findings)} issues)\n\n"

        for finding in severity_findings:
            file_path = finding.get("file_path", "unknown")
            line_number = finding.get("line_number", "")
            line_info = f":{line_number}" if line_number else ""

            description += f"**{finding.get('rule_id')}: {finding.get('rule_name')}**\n"
            description += f"- **File**: `{file_path}{line_info}`\n"
            description += f"- **Issue**: {finding.get('description')}\n"
            description += f"- **Fix**: {finding.get('recommendation')}\n\n"

    description += f"""### 📝 Changes Made

"""

    # List modified files
    modified_files = set()
    for finding in findings:
        file_path = finding.get("file_path")
        if file_path:
            modified_files.add(file_path)

    for file_path in sorted(modified_files):
        description += f"- Modified: `{file_path}`\n"

    description += f"""

### ✅ Review Checklist

- [ ] Review all changes before merging
- [ ] Test in staging/development environment
- [ ] Verify Terraform plan output (if applicable)
- [ ] Confirm Kubernetes deployments work as expected
- [ ] Run CI/CD pipeline checks

### 🔗 View Full Report

[View DevArchAI Scan Report]({app_url}/scans/{scan_id})

---

*Generated by [DevArchAI](https://devarchai.com) on {datetime.utcnow().strftime('%Y-%m-%d at %H:%M UTC')}*
"""

    return description
