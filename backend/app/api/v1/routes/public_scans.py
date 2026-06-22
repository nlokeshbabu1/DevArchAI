"""
Anonymous scan endpoints.

Allows unauthenticated users to:
- Submit repository URLs for scanning
- View limited scan results (score, issue counts, titles)
- See blurred AI suggestions with login CTA
"""

import json
import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.anonymous_scan import AnonymousScan
from app.models.finding import Finding
from app.models.repository import Repository as RepositoryModel
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.workers.tasks.scan_repository import scan_repository_task

from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/public", tags=["Public Scans"])


class PublicScanRequest(BaseModel):
    """Request model for public scan endpoint."""
    repository_url: str
    branch: str = "main"


@router.post("/scan", response_model=dict)
async def create_anonymous_scan(
    request: PublicScanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an anonymous scan session.

    No authentication required.
    Returns a session token to retrieve results.
    """
    try:
        from app.db.session import get_sync_session_factory
        from app.workers.tasks.scan_repository import SyncScanService
        import httpx
        
        # Generate session token
        session_token = AnonymousScan.generate_session_token()
        expires_at = AnonymousScan.get_expiry()

        # Extract repo name from URL
        repo_name = request.repository_url.rstrip("/").split("/")[-1].replace(".git", "")

        # Auto-detect branch from GitHub API if not specified or is 'main'
        branch = request.branch or "main"
        if branch == "main":
            try:
                # Extract owner and repo from URL
                # URL format: https://github.com/owner/repo
                url_parts = request.repository_url.rstrip("/").split("/")
                if len(url_parts) >= 2:
                    owner = url_parts[-2]
                    repo = url_parts[-1].replace(".git", "")

                    # Try to get default branch from GitHub API
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        api_url = f"https://api.github.com/repos/{owner}/{repo}"
                        headers = {}
                        if settings.GITHUB_TOKEN:
                            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
                        response = await client.get(api_url, headers=headers)
                        if response.status_code == 200:
                            repo_data = response.json()
                            branch = repo_data.get("default_branch", "main")
                            logger.info(f"✅ Detected default branch: {branch} for {owner}/{repo}")
                        else:
                            logger.warning(f"GitHub API returned {response.status_code}, trying fallback branches")
                            # Try common branch names
                            for fallback in ["master", "main", "develop"]:
                                try:
                                    branch_check = await client.get(
                                        f"https://api.github.com/repos/{owner}/{repo}/branches/{fallback}",
                                        headers=headers
                                    )
                                    if branch_check.status_code == 200:
                                        branch = fallback
                                        logger.info(f"✅ Using fallback branch: {branch}")
                                        break
                                except:
                                    continue
            except Exception as e:
                logger.warning(f"❌ Could not detect branch from GitHub API: {e}")
                # Try common branch names as fallback
                branch = "master"  # Default to master instead of main

        # Create anonymous scan record (for session tracking)
        anon_scan = AnonymousScan(
            session_token=session_token,
            repository_url=request.repository_url,
            repository_name=repo_name,
            branch=branch,
            expires_at=expires_at,
            status="pending",
        )

        db.add(anon_scan)
        await db.commit()
        await db.refresh(anon_scan)

        # Create actual scan record linked to anonymous session
        scan = Scan(
            id=uuid4(),
            user_id=None,
            repository_url=request.repository_url,
            branch=branch,
            status=ScanStatus.PENDING,
            progress=0,
        )

        db.add(scan)
        await db.commit()
        await db.refresh(scan)

        # Link anonymous scan to actual scan using dedicated field
        anon_scan.linked_scan_id = str(scan.id)
        await db.commit()

        # Initialize progress tracking
        from app.services.scan_progress_store import get_scan_progress_store
        store = get_scan_progress_store()
        await store.create_scan(str(scan.id))
        await store.add_log(str(scan.id), f"Scan started for {request.repository_url}")

        # Run scan synchronously for development
        try:
            SessionLocal = get_sync_session_factory()
            sync_db = SessionLocal()
            try:
                scan_service = SyncScanService(
                    db=sync_db, 
                    include_ai_explanations=True,
                    progress_store=store,
                    scan_id=str(scan.id),
                )

                # Get fresh scan from sync db
                from app.models.scan import Scan as SyncScan
                sync_scan = sync_db.get(SyncScan, scan.id)

                if sync_scan:
                    # Execute scan synchronously with progress tracking
                    updated_scan = scan_service.execute_scan(sync_scan)

                    # Copy results back to async session
                    scan.status = updated_scan.status
                    scan.progress = updated_scan.progress
                    scan.overall_score = updated_scan.overall_score
                    scan.security_score = updated_scan.security_score
                    scan.completed_at = updated_scan.completed_at
                    await db.commit()

                    logger.info(f"Sync scan completed: {scan.status.value}, score: {scan.overall_score}")
            finally:
                sync_db.close()

        except Exception as scan_error:
            error_msg = str(scan_error)

            # If branch not found, try fallback branches
            if "Could not find remote branch" in error_msg or "not found in upstream" in error_msg:
                fallback_branches = ["master", "develop", "dev", "main"]
                if branch in fallback_branches:
                    fallback_branches.remove(branch)

                logger.warning(f"Branch '{branch}' not found. Trying fallback branches: {fallback_branches}")
                await store.add_log(str(scan.id), f"Branch '{branch}' not found, trying fallbacks...")

                # Try fallback branches
                for fallback in fallback_branches:
                    try:
                        SessionLocal = get_sync_session_factory()
                        sync_db = SessionLocal()
                        try:
                            scan_service = SyncScanService(
                                db=sync_db,
                                include_ai_explanations=True,
                                progress_store=store,
                                scan_id=str(scan.id),
                            )
                            sync_scan = sync_db.get(SyncScan, scan.id)

                            if sync_scan:
                                sync_scan.branch = fallback
                                updated_scan = scan_service.execute_scan(sync_scan)

                                # Update scan record
                                scan.branch = fallback
                                scan.status = updated_scan.status
                                scan.progress = updated_scan.progress
                                scan.overall_score = updated_scan.overall_score
                                scan.security_score = updated_scan.security_score
                                scan.completed_at = updated_scan.completed_at
                                await db.commit()

                                branch = fallback  # Update branch variable
                                logger.info(f"Scan succeeded with fallback branch: {fallback}")
                                await store.add_log(str(scan.id), f"Using fallback branch: {fallback}")
                                break
                        finally:
                            sync_db.close()
                    except Exception as fallback_error:
                        logger.warning(f"Fallback branch '{fallback}' failed: {fallback_error}")
                        await store.add_log(str(scan.id), f"Fallback branch '{fallback}' failed")
                        continue
                else:
                    # All fallbacks failed
                    scan.status = ScanStatus.FAILED
                    scan.error_message = f"Scan failed: No valid branch found. Tried: {branch}, {', '.join(fallback_branches)}"
                    await db.commit()
                    await store.fail_scan(str(scan.id), scan.error_message)

                    return {
                        "session_token": session_token,
                        "scan_id": str(scan.id),
                        "repository_name": repo_name,
                        "status": "failed",
                        "message": f"Scan failed: No valid branch found. Please specify a valid branch.",
                        "expires_at": expires_at.isoformat(),
                    }
            else:
                # Other error - mark as failed
                logger.exception(f"Sync scan failed: {scan_error}")
                scan.status = ScanStatus.FAILED
                scan.error_message = f"Scan error: {str(scan_error)}"
                await db.commit()
                await store.fail_scan(str(scan.id), str(scan_error))

                return {
                    "session_token": session_token,
                    "scan_id": str(scan.id),
                    "repository_name": repo_name,
                    "status": "failed",
                    "message": f"Scan failed: {str(scan_error)}",
                    "expires_at": expires_at.isoformat(),
                }

        return {
            "session_token": session_token,
            "scan_id": str(scan.id),
            "repository_name": repo_name,
            "status": scan.status.value,
            "message": "Scan completed successfully.",
            "branch": branch,
            "expires_at": expires_at.isoformat(),
        }

    except Exception as e:
        await db.rollback()
        logger.exception("Anonymous scan creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scan session: {str(e)}",
        )


@router.get("/status/{scan_id}", response_model=dict)
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time scan progress status.

    Returns current step, progress percentage, and logs.
    """
    from app.services.scan_progress_store import get_scan_progress_store

    store = get_scan_progress_store()
    progress = await store.get_progress(scan_id)

    if not progress:
        # Return scan status from database if progress not found
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )
        
        # Only expose anonymous scan status via public endpoint
        if scan.user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Return completed scan data
        detected_techs = []
        if scan.detected_stack:
            # scan.detected_stack is a dict with "detected_stack" key containing the list
            if isinstance(scan.detected_stack, dict):
                detected_techs = scan.detected_stack.get("detected_stack", [])
            elif isinstance(scan.detected_stack, list):
                detected_techs = scan.detected_stack

        return {
            "scan_id": str(scan.id),
            "status": scan.status.value,
            "progress": 100 if scan.status == 'completed' else scan.progress,
            "current_step": "Scan completed" if scan.status == 'completed' else scan.status.value,
            "steps": [],
            "detected_stack": detected_techs,  # Return actual detected technologies list
            "logs": [f"Scan {scan.status.value} at {scan.created_at}"],
            "created_at": scan.created_at.isoformat(),
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "error_message": scan.error_message,
        }

    return {
        "scan_id": progress.scan_id,
        "status": progress.status,
        "progress": progress.progress,
        "current_step": progress.current_step,
        "steps": [step.dict() for step in progress.steps],
        "detected_stack": progress.detected_stack,
        "logs": progress.logs,
        "created_at": progress.created_at.isoformat(),
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "error_message": progress.error_message,
    }


