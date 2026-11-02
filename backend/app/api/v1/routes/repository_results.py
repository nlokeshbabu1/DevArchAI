"""Repository results - get latest scan results for a repository."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_optional_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.finding_ai_job import FindingAIJob
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.services.ai_job_service import source_display
from app.services.ai_source_provenance import (
    documentation_status_display,
    normalize_sources,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repository Results"])


@router.get("/{repository_id}/results")
async def get_repository_results(
    repository_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get latest completed scan results for a repository."""
    try:
        repo_uuid = UUID(repository_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid repository ID")

    # Get repository
    result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Check access
    if repository.user_id and current_user and repository.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if repository.user_id and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get latest completed scan (eagerly load scanner_executions to avoid lazy-load in async context)
    scan_result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.scanner_executions))
        .where(
            Scan.repository_id == repo_uuid,
            Scan.status == ScanStatus.COMPLETED,
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    scan = scan_result.scalar_one_or_none()

    if not scan:
        return {
            "repository_id": str(repository.id),
            "repository_name": repository.name,
            "repository_url": repository.url,
            "default_branch": repository.default_branch,
            "description": repository.description,
            "has_scan": False,
            "scan": None,
        }

    # Get findings for this scan
    findings_result = await db.execute(
        select(Finding)
        .where(Finding.scan_id == scan.id)
        .order_by(Finding.severity, Finding.created_at)
    )
    findings = findings_result.scalars().all()

    # Map each finding to its AI job so provenance is consistent across routes.
    jobs = (
        await db.execute(select(FindingAIJob).where(FindingAIJob.scan_id == scan.id))
    ).scalars().all()
    job_by_finding: dict[str, FindingAIJob] = {}
    for job in jobs:
        for finding_id in job.finding_ids or []:
            job_by_finding[str(finding_id)] = job

    # Count by severity
    import json

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Detect technologies
    detected_technologies = []
    files_analyzed = 0
    if scan.detected_stack:
        stack = scan.detected_stack
        tech_map = {
            "has_docker": "Docker",
            "has_terraform": "Terraform",
            "has_kubernetes": "Kubernetes",
            "has_helm": "Helm",
            "has_github_actions": "GitHub Actions",
            "has_gitlab_ci": "GitLab CI",
            "has_jenkins": "Jenkins",
            "has_docker_compose": "Docker Compose",
            "has_ansible": "Ansible",
            "has_circleci": "CircleCI",
            "has_azure_devops": "Azure DevOps",
        }
        for key, name in tech_map.items():
            if stack.get(key) or stack.get(key.replace("has_", "") + "_files"):
                detected_technologies.append(name)
        file_keys = [k for k in stack if k.endswith("_files")]
        files_analyzed = sum(len(stack.get(k, [])) for k in file_keys)

    if files_analyzed == 0:
        files_analyzed = len({f.file_path for f in findings if f.file_path})

    return {
        "repository_id": str(repository.id),
        "repository_name": repository.name,
        "repository_url": repository.url,
        "default_branch": repository.default_branch,
        "description": repository.description,
        "has_scan": True,
        "scan": {
            "id": str(scan.id),
            "user_id": str(scan.user_id) if scan.user_id else None,
            "repository_id": str(scan.repository_id) if scan.repository_id else None,
            "repository_url": scan.repository_url,
            "branch": scan.branch,
            "status": scan.status.value if hasattr(scan.status, "value") else str(scan.status),
            "scan_status": scan.status.value if hasattr(scan.status, "value") else str(scan.status),
            "ai_status": scan.ai_status or "pending",
            "progress": scan.progress,
            "error_message": scan.error_message,
            "overall_score": scan.overall_score,
            "security_score": scan.security_score,
            "scalability_score": scan.scalability_score,
            "reliability_score": scan.reliability_score,
            "cost_score": scan.cost_score,
            "observability_score": scan.observability_score,
            "detected_stack": scan.detected_stack,
            "detected_technologies": detected_technologies,
            "files_analyzed": files_analyzed,
            "findings_count": len(findings),
            "severity_counts": severity_counts,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "analysis_duration_seconds": scan.analysis_duration_seconds,
            "created_at": scan.created_at.isoformat(),
            "updated_at": scan.updated_at.isoformat() if scan.updated_at else None,
            "scanner_executions": [
                {
                    "scanner_name": se.scanner_name,
                    "scanner_id": se.scanner_id,
                    "version": se.version,
                    "status": se.status,
                    "applicable": se.applicable,
                    "enabled": se.enabled,
                    "execution_start": se.execution_start.isoformat()
                    if se.execution_start
                    else None,
                    "execution_end": se.execution_end.isoformat() if se.execution_end else None,
                    "duration_ms": se.duration_ms,
                    "files_scanned": se.files_scanned,
                    "rules_executed": se.rules_executed,
                    "findings_count": se.findings_count,
                    "skipped_reason": se.skipped_reason,
                    "error_message": se.error_message,
                }
                for se in (scan.scanner_executions or [])
            ],
            "findings": [
                {
                    "id": str(f.id),
                    "scan_id": str(f.scan_id),
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity.value
                    if hasattr(f.severity, "value")
                    else str(f.severity),
                    "category": f.category.value
                    if hasattr(f.category, "value")
                    else str(f.category),
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "ai_explanation": f.ai_explanation,
                    "ai_generated": f.ai_generated,
                    "summary": f.summary,
                    "risk": f.risk,
                    "impact": f.impact,
                    "fix_code": f.fix_code,
                    "fix_example": f.fix_example,
                    "full_example": f.full_example,
                    "best_practices": json.loads(f.best_practices) if f.best_practices else [],
                    "confidence_score": f.confidence_score,
                    "documentation_url": f.documentation_url,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "scanner_name": f.scanner_name,
                    "scanner_rule_id": f.scanner_rule_id,
                    "package": f.package,
                    "installed_version": f.installed_version,
                    "fixed_version": f.fixed_version,
                    "cve": f.cve,
                    "cwe": f.cwe,
                    "references": json.loads(f.references) if f.references else [],
                    "evidence": f.evidence,
                    "ai_source": (job_by_finding.get(str(f.id)).source if job_by_finding.get(str(f.id)) else None),
                    "source_display": source_display(
                        job_by_finding.get(str(f.id)).source if job_by_finding.get(str(f.id)) else None
                    ),
                    "documentation_status": (
                        job_by_finding.get(str(f.id)).documentation_status
                        if job_by_finding.get(str(f.id))
                        else None
                    ),
                    "documentation_status_display": documentation_status_display(
                        job_by_finding.get(str(f.id)).documentation_status
                        if job_by_finding.get(str(f.id))
                        else None
                    ),
                    "sources": (
                        normalize_sources(job_by_finding.get(str(f.id)).sources)
                        if job_by_finding.get(str(f.id))
                        else []
                    ),
                    "job": (
                        {
                            "id": str(job_by_finding[str(f.id)].id),
                            "status": job_by_finding[str(f.id)].status,
                            "source": job_by_finding[str(f.id)].source,
                        }
                        if str(f.id) in job_by_finding
                        else None
                    ),
                }
                for f in findings
            ],
        },
    }


@router.get("/{repository_id}/latest-scan")
async def get_repository_latest_scan(
    repository_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get the latest scan (any status) for a repository."""
    try:
        repo_uuid = UUID(repository_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid repository ID")

    result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    if repository.user_id and current_user and repository.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    scan_result = await db.execute(
        select(Scan)
        .where(Scan.repository_id == repo_uuid)
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    scan = scan_result.scalar_one_or_none()

    if not scan:
        return {"repository_id": str(repository.id), "has_scan": False, "scan": None}

    return {
        "repository_id": str(repository.id),
        "has_scan": True,
        "scan": {
            "id": str(scan.id),
            "status": scan.status.value if hasattr(scan.status, "value") else str(scan.status),
            "ai_status": scan.ai_status or "pending",
            "created_at": scan.created_at.isoformat(),
        },
    }
