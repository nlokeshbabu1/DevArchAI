"""
Unified Scan API - Works for BOTH guest and authenticated users.

Provides real-time progress tracking with step-by-step updates.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db, get_sync_session_factory
from app.models.anonymous_scan import AnonymousScan
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.config import settings
from app.services.scan_progress_store import get_scan_progress_store
from app.workers.tasks.scan_repository import SyncScanService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scan", tags=["Unified Scan"])


class UnifiedScanRequest(BaseModel):
    """Request model for unified scan endpoint."""
    repository_url: str = Field(..., min_length=10, max_length=500)
    branch: str = Field(default="main", max_length=100)
    include_ai_explanations: bool = True

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        """Validate repository URL format."""
        v = v.strip()
        # Must be a valid HTTPS URL
        if not v.startswith("https://"):
            raise ValueError("Repository URL must use HTTPS (https://)")
        # Only allow known git hosting providers
        allowed_hosts = ["github.com", "gitlab.com", "bitbucket.org"]
        url_pattern = r"^https://(www\.)?([a-zA-Z0-9.-]+)\.([a-zA-Z]{2,})/.*\.git$"
        if not re.match(url_pattern, v) and not any(host in v for host in allowed_hosts):
            raise ValueError("Repository URL must be from a supported provider (GitHub, GitLab, Bitbucket)")
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate branch name format."""
        if not re.match(r'^[a-zA-Z0-9_./-]+$', v):
            raise ValueError("Branch name contains invalid characters")
        return v