@router.get("/scan/{session_token}")
async def get_anonymous_scan_results(
    session_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get anonymous scan results.

    Returns:
    - Security score
    - Issue severity counts
    - Issue titles and descriptions
    - AI suggestions (gated by user plan)

    No authentication required, but authenticated users get AI suggestions based on plan.
    """
    from sqlalchemy.orm import selectinload
    from app.services.feature_gating import FeatureGatingService

    # Find scan session
    result = await db.execute(
        select(AnonymousScan).where(
            AnonymousScan.session_token == session_token,
            AnonymousScan.expires_at > datetime.utcnow(),
        )
    )
    anon_scan = result.scalar_one_or_none()

    if not anon_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found or expired",
        )

    # Get linked scan ID
    scan_id = anon_scan.linked_scan_id

    if not scan_id:
        # Scan not yet linked, still pending
        return {
            "session_token": session_token,
            "status": "pending",
            "message": "Scan is in progress. Please check back in a few moments.",
            "repository_name": anon_scan.repository_name,
        }

    # Fetch actual scan results
    from uuid import UUID
    try:
        scan_uuid = UUID(scan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid scan ID",
        )

    scan_result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(Scan.id == scan_uuid)
    )
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # If scan is still pending/processing, return status
    if scan.status in [ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.PROCESSING]:
        return {
            "session_token": session_token,
            "status": scan.status.value,
            "message": "Scan is in progress. Please check back in a few moments.",
            "repository_name": anon_scan.repository_name,
            "progress": scan.progress,
        }

    # If scan failed, return error
    if scan.status == ScanStatus.FAILED:
        return {
            "session_token": session_token,
            "status": "failed",
            "message": f"Scan failed: {scan.error_message}",
            "repository_name": anon_scan.repository_name,
        }

    # Get feature gating settings based on user plan
    show_all_ai, preview_count = FeatureGatingService.get_ai_suggestion_limit(current_user)
    user_plan = getattr(current_user, 'subscription_plan', 'free') if current_user else 'free'

    # Process findings with appropriate AI gating
    findings = []
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

    for finding in scan.findings:
        severity = finding.severity.lower() if finding.severity else "info"
        if severity in severity_counts:
            severity_counts[severity] += 1

        # Build finding response
        finding_data = {
            "rule_id": finding.rule_id,
            "rule_name": finding.rule_name,
            "severity": finding.severity,
            "category": finding.category,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "file_path": finding.file_path,
            "line_number": finding.line_number,
            "ai_explanation": finding.ai_explanation,
            "ai_fix_code": None,
        }
        findings.append(finding_data)

    # Sort findings by severity (critical → high → medium → low → info)
    severity_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda x: severity_priority.get(x["severity"].lower(), 5))

    # Apply AI gating after sorting (based on sorted index)
    for index, finding_data in enumerate(findings):
        should_blur = FeatureGatingService.should_blur_suggestion(current_user, index)
        finding_data["is_ai_blurred"] = should_blur
        finding_data["ai_explanation"] = finding_data["ai_explanation"] if not should_blur else None

    # Calculate security score as string (e.g., "72/100")
    security_score = f"{int(scan.security_score)}/100" if scan.security_score else "N/A"
    
    # Calculate files analyzed from detected_stack or findings
    files_analyzed = 0
    detected_technologies = []
    
    if scan.detected_stack:
        stack = scan.detected_stack
        files_analyzed = (
            len(stack.get('docker_files', [])) +
            len(stack.get('terraform_files', [])) +
            len(stack.get('kubernetes_files', [])) +
            len(stack.get('github_actions_files', [])) +
            len(stack.get('gitlab_ci_files', [])) +
            len(stack.get('jenkins_files', [])) +
            len(stack.get('docker_compose_files', [])) +
            len(stack.get('helm_files', [])) +
            len(stack.get('ansible_files', [])) +
            len(stack.get('circleci_files', [])) +
            len(stack.get('azure_devops_files', [])) +
            len(stack.get('travis_files', [])) +
            len(stack.get('drone_files', []))
        )
        
        # Build detected technologies list
        if stack.get('has_docker') or stack.get('docker_files'):
            detected_technologies.append('docker')
        if stack.get('has_terraform') or stack.get('terraform_files'):
            detected_technologies.append('terraform')
        if stack.get('has_kubernetes') or stack.get('kubernetes_files'):
            detected_technologies.append('kubernetes')
        if stack.get('has_github_actions') or stack.get('github_actions_files'):
            detected_technologies.append('github_actions')
        if stack.get('has_gitlab_ci') or stack.get('gitlab_ci_files'):
            detected_technologies.append('gitlab_ci')
        if stack.get('has_jenkins') or stack.get('jenkins_files'):
            detected_technologies.append('jenkins')
        if stack.get('has_docker_compose') or stack.get('docker_compose_files'):
            detected_technologies.append('docker_compose')
        if stack.get('has_helm') or stack.get('helm_files'):
            detected_technologies.append('helm')
        if stack.get('has_ansible') or stack.get('ansible_files'):
            detected_technologies.append('ansible')
        if stack.get('has_circleci') or stack.get('circleci_files'):
            detected_technologies.append('circleci')
        if stack.get('has_azure_devops') or stack.get('azure_devops_files'):
            detected_technologies.append('azure_devops')
        if stack.get('has_travis') or stack.get('travis_files'):
            detected_technologies.append('travis')
        if stack.get('has_drone') or stack.get('drone_files'):
            detected_technologies.append('drone')
    
    if files_analyzed == 0:
        files_analyzed = len(set(f.file_path for f in scan.findings if f.file_path))

    # Update anonymous scan record with results
    anon_scan.security_score = security_score
    anon_scan.critical_count = str(severity_counts["critical"])
    anon_scan.high_count = str(severity_counts["high"])
    anon_scan.medium_count = str(severity_counts["medium"])
    anon_scan.low_count = str(severity_counts["low"])
    anon_scan.status = "completed"
    await db.commit()

    # Return results with user plan and gating info
    return {
        "session_token": session_token,
        "scan_id": scan_id,
        "status": "completed",
        "repository_name": anon_scan.repository_name,
        "repository_url": anon_scan.repository_url,
        "branch": anon_scan.branch,
        "security_score": security_score,
        "severity_counts": severity_counts,
        "files_analyzed": files_analyzed,
        "detected_technologies": detected_technologies,
        "findings": findings,
        "user_plan": user_plan,
        "ai_suggestions_blurred": not show_all_ai,
        "ai_preview_count": preview_count,
        "login_required": current_user is None,
        "total_findings": len(findings),
    }


@router.post("/scan/{session_token}/claim")
async def claim_anonymous_scan(
    session_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Claim an anonymous scan and associate it with a user account.
    
    Called after user logs in or signs up.
    Converts anonymous scan to authenticated scan.
    """
    from app.core.security import get_current_user, get_optional_user
    
    # Find anonymous scan
    result = await db.execute(
        select(AnonymousScan).where(
            AnonymousScan.session_token == session_token,
            AnonymousScan.expires_at > datetime.utcnow(),
        )
    )
    anon_scan = result.scalar_one_or_none()
    
    if not anon_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found or expired",
        )
    
    # Create authenticated scan
    auth_scan = Scan(
        user_id=current_user.id,
        repository_url=anon_scan.repository_url,
        branch=anon_scan.branch,
        status=ScanStatus.COMPLETED if anon_scan.status == "completed" else ScanStatus.PENDING,
        security_score=float(anon_scan.security_score.split("/")[0]) if anon_scan.security_score else None,
    )
    
    db.add(auth_scan)
    
    # Mark anonymous scan as claimed
    anon_scan.status = "claimed"
    
    await db.commit()
    await db.refresh(auth_scan)
    
    return {
        "scan_id": str(auth_scan.id),
        "message": "Scan claimed successfully. Full results now available.",
    }


@router.delete("/scan/{session_token}")
async def delete_anonymous_scan(
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an anonymous scan session."""
    result = await db.execute(
        select(AnonymousScan).where(AnonymousScan.session_token == session_token)
    )
    anon_scan = result.scalar_one_or_none()
    
    if not anon_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found",
        )
    
    await db.delete(anon_scan)
    await db.commit()

    return MessageResponse(message="Scan session deleted")
