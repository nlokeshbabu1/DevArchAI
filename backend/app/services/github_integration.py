"""GitHub integration for creating PRs with fixes."""

import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class GitHubIntegrationService:
    """Service for GitHub operations (clone, commit, create PR)."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def get_repo_info(self, repo_url: str) -> dict:
        """Get repository information."""
        try:
            # Extract owner and repo from URL
            parts = repo_url.rstrip("/").split("/")
            if len(parts) < 2:
                return {"success": False, "error": "Invalid repository URL"}
            
            owner = parts[-2]
            repo = parts[-1]
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers,
                    timeout=10.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "owner": owner,
                        "repo": repo,
                        "default_branch": data.get("default_branch", "main"),
                        "clone_url": data.get("clone_url"),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get repo info: {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Get repo info failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_branch(self, owner: str, repo: str, branch_name: str, base_branch: str) -> dict:
        """Create a new branch from base branch."""
        try:
            async with httpx.AsyncClient() as client:
                # Get base branch ref
                ref_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                    headers=self.headers,
                    timeout=10.0,
                )
                
                if ref_response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Failed to get base branch: {ref_response.status_code}",
                    }
                
                base_sha = ref_response.json()["object"]["sha"]
                
                # Create new branch
                branch_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/refs",
                    headers=self.headers,
                    json={
                        "ref": f"refs/heads/{branch_name}",
                        "sha": base_sha,
                    },
                    timeout=10.0,
                )
                
                if branch_response.status_code == 201:
                    return {
                        "success": True,
                        "branch_name": branch_name,
                        "sha": base_sha,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to create branch: {branch_response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Create branch failed: {e}")
            return {"success": False, "error": str(e)}

    async def commit_file(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        file_path: str,
        content: str,
        message: str,
    ) -> dict:
        """Commit a file to a branch."""
        try:
            async with httpx.AsyncClient() as client:
                # Get current file SHA if it exists
                file_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}",
                    headers=self.headers,
                    params={"ref": branch_name},
                    timeout=10.0,
                )
                
                sha = None
                if file_response.status_code == 200:
                    sha = file_response.json()["sha"]
                
                # Commit the file
                import base64
                commit_response = await client.put(
                    f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}",
                    headers=self.headers,
                    json={
                        "message": message,
                        "content": base64.b64encode(content.encode()).decode(),
                        "branch": branch_name,
                        "sha": sha,
                    },
                    timeout=10.0,
                )
                
                if commit_response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "commit_sha": commit_response.json()["commit"]["sha"],
                        "file_path": file_path,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to commit: {commit_response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Commit file failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ) -> dict:
        """Create a pull request."""
        try:
            async with httpx.AsyncClient() as client:
                pr_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls",
                    headers=self.headers,
                    json={
                        "title": title,
                        "body": body,
                        "head": head_branch,
                        "base": base_branch,
                    },
                    timeout=10.0,
                )
                
                if pr_response.status_code == 201:
                    data = pr_response.json()
                    return {
                        "success": True,
                        "pr_number": data["number"],
                        "pr_url": data["html_url"],
                        "pr_id": data["id"],
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to create PR: {pr_response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Create PR failed: {e}")
            return {"success": False, "error": str(e)}

    async def apply_fix_and_create_pr(
        self,
        repo_url: str,
        file_path: str,
        fix_code: str,
        finding_title: str,
        branch_name: Optional[str] = None,
    ) -> dict:
        """
        Apply fix and create PR in one flow.
        
        Args:
            repo_url: GitHub repository URL
            file_path: Path to file to fix
            fix_code: The fix code to apply
            finding_title: Title of the finding/issue
            branch_name: Optional custom branch name
        
        Returns:
            PR creation result
        """
        try:
            # Get repo info
            repo_info = await self.get_repo_info(repo_url)
            if not repo_info["success"]:
                return repo_info
            
            owner = repo_info["owner"]
            repo = repo_info["repo"]
            default_branch = repo_info["default_branch"]
            
            # Generate branch name
            if not branch_name:
                import re
                from datetime import datetime
                safe_title = re.sub(r"[^a-zA-Z0-9]", "-", finding_title.lower())[:50]
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                branch_name = f"fix/{safe_title}-{timestamp}"
            
            # Create branch
            branch_result = await self.create_branch(owner, repo, branch_name, default_branch)
            if not branch_result["success"]:
                return branch_result
            
            # Commit fix
            commit_message = f"Fix: {finding_title}\n\nAutomated fix applied by DevArchAI"
            commit_result = await self.commit_file(
                owner, repo, branch_name, file_path, fix_code, commit_message
            )
            if not commit_result["success"]:
                return commit_result
            
            # Create PR
            pr_title = f"Fix: {finding_title}"
            pr_body = f"""## Automated Fix by DevArchAI

This PR was automatically generated to fix a security/reliability issue.

### Changes
- Applied fix to `{file_path}`

### Details
- **Finding**: {finding_title}
- **Generated by**: DevArchAI
- **Branch**: {branch_name}

Please review the changes carefully before merging.

---
*This PR was created automatically. Please review and test before merging.*"""
            
            pr_result = await self.create_pull_request(
                owner, repo, pr_title, pr_body, branch_name, default_branch
            )
            
            if pr_result["success"]:
                pr_result["branch_name"] = branch_name
            
            return pr_result
            
        except Exception as e:
            logger.error(f"Apply fix and create PR failed: {e}")
            return {"success": False, "error": str(e)}


# Global instance
github_integration_service = GitHubIntegrationService()


def get_github_integration_service() -> GitHubIntegrationService:
    """Get the GitHub integration service."""
    return github_integration_service
