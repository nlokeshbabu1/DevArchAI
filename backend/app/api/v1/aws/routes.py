"""AWS cloud integration API routes."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import get_encryption_service
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.aws import AWSAccount, AWSCostRecommendation, AWSFinding, AWSInventory
from app.models.user import User
from app.schemas.aws import (
    AWSAccountResponse,
    AWSConnectRequest,
    AWSConnectResponse,
    AWSCostRecommendationItem,
    AWSFindingItem,
    AWSInventoryItem,
)
from app.services.aws.aws_client import AWSIntegrationError, validate_credentials
from app.services.aws.aws_scan_service import AWSScanService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/aws", tags=["AWS"])


async def _owned_account(db: AsyncSession, user_id, account_uuid: UUID | None) -> AWSAccount:
    query = select(AWSAccount).where(AWSAccount.user_id == user_id, AWSAccount.is_active.is_(True))
    if account_uuid:
        query = query.where(AWSAccount.id == account_uuid)
    account = await db.scalar(query.order_by(AWSAccount.created_at.desc()).limit(1))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found")
    return account


@router.post("/connect", response_model=AWSConnectResponse, status_code=status.HTTP_201_CREATED)
async def connect_aws_account(
    payload: AWSConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate AWS credentials, store encrypted secrets, and start a background scan."""
    if payload.connection_type != "access_key":
        raise HTTPException(status_code=400, detail="AssumeRole is reserved for a future release")

    try:
        identity = await validate_credentials(payload.access_key_id, payload.secret_access_key, payload.default_region)
    except AWSIntegrationError as exc:
        logger.warning("AWS credential validation failed", user_id=str(current_user.id), error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or insufficient AWS credentials")

    encryption = get_encryption_service()
    existing = await db.scalar(
        select(AWSAccount).where(
            AWSAccount.user_id == current_user.id,
            AWSAccount.account_id == identity["account_id"],
            AWSAccount.is_active.is_(True),
        )
    )
    account = existing or AWSAccount(user_id=current_user.id, account_id=identity["account_id"])
    account.account_alias = payload.account_alias
    account.connection_type = payload.connection_type
    account.default_region = payload.default_region
    account.access_key_id_encrypted = encryption.encrypt(payload.access_key_id)
    account.secret_access_key_encrypted = encryption.encrypt(payload.secret_access_key)
    account.role_arn_encrypted = encryption.encrypt(payload.role_arn) if payload.role_arn else None
    account.external_id_encrypted = encryption.encrypt(payload.external_id) if payload.external_id else None
    account.scan_status = "queued"
    account.scan_progress = 0
    account.last_error = None

    db.add(account)
    await db.commit()
    await db.refresh(account)
    logger.info("AWS account connected", user_id=str(current_user.id), aws_account_id=str(account.id), cloud_account_id=account.account_id)

    background_tasks.add_task(AWSScanService().run_full_scan, account.id)
    return AWSConnectResponse(account=account, message="AWS account connected. Inventory scan queued.")


@router.get("/accounts", response_model=list[AWSAccountResponse])
async def list_aws_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AWSAccount)
        .where(AWSAccount.user_id == current_user.id, AWSAccount.is_active.is_(True))
        .order_by(AWSAccount.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/accounts/{account_id}/scan", response_model=AWSAccountResponse)
async def scan_aws_account(
    account_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue a fresh AWS scan without changing existing AWS API contracts."""
    account = await _owned_account(db, current_user.id, account_id)
    if account.scan_status in {"queued", "running"}:
        return account

    account.scan_status = "queued"
    account.scan_progress = 0
    account.last_error = None
    await db.commit()
    await db.refresh(account)
    background_tasks.add_task(AWSScanService().run_full_scan, account.id)
    logger.info("AWS inventory scan started", user_id=str(current_user.id), aws_account_id=str(account.id), source="manual")
    return account


@router.delete("/accounts/{account_id}")
async def disconnect_aws_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-disconnect AWS account without exposing or returning secrets."""
    account = await _owned_account(db, current_user.id, account_id)
    account.is_active = False
    account.scan_status = "disconnected"
    await db.commit()
    logger.info("AWS account disconnected", user_id=str(current_user.id), aws_account_id=str(account.id))
    return {"message": "AWS account disconnected", "success": True}


@router.get("/inventory")
async def get_aws_inventory(
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _owned_account(db, current_user.id, account_id)
    result = await db.execute(select(AWSInventory).where(AWSInventory.account_id == account.id).order_by(AWSInventory.resource_type, AWSInventory.name))
    items = list(result.scalars().all())
    counts = Counter(item.resource_type for item in items)
    return {"account": AWSAccountResponse.model_validate(account), "summary": dict(counts), "items": [AWSInventoryItem.model_validate(item) for item in items]}


@router.get("/security")
async def get_aws_security(
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _owned_account(db, current_user.id, account_id)
    result = await db.execute(select(AWSFinding).where(AWSFinding.account_id == account.id, AWSFinding.category == "security").order_by(AWSFinding.severity, AWSFinding.detected_at.desc()))
    items = list(result.scalars().all())
    severity_counts = Counter(item.severity for item in items)
    score = max(0, 100 - severity_counts.get("critical", 0) * 25 - severity_counts.get("high", 0) * 15 - severity_counts.get("medium", 0) * 7 - severity_counts.get("low", 0) * 3)
    return {"account": AWSAccountResponse.model_validate(account), "score": score, "severity_counts": dict(severity_counts), "items": [AWSFindingItem.model_validate(item) for item in items]}


@router.get("/cost")
async def get_aws_cost(
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _owned_account(db, current_user.id, account_id)
    result = await db.execute(select(AWSCostRecommendation).where(AWSCostRecommendation.account_id == account.id).order_by(AWSCostRecommendation.estimated_monthly_savings.desc()))
    items = list(result.scalars().all())
    total_savings = sum(item.estimated_monthly_savings for item in items)
    score = max(0, 100 - min(80, int(total_savings / 10)))
    return {"account": AWSAccountResponse.model_validate(account), "score": score, "estimated_monthly_savings": total_savings, "items": [AWSCostRecommendationItem.model_validate(item) for item in items]}


@router.get("/iam-analysis")
async def get_aws_iam_analysis(
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _owned_account(db, current_user.id, account_id)
    result = await db.execute(select(AWSFinding).where(AWSFinding.account_id == account.id, AWSFinding.category == "iam").order_by(AWSFinding.severity, AWSFinding.detected_at.desc()))
    items = list(result.scalars().all())
    return {"account": AWSAccountResponse.model_validate(account), "total": len(items), "items": [AWSFindingItem.model_validate(item) for item in items]}


@router.get("/overview")
async def get_aws_overview(
    account_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _owned_account(db, current_user.id, account_id)
    inventory_counts = await db.execute(select(AWSInventory.resource_type, func.count(AWSInventory.id)).where(AWSInventory.account_id == account.id).group_by(AWSInventory.resource_type))
    finding_counts = await db.execute(select(AWSFinding.severity, func.count(AWSFinding.id)).where(AWSFinding.account_id == account.id).group_by(AWSFinding.severity))
    savings = await db.scalar(select(func.coalesce(func.sum(AWSCostRecommendation.estimated_monthly_savings), 0)).where(AWSCostRecommendation.account_id == account.id))
    regions = await db.execute(select(AWSInventory.region).where(AWSInventory.account_id == account.id, AWSInventory.region.is_not(None)).distinct())
    resource_total = await db.scalar(select(func.count(AWSInventory.id)).where(AWSInventory.account_id == account.id))
    finding_total = await db.scalar(select(func.count(AWSFinding.id)).where(AWSFinding.account_id == account.id))
    recommendation_total = await db.scalar(select(func.count(AWSCostRecommendation.id)).where(AWSCostRecommendation.account_id == account.id))
    severity_counts = {severity: count for severity, count in finding_counts.all()}
    security_score = max(0, 100 - severity_counts.get("critical", 0) * 25 - severity_counts.get("high", 0) * 15 - severity_counts.get("medium", 0) * 7 - severity_counts.get("low", 0) * 3)
    cost_score = max(0, 100 - min(80, int(float(savings or 0) / 10)))
    sync_time = account.last_scanned_at or account.updated_at or datetime.now(UTC)
    region_names = sorted({region for (region,) in regions.all() if region})
    return {
        "account": AWSAccountResponse.model_validate(account),
        "inventory_summary": {resource_type: count for resource_type, count in inventory_counts.all()},
        "severity_counts": severity_counts,
        "security_score": security_score,
        "cost_score": cost_score,
        "estimated_monthly_savings": float(savings or 0),
        "posture_grade": "A" if security_score >= 90 else "B" if security_score >= 80 else "C" if security_score >= 70 else "D" if security_score >= 60 else "F",
        "last_sync": sync_time.isoformat() if sync_time else None,
        "scan_duration_seconds": None,
        "regions_scanned": region_names,
        "aws_api_health": "healthy" if account.scan_status != "failed" else "degraded",
        "resource_coverage": 100 if resource_total else 0,
        "queue_status": account.scan_status,
        "totals": {
            "resources": int(resource_total or 0),
            "findings": int(finding_total or 0),
            "recommendations": int(recommendation_total or 0),
        },
        "trend_data": {
            "security": [{"timestamp": sync_time.isoformat(), "critical": severity_counts.get("critical", 0), "high": severity_counts.get("high", 0), "medium": severity_counts.get("medium", 0), "low": severity_counts.get("low", 0)}] if sync_time else [],
            "cost": [{"timestamp": sync_time.isoformat(), "estimated_monthly_savings": float(savings or 0), "recommendations": int(recommendation_total or 0)}] if sync_time else [],
            "resources": [{"timestamp": sync_time.isoformat(), "total": int(resource_total or 0)}] if sync_time else [],
        },
    }