@router.post("/start", response_model=Dict[str, Any])
async def start_unified_scan(
    request: UnifiedScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Start a unified scan that works for BOTH guest and authenticated users.

    Returns:
    - scan_id: Unique identifier for tracking progress
    - session_token: For guest users to retrieve results
    - status: Initial scan status
    """
    try:
        # Generate identifiers
        scan_id = str(uuid4())
        session_token = None
        
        # Auto-detect branch from GitHub API if not specified or is 'main'
        branch = request.branch or "main"
        if branch == "main":
            try:
                import httpx
                # Extract owner and repo from URL
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
                            logger.warning(f"GitHub API returned {response.status_code}, using default: main")
            except Exception as e:
                logger.warning(f"❌ Could not detect branch from GitHub API: {e}, using default: main")

        # For guest users, create anonymous scan record
        if not current_user:
            session_token = AnonymousScan.generate_session_token()
            expires_at = AnonymousScan.get_expiry()

            # Extract repo name
            repo_name = request.repository_url.rstrip("/").split("/")[-1].replace(".git", "")

            # Create anonymous scan session
            anon_scan = AnonymousScan(
                session_token=session_token,
                repository_url=request.repository_url,
                repository_name=repo_name,
                branch=branch,
                expires_at=expires_at,
                status="pending",
                linked_scan_id=scan_id,  # Link to scan_id from the start
            )
            db.add(anon_scan)
            logger.info(f"Anonymous scan session created: {session_token}")

        # Create scan record with the SAME ID used for progress tracking
        scan = Scan(
            id=uuid4(),  # This will be converted to string for scan_id
            user_id=current_user.id if current_user else None,
            repository_url=request.repository_url,
            branch=branch,
            status=ScanStatus.PENDING,
            progress=0,
        )
        
        # Use the scan's UUID as scan_id for progress tracking
        scan_id = str(scan.id)
        
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        
        # Initialize progress tracking with the SAME scan_id
        store = get_scan_progress_store()
        await store.create_scan(scan_id)
        await store.add_log(scan_id, f"Scan started for {request.repository_url}")
        await store.add_log(scan_id, f"Branch: {request.branch}")
        
        # Run scan synchronously with progress tracking
        try:
            SessionLocal = get_sync_session_factory()
            sync_db = SessionLocal()
            try:
                scan_service = SyncScanService(
                    db=sync_db,
                    include_ai_explanations=request.include_ai_explanations,
                    progress_store=store,
                    scan_id=scan_id,
                )
                
                # Get fresh scan from sync db using the SAME ID
                from app.models.scan import Scan as SyncScan
                sync_scan = sync_db.get(SyncScan, scan.id)
                
                if sync_scan:
                    # Execute scan synchronously with progress tracking
                    # SyncScanService uses sync db but has async methods - call without await
                    updated_scan = scan_service.execute_scan(sync_scan)

                    # Copy results back to async session
                    scan.status = updated_scan.status
                    scan.progress = updated_scan.progress
                    scan.overall_score = updated_scan.overall_score
                    scan.security_score = updated_scan.security_score
                    scan.completed_at = updated_scan.completed_at
                    await db.commit()
                    
                    logger.info(f"Scan completed: {scan.status.value}, score: {scan.overall_score}")
                else:
                    logger.error(f"Scan not found in sync DB: {scan.id}")
                    raise Exception(f"Scan not found: {scan.id}")
            finally:
                sync_db.close()
                
        except Exception as scan_error:
            error_msg = str(scan_error)
            logger.exception(f"Scan failed: {error_msg}")
            
            # Update scan status to failed
            scan.status = ScanStatus.FAILED
            scan.error_message = error_msg
            await db.commit()
            
            # Update progress store
            await store.fail_scan(scan_id, error_msg)
            
            # For guest users, update anonymous scan status too
            if not current_user and session_token:
                result = await db.execute(
                    select(AnonymousScan).where(AnonymousScan.session_token == session_token)
                )
                anon_scan = result.scalar_one_or_none()
                if anon_scan:
                    anon_scan.status = "failed"
                    await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Scan failed: {error_msg}",
            )
        
        # Return response with detected branch
        return {
            "scan_id": scan_id,
            "session_token": session_token,
            "status": "running",
            "message": "Scan started successfully",
            "repository_url": request.repository_url,
            "branch": branch,  # Use detected branch, not request.branch
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to start scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scan: {str(e)}",
        )


@router.get("/status/{scan_id}", response_model=Dict[str, Any])
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get real-time scan progress status.
    
    Returns current step, progress percentage, and logs.
    Works for BOTH guest and authenticated users.
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
        
        # Check access for authenticated scans
        if scan.user_id and not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required",
            )
        
        if scan.user_id and current_user and scan.user_id != current_user.id:
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


@router.get("/results/{scan_id}", response_model=Dict[str, Any])
async def get_scan_results(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get complete scan results after completion.
    
    Returns:
    - Security score
    - Findings with severity counts
    - AI suggestions
    - Detected technology stack
    """
    # Get scan
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check access
    if scan.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")
    
    if scan.user_id and current_user and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Scan not completed. Status: {scan.status.value}",
        )
    
    # Get findings
    from app.models.finding import Finding
    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = findings_result.scalars().all()

    # Count by severity
    severity_counts = {}
    for f in findings:
        severity = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    # Get AI suggestions
    from app.models.ai_suggestion import AISuggestion
    suggestions_result = await db.execute(
        select(AISuggestion).where(AISuggestion.scan_id == scan_id)
    )
    suggestions = suggestions_result.scalars().all()

    # Get detected technologies from findings file paths
    # (Progress store data expires, so we extract from permanent findings data)
    detected_technologies = []
    tech_files = {}

    for f in findings:
        if not f.file_path:
            continue

        path_lower = f.file_path.lower()

        # Docker
        if 'dockerfile' in path_lower or 'docker' in path_lower:
            if 'docker' not in detected_technologies:
                detected_technologies.append('docker')
            tech_files['docker'] = tech_files.get('docker', 0) + 1

        # Terraform
        if '.tf' in path_lower or 'terraform' in path_lower:
            if 'terraform' not in detected_technologies:
                detected_technologies.append('terraform')
            tech_files['terraform'] = tech_files.get('terraform', 0) + 1

        # Kubernetes
        if 'kubernetes' in path_lower or 'k8s' in path_lower or ('.yaml' in path_lower and 'deployment' in path_lower):
            if 'kubernetes' not in detected_technologies:
                detected_technologies.append('kubernetes')
            tech_files['kubernetes'] = tech_files.get('kubernetes', 0) + 1

        # GitHub Actions
        if '.github/workflows' in path_lower:
            if 'github_actions' not in detected_technologies:
                detected_technologies.append('github_actions')
            tech_files['github_actions'] = tech_files.get('github_actions', 0) + 1

        # AWS
        if 'aws' in path_lower or 'ec2' in path_lower or 's3' in path_lower or 'lambda' in path_lower:
            if 'aws' not in detected_technologies:
                detected_technologies.append('aws')
            tech_files['aws'] = tech_files.get('aws', 0) + 1

        # Azure
        if 'azure' in path_lower or 'aks' in path_lower:
            if 'azure' not in detected_technologies:
                detected_technologies.append('azure')
            tech_files['azure'] = tech_files.get('azure', 0) + 1

        # GCP
        if 'gcp' in path_lower or 'gke' in path_lower or 'google' in path_lower:
            if 'gcp' not in detected_technologies:
                detected_technologies.append('gcp')
            tech_files['gcp'] = tech_files.get('gcp', 0) + 1

        # Helm
        if 'helm' in path_lower or 'chart.yaml' in path_lower:
            if 'helm' not in detected_technologies:
                detected_technologies.append('helm')
            tech_files['helm'] = tech_files.get('helm', 0) + 1

        # Jenkins
        if 'jenkins' in path_lower or 'jenkinsfile' in path_lower:
            if 'jenkins' not in detected_technologies:
                detected_technologies.append('jenkins')
            tech_files['jenkins'] = tech_files.get('jenkins', 0) + 1

        # Prometheus
        if 'prometheus' in path_lower:
            if 'prometheus' not in detected_technologies:
                detected_technologies.append('prometheus')
            tech_files['prometheus'] = tech_files.get('prometheus', 0) + 1

        # Grafana
        if 'grafana' in path_lower:
            if 'grafana' not in detected_technologies:
                detected_technologies.append('grafana')
            tech_files['grafana'] = tech_files.get('grafana', 0) + 1

    # PHASE 2: Also add technologies from detected_stack (even if no findings for them)
    if scan.detected_stack:
        stack = scan.detected_stack
        if stack.get('has_jenkins') or stack.get('jenkins_files'):
            if 'jenkins' not in detected_technologies:
                detected_technologies.append('jenkins')
        if stack.get('has_gitlab_ci') or stack.get('gitlab_ci_files'):
            if 'gitlab_ci' not in detected_technologies:
                detected_technologies.append('gitlab_ci')
        if stack.get('has_circleci') or stack.get('circleci_files'):
            if 'circleci' not in detected_technologies:
                detected_technologies.append('circleci')
        if stack.get('has_azure_devops') or stack.get('azure_devops_files'):
            if 'azure_devops' not in detected_technologies:
                detected_technologies.append('azure_devops')
        if stack.get('has_ansible') or stack.get('ansible_files'):
            if 'ansible' not in detected_technologies:
                detected_technologies.append('ansible')
        if stack.get('has_prometheus') or stack.get('prometheus_files'):
            if 'prometheus' not in detected_technologies:
                detected_technologies.append('prometheus')
        if stack.get('has_grafana') or stack.get('grafana_files'):
            if 'grafana' not in detected_technologies:
                detected_technologies.append('grafana')

    # Calculate files analyzed from detected_stack (stored in scan.detected_stack)
    # This ensures we show files analyzed even if no findings were detected
    files_analyzed = 0
    if scan.detected_stack:
        # Count total files from all technologies
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

    # Fallback to counting from findings if detected_stack is empty
    if files_analyzed == 0:
        files_analyzed = len(set(f.file_path for f in findings if f.file_path))

    return {
        "scan_id": str(scan.id),
        "repository_url": scan.repository_url,
        "branch": scan.branch,
        "status": "completed",
        "overall_score": scan.overall_score,
        "security_score": scan.security_score,
        "scalability_score": scan.scalability_score,
        "reliability_score": scan.reliability_score,
        "cost_score": scan.cost_score,
        "observability_score": scan.observability_score,
        "findings_count": len(findings),
        "severity_counts": severity_counts,
        "files_analyzed": files_analyzed,
        "detected_technologies": detected_technologies,  # Extracted from findings
        "findings": [
            {
                "id": str(f.id),
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                "category": f.category.value if hasattr(f.category, 'value') else str(f.category),
                "description": f.description,
                "recommendation": f.recommendation,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "ai_explanation": f.ai_explanation,
                # AI Fix Generator fields (production-grade)
                "summary": f.summary,
                "risk": f.risk,
                "impact": f.impact,
                "fix_code": f.fix_code,
                "fix_example": f.fix_example,
                "full_example": f.full_example,
                # Parse best_practices if it's a JSON string
                "best_practices": json.loads(f.best_practices) if isinstance(f.best_practices, str) else (f.best_practices or []),
                # Use confidence_score (frontend expects this field name)
                "confidence_score": f.confidence_score or f.confidence or 0.8,
                "confidence": f.confidence or f.confidence_score or 0.8,  # Also include for backwards compatibility
                "documentation_url": f.documentation_url,
            }
            for f in findings
        ],
        "ai_suggestions_count": len(suggestions),
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "analysis_duration_seconds": scan.analysis_duration_seconds,
    }
