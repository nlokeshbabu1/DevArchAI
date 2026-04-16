"""Pull Request creation endpoint."""

import structlog
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.github_installation import GitHubInstallation
from app.models.pull_request import PullRequest, PRStatus
from app.models.scan import Scan
from app.models.user import User
from app.schemas.pull_request import CreatePRRequest, CreatePRResponse
from app.services.github_app_service import GitHubAppService, GitHubAppServiceError
from app.services.github_pr import (
    GitHubPRService,
    generate_pr_title,
    generate_pr_description,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/github", tags=["GitHub Pull Requests"])


def _parse_uuid(uuid_str: str) -> UUID:
    """Parse UUID from string."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {uuid_str}"
        )


def _extract_repo_full_name(repo_url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    cleaned = repo_url.replace("https://github.com/", "").rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    parts = cleaned.split("/")
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub repository URL: {repo_url}",
        )
    return f"{parts[0]}/{parts[1]}"


@router.post("/create-pr", response_model=CreatePRResponse)
async def create_pull_request(
    request: CreatePRRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a GitHub Pull Request with AI-generated fixes.

    This endpoint:
    1. Validates scan and findings
    2. Checks user has GitHub token
    3. Clones repository
    4. Applies fixes to files
    5. Creates new branch
    6. Commits and pushes changes
    7. Creates Pull Request on GitHub
    8. Stores PR information in database
    """
    logger.info(
        "PR creation initiated",
        scan_id=request.scan_id,
        user_id=current_user.id,
        finding_count=len(request.finding_ids) if request.finding_ids else "auto"
    )

    # Step 1: Validate scan exists and belongs to user
    scan_uuid = _parse_uuid(request.scan_id)

    scan_result = await db.execute(
        select(Scan).where(
            Scan.id == scan_uuid,
            Scan.user_id == current_user.id
        )
    )
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {request.scan_id} not found or access denied"
        )

    if scan.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scan must be completed before creating PR. Current status: {scan.status.value}"
        )

    # Step 2: Get findings to fix
    if request.finding_ids:
        # User specified specific findings
        finding_uuids = [_parse_uuid(fid) for fid in request.finding_ids]
        findings_result = await db.execute(
            select(Finding).where(
                Finding.scan_id == scan_uuid,
                Finding.id.in_(finding_uuids)
            )
        )
        findings = findings_result.scalars().all()

        if len(findings) != len(finding_uuids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some finding IDs are invalid or don't belong to this scan"
            )
    else:
        # Default: fix all critical and high severity findings
        findings_result = await db.execute(
            select(Finding).where(
                Finding.scan_id == scan_uuid,
                Finding.severity.in_(["critical", "high"])
            ).order_by(Finding.severity)
        )
        findings = findings_result.scalars().all()

    if not findings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No findings to fix. Specify finding_ids or ensure scan has critical/high severity findings."
        )

    # Step 3: Resolve GitHub App installation and short-lived installation token
    repo_full_name = _extract_repo_full_name(scan.repository_url)
    install_result = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.user_id == current_user.id,
            GitHubInstallation.repo_full_name == repo_full_name,
        )
    )
    installation = install_result.scalar_one_or_none()

    github_app_service = GitHubAppService()

    # Try DB first, then GitHub API as fallback
    if not installation:
        owner, repo = repo_full_name.split("/", 1)

        logger.info(
            "GitHub App installation not found in database, resolving via GitHub API",
            repo_full_name=repo_full_name,
        )

        try:
            installation_id = await github_app_service.get_installation_id(
                owner=owner,
                repo=repo,
            )
        except GitHubAppServiceError as exc:
            logger.error(
                "Failed to resolve installation_id from GitHub API",
                repo_full_name=repo_full_name,
                error=exc.message,
                status_code=exc.status_code,
            )

            if exc.status_code in (404, 403):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GitHub App is not installed on this repository",
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=exc.message,
            ) from exc

        logger.info(
            "Dynamically resolved installation_id from GitHub API",
            repo_full_name=repo_full_name,
            installation_id=installation_id,
        )

        # Best-effort: persist installation mapping for future requests
        installation = GitHubInstallation(
            user_id=current_user.id,
            repo_full_name=repo_full_name,
            installation_id=installation_id,
        )
        db.add(installation)

    try:
        installation_token_data = await github_app_service.get_installation_token(
            installation.installation_id
        )
    except GitHubAppServiceError as exc:
        logger.error(
            "Failed to get GitHub installation token",
            installation_id=installation.installation_id,
            error=exc.message,
        )
        # Map error status codes to appropriate HTTP status codes
        http_status = status.HTTP_502_BAD_GATEWAY
        if exc.status_code == 404:
            http_status = status.HTTP_400_BAD_REQUEST
        elif exc.status_code == 401:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif exc.status_code == 403:
            http_status = status.HTTP_403_FORBIDDEN

        raise HTTPException(
            status_code=http_status,
            detail=exc.message,
        ) from exc

    installation_token = installation_token_data.get("token")
    if not installation_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub installation token response missing token",
        )

    # Log token type for debugging
    token_type = github_app_service.detect_token_type(installation_token)
    logger.info(
        "Installation token obtained",
        installation_id=installation.installation_id,
        token_type=token_type,
        token_prefix=installation_token[:10] if len(installation_token) > 10 else "invalid",
        expires_at=installation_token_data.get("expires_at"),
    )

    # Step 4: Prepare fixes
    fixes = []
    for finding in findings:
        fix_code = finding.fix_code or finding.fix_example
        if not fix_code:
            logger.warning(
                "Skipping finding - no fix code available",
                finding_id=str(finding.id),
                rule_id=finding.rule_id
            )
            continue

        fixes.append({
            "file_path": finding.file_path,
            "fix_code": fix_code,
            "finding_id": str(finding.id),
            "rule_id": finding.rule_id,
        })

    if not fixes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fixes available for selected findings. AI-generated fixes may not be ready yet."
        )

    # Step 5: Generate branch name, title, and description
    branch_name = request.branch_name or f"devarchai/fix-{request.scan_id}"
    
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        severity_counts[finding.severity.value] = severity_counts.get(finding.severity.value, 0) + 1

    pr_title = request.pr_title or generate_pr_title(len(findings), severity_counts)
    
    score_before = scan.overall_score or 0
    # Estimate score improvement (rough calculation: ~5 points per critical, ~3 per high)
    estimated_improvement = (severity_counts.get("critical", 0) * 5) + (severity_counts.get("high", 0) * 3)
    score_after = min(100.0, score_before + estimated_improvement)

    pr_description = request.pr_description or generate_pr_description(
        scan_id=request.scan_id,
        findings=[{
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "severity": f.severity.value,
            "description": f.description,
            "recommendation": f.recommendation,
            "file_path": f.file_path,
            "line_number": f.line_number,
        } for f in findings],
        score_before=score_before,
        score_after=score_after,
    )

    commit_message = f"fix: apply DevArchAI fixes for scan {request.scan_id[:8]}\n\n{pr_title}"

    # Step 6: Create PR using GitHub service
    try:
        # Log token info for debugging (not the token itself)
        token_length = len(installation_token)
        token_prefix = installation_token[:10] if token_length > 10 else "invalid"

        logger.info(
            "Initializing GitHub PR service",
            repo_url=scan.repository_url,
            token_length=token_length,
            token_prefix=token_prefix,
            installation_id=installation.installation_id,
        )

        pr_service = GitHubPRService(
            github_token=installation_token,
            repo_url=scan.repository_url,
        )

        pr_info = await pr_service.create_pr_with_fixes(
            fixes=fixes,
            branch_name=branch_name,
            base_branch=scan.branch or "main",
            title=pr_title,
            description=pr_description,
            commit_message=commit_message,
            is_draft=request.is_draft,
        )

        logger.info(
            "PR created successfully",
            pr_number=pr_info["pr_number"],
            pr_url=pr_info["pr_url"],
            branch=branch_name
        )

    except Exception as e:
        logger.error("PR creation failed", error=str(e), scan_id=request.scan_id)

        # Provide helpful error messages
        error_msg = str(e)
        if "branch already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Branch '{branch_name}' already exists. Please delete it or use a different branch name."
            )
        elif "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found. Please ensure you have access and GitHub token is valid."
            )
        elif "permission denied" in error_msg.lower() or "403" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission denied.\n\n{error_msg}\n\n"
                    "This usually means:\n"
                    "- Your GitHub App installation lacks repository permissions\n"
                    "- The app doesn't have 'Contents' and 'Pull requests' write permissions\n"
                    "- The installation doesn't have access to this repository\n\n"
                    "To fix:\n"
                    "1. Go to your GitHub App settings\n"
                    "2. Ensure 'Contents: Read & write' permission is granted\n"
                    "3. Ensure 'Pull requests: Read & write' permission is granted\n"
                    "4. Reinstall the GitHub App to the repository\n"
                    "5. Try creating the PR again"
                )
            )
        elif "authentication failed" in error_msg.lower() or "401" in error_msg or "invalid or expired" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    f"Authentication failed.\n\n{error_msg}\n\n"
                    "Your GitHub App JWT may be invalid or expired.\n"
                    "Check your App ID and private key configuration."
                )
            )
        elif "installation" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"GitHub App installation not found.\n\n{error_msg}\n\n"
                    "Please install the GitHub App on this repository first."
                )
            )
        elif "access denied" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Repository access denied.\n\n{error_msg}\n\n"
                    "Please verify the GitHub App has access to this repository."
                )
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create PR: {error_msg}"
            )

    # Step 7: Save PR to database
    pr_record = PullRequest(
        scan_id=scan_uuid,
        user_id=current_user.id,
        github_pr_number=pr_info["pr_number"],
        github_pr_url=pr_info["pr_url"],
        branch_name=branch_name,
        title=pr_title,
        description=pr_description,
        status=PRStatus(pr_info["status"]),
        findings_fixed=[str(f.id) for f in findings],
        score_before=score_before,
        score_after=score_after,
    )

    db.add(pr_record)
    await db.commit()
    await db.refresh(pr_record)

    logger.info(
        "PR record saved to database",
        pr_id=str(pr_record.id),
        pr_number=pr_info["pr_number"]
    )

    # Step 8: Return PR information
    return CreatePRResponse(
        pr_id=str(pr_record.id),
        scan_id=str(scan_uuid),
        github_pr_number=pr_info["pr_number"],
        github_pr_url=pr_info["pr_url"],
        branch_name=branch_name,
        title=pr_title,
        status=PRStatus(pr_info["status"]),
        findings_fixed=[str(f.id) for f in findings],
        score_before=score_before,
        score_after=score_after,
        created_at=pr_record.created_at,
    )


@router.get("/prs/{scan_id}")
async def list_scan_prs(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all PRs created for a specific scan."""
    scan_uuid = _parse_uuid(scan_id)

    # Verify scan belongs to user
    scan_result = await db.execute(
        select(Scan).where(
            Scan.id == scan_uuid,
            Scan.user_id == current_user.id
        )
    )
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found or access denied"
        )

    # Get PRs
    prs_result = await db.execute(
        select(PullRequest).where(
            PullRequest.scan_id == scan_uuid
        ).order_by(PullRequest.created_at.desc())
    )
    prs = prs_result.scalars().all()

    return {
        "prs": [
            {
                "id": str(pr.id),
                "github_pr_number": pr.github_pr_number,
                "github_pr_url": pr.github_pr_url,
                "branch_name": pr.branch_name,
                "title": pr.title,
                "status": pr.status.value,
                "created_at": pr.created_at.isoformat(),
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            }
            for pr in prs
        ],
        "total": len(prs),
    }
