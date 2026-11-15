from __future__ import annotations

from typing import Any

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud.aws.orchestrator import cloud_scan_orchestrator
from app.cloud.websocket_manager import cloud_ws_manager
from app.config import settings
from app.core.encryption import get_encryption_service
from app.core.security import get_current_user
from app.core.validators import parse_uuid
from app.db.session import get_db
from app.models.ai_recommendation import AIRecommendation
from app.models.cloud import (
    CloudComplianceResult,
    CloudConnection,
    CloudCostRecommendation,
    CloudFinding,
    CloudResource,
    CloudScanSession,
)
from app.models.user import User
from app.schemas.cloud import (
    CloudAIRecommendationSummary,
    CloudComplianceResultSchema,
    CloudConnectionResponse,
    CloudConnectRequest,
    CloudConnectResponse,
    CloudCostSummary,
    CloudFindingSummary,
    CloudOverview,
    CloudResourceSummary,
    CloudScanSessionSchema,
    CreateJiraTicketRequest,
    JiraTicketResponse,
    ScanComparisonDelta,
    ScanComparisonResponse,
    ScanComparisonSection,
    WizardCompleteRequest,
    WizardInitRequest,
    WizardInitResponse,
    WizardStatusResponse,
    WizardVerifyResponse,
)
from app.services.jira_service import create_jira_ticket

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/cloud", tags=["Cloud Integration"])


# ── helpers ──

async def _owned_connection(
    connection_id: str,
    user: User,
    db: AsyncSession,
) -> CloudConnection:
    conn_uuid = parse_uuid(connection_id, "connection_id")
    result = await db.execute(
        select(CloudConnection).where(
            CloudConnection.id == conn_uuid,
            CloudConnection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="Cloud connection not found")
    return conn


# ── AWS Onboarding Wizard ──


@router.post("/aws/wizard/init", response_model=WizardInitResponse)
async def init_aws_wizard(
    payload: WizardInitRequest,
    user: User = Depends(get_current_user),
) -> WizardInitResponse:
    """Initialize the AWS onboarding wizard.

    Step 1 of the onboarding flow. User provides their AWS Account ID
    and optional friendly name. Backend generates External ID,
    CloudFormation URL, and all required parameters.
    """
    from app.cloud.wizard import init_wizard

    session = init_wizard(
        user_id=str(user.id),
        account_id=payload.account_id,
        connection_name=payload.connection_name,
    )

    return WizardInitResponse(
        wizard_id=session.wizard_id,
        account_id=session.account_id,
        connection_name=session.connection_name,
        external_id=session.external_id,
        stack_name=session.stack_name,
        role_name=session.role_name,
        cloudformation_url=session.cloudformation_url,
        template_url=session.template_url,
        status=session.status,
    )


@router.get("/aws/wizard/{wizard_id}/status", response_model=WizardStatusResponse)
async def get_wizard_status(
    wizard_id: str,
    user: User = Depends(get_current_user),
) -> WizardStatusResponse:
    """Get current wizard session status.

    Used by the frontend to poll for status updates while the user
    deploys the CloudFormation stack.
    """
    from app.cloud.wizard import get_wizard

    session = get_wizard(wizard_id)
    if not session:
        raise HTTPException(status_code=404, detail="Wizard session not found or expired")

    if session.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    return WizardStatusResponse(
        wizard_id=session.wizard_id,
        account_id=session.account_id,
        connection_name=session.connection_name,
        status=session.status,
        role_arn=session.role_arn,
        regions=session.regions,
        error_message=session.error_message,
        verified_account_id=session.verified_account_id,
        verified_permissions=session.verified_permissions,
    )


@router.post("/aws/wizard/{wizard_id}/verify", response_model=WizardVerifyResponse)
async def verify_aws_wizard(
    wizard_id: str,
    user: User = Depends(get_current_user),
) -> WizardVerifyResponse:
    """Verify the AWS connection after CloudFormation stack is deployed.

    Step 4 of the onboarding flow. Backend assumes the IAM role
    using STS and validates account ID, permissions, and regions.
    """
    from app.cloud.wizard import get_wizard, verify_connection

    session = get_wizard(wizard_id)
    if not session:
        raise HTTPException(status_code=404, detail="Wizard session not found or expired")

    if session.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    result = verify_connection(wizard_id)

    return WizardVerifyResponse(
        success=result["success"],
        account_id=result.get("account_id"),
        role_arn=result.get("role_arn"),
        permissions=result.get("permissions", {}),
        regions=result.get("regions", []),
        error=result.get("error"),
    )


@router.post("/aws/wizard/{wizard_id}/complete", response_model=CloudConnectResponse)
async def complete_aws_wizard(
    wizard_id: str,
    payload: WizardCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudConnectResponse:
    """Complete the wizard and create the cloud connection.

    Called after verification succeeds. Creates the CloudConnection
    record in the database.
    """
    from app.cloud.wizard import complete_wizard, get_wizard

    session = get_wizard(wizard_id)
    if not session:
        raise HTTPException(status_code=404, detail="Wizard session not found or expired")

    if session.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    if session.status != "verified":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete wizard in status: {session.status}",
        )

    encryption = get_encryption_service()
    encrypted_external_id = encryption.encrypt(session.external_id)

    # Check for existing connection
    existing = await db.execute(
        select(CloudConnection).where(
            CloudConnection.user_id == user.id,
            CloudConnection.account_id == session.account_id,
            CloudConnection.provider == "aws",
        )
    )
    existing_conn = existing.scalar_one_or_none()

    if existing_conn:
        existing_conn.role_arn = session.role_arn or ""
        existing_conn.external_id_encrypted = encrypted_external_id
        existing_conn.regions = payload.regions or session.regions
        existing_conn.connection_name = session.connection_name
        existing_conn.status = "active"
        conn = existing_conn
    else:
        conn = CloudConnection(
            user_id=user.id,
            provider="aws",
            account_id=session.account_id,
            role_arn=session.role_arn or "",
            external_id_encrypted=encrypted_external_id,
            regions=payload.regions or session.regions,
            connection_name=session.connection_name,
            status="active",
            scan_status="idle",
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    complete_wizard(wizard_id)

    logger.info(
        "wizard_completed",
        wizard_id=wizard_id,
        user_id=user.id,
        account_id=session.account_id,
    )

    return CloudConnectResponse(
        connection=CloudConnectionResponse.model_validate(conn),
        message="AWS account connected successfully",
    )


@router.get("/aws/wizard/template")
async def get_cloudformation_template(
    wizard_id: str,
) -> dict[str, str]:
    """Serve the CloudFormation template YAML.

    Returns the pre-rendered template content for the wizard session.
    """
    from app.cloud.wizard import get_wizard
    from app.services.cloudformation.template_service import (
        CloudFormationTemplateError,
        load_template,
        render_template,
    )

    session = get_wizard(wizard_id)
    if not session:
        raise HTTPException(status_code=404, detail="Wizard session not found or expired")

    try:
        template_content = load_template("aws-role-v1.yaml")
        rendered = render_template(template_content, {
            "ACCOUNT_ID": session.account_id,
            "EXTERNAL_ID": session.external_id,
            "ROLE_NAME": session.role_name,
            "SCANNER_ROLE_ARN": settings.DEVARCHAI_SCANNER_ARN,
        })
    except CloudFormationTemplateError as exc:
        raise HTTPException(status_code=500, detail=f"Template error: {exc}")

    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(content=rendered, media_type="application/x-yaml")


# ── Connection management ──

@router.post("/connect", response_model=CloudConnectResponse)
async def connect_cloud(
    payload: CloudConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudConnectResponse:
    """Validate OIDC credentials and create a cloud connection."""
    from app.cloud.aws.sts import STSAssumeRoleError, assume_customer_role

    encryption = get_encryption_service()
    encrypted_external_id = encryption.encrypt(payload.external_id)

    try:
        session = assume_customer_role(
            customer_account_id=payload.account_id,
            customer_role_name=payload.role_arn.split("/")[-1],
            external_id=payload.external_id,
            session_name=f"devarchai-validate-{payload.account_id}",
        )
        identity = session.client("sts").get_caller_identity()
        validated_account_id = identity["Account"]
    except STSAssumeRoleError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to assume IAM role: {exc.message}",
        )

    if validated_account_id != payload.account_id:
        raise HTTPException(
            status_code=400,
            detail=f"Account mismatch: expected {payload.account_id}, got {validated_account_id}",
        )

    existing = await db.execute(
        select(CloudConnection).where(
            CloudConnection.user_id == user.id,
            CloudConnection.account_id == payload.account_id,
            CloudConnection.provider == payload.provider,
        )
    )
    existing_conn = existing.scalar_one_or_none()

    if existing_conn:
        existing_conn.role_arn = payload.role_arn
        existing_conn.external_id_encrypted = encrypted_external_id
        existing_conn.regions = payload.regions
        existing_conn.connection_name = payload.connection_name or existing_conn.connection_name
        existing_conn.status = "active"
        conn = existing_conn
    else:
        conn = CloudConnection(
            user_id=user.id,
            provider=payload.provider,
            account_id=payload.account_id,
            role_arn=payload.role_arn,
            external_id_encrypted=encrypted_external_id,
            regions=payload.regions,
            connection_name=payload.connection_name or f"{payload.provider.upper()} ({payload.account_id})",
            status="active",
            scan_status="idle",
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    logger.info("cloud_connected", user_id=user.id, provider=payload.provider, account_id=payload.account_id)

    return CloudConnectResponse(
        connection=CloudConnectionResponse.model_validate(conn),
        message="Cloud account connected successfully",
    )


@router.get("/connections", response_model=list[CloudConnectionResponse])
async def list_connections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CloudConnectionResponse]:
    result = await db.execute(
        select(CloudConnection).where(CloudConnection.user_id == user.id).order_by(CloudConnection.created_at.desc())
    )
    conns = result.scalars().all()
    return [CloudConnectionResponse.model_validate(c) for c in conns]


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    conn = await _owned_connection(connection_id, user, db)
    await db.delete(conn)
    await db.commit()
    return {"message": "Connection deleted"}


# ── Scanning ──

@router.post("/connections/{connection_id}/scan")
async def trigger_scan(
    connection_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    logger.info(
        "SCAN_ENDPOINT_RECEIVED",
        connection_id=connection_id,
        user_id=str(user.id),
        method="POST",
        path=f"/cloud/connections/{connection_id}/scan",
    )

    conn = await _owned_connection(connection_id, user, db)

    if conn.scan_status == "scanning":
        # Allow retry if the scan appears stuck (>10 min stale)
        from datetime import UTC, datetime, timedelta

        stale_threshold = datetime.now(UTC) - timedelta(minutes=10)
        if conn.updated_at and conn.updated_at.replace(tzinfo=UTC) > stale_threshold:
            raise HTTPException(status_code=409, detail="Scan already in progress")
        # Stale scan — reset and allow retry
        logger.info(
            "STALE_SCAN_RESET",
            connection_id=connection_id,
            last_updated=str(conn.updated_at),
        )
        conn.scan_status = "idle"
        conn.scan_progress = 0.0

    conn.scan_status = "scanning"
    conn.scan_progress = 0.0
    await db.commit()
    await db.refresh(conn)

    logger.info(
        "SCAN_BACKGROUND_TASK_SCHEDULED",
        connection_id=connection_id,
        account_id=conn.account_id,
        provider=conn.provider,
        regions=conn.regions,
        user_id=str(user.id),
    )

    background_tasks.add_task(_run_scan_background, connection_id)

    return {"status": "scanning"}


async def _run_scan_background(connection_id: str) -> None:
    import time
    import traceback

    from app.db.session import get_session_factory

    bg_start = time.time()
    logger.info(
        "BACKGROUND_SCAN_STARTED",
        connection_id=connection_id,
    )

    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            await cloud_scan_orchestrator.run_full_scan(connection_id, db)
        except Exception as exc:
            tb = traceback.format_exc()
            bg_duration = round(time.time() - bg_start, 2)
            logger.error(
                "BACKGROUND_SCAN_FAILED",
                connection_id=connection_id,
                error=str(exc),
                traceback=tb,
                duration_seconds=bg_duration,
            )
            # Reset scan_status on a fresh session so the user can retry
            try:
                async with session_factory() as reset_db:
                    result = await reset_db.execute(
                        select(CloudConnection).where(CloudConnection.id == connection_id)
                    )
                    conn = result.scalar_one_or_none()
                    if conn:
                        conn.scan_status = "failed"
                        conn.scan_progress = 0.0
                        await reset_db.commit()
            except Exception:
                logger.error("cloud_scan_status_reset_failed", connection_id=connection_id)
            await cloud_ws_manager.scan_failed(connection_id, str(exc))

    bg_duration = round(time.time() - bg_start, 2)
    logger.info(
        "BACKGROUND_SCAN_FINISHED",
        connection_id=connection_id,
        duration_seconds=bg_duration,
    )


# ── Data retrieval ──

@router.get("/connections/{connection_id}/overview", response_model=CloudOverview)
async def get_overview(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudOverview:
    conn = await _owned_connection(connection_id, user, db)

    resource_summary = await _build_resource_summary(db, connection_id)
    finding_summary = await _build_finding_summary(db, connection_id)
    cost_summary = await _build_cost_summary(db, connection_id)

    compliance_result = await db.execute(
        select(CloudComplianceResult).where(
            CloudComplianceResult.connection_id == connection_id,
            CloudComplianceResult.status == "active",
        )
    )
    compliance_items = compliance_result.scalars().all()

    # AI recommendation summary — single source of truth query
    from sqlalchemy import func as sa_func

    ai_agg = await db.execute(
        select(
            AIRecommendation.severity,
            AIRecommendation.category,
            AIRecommendation.status,
            sa_func.count().label("cnt"),
            sa_func.coalesce(sa_func.sum(AIRecommendation.estimated_monthly_savings), 0).label("total_savings"),
            sa_func.coalesce(sa_func.avg(AIRecommendation.estimated_risk_reduction), 0).label("avg_risk"),
        ).where(
            AIRecommendation.connection_id == connection_id,
            AIRecommendation.status == "open",
        ).group_by(
            AIRecommendation.severity,
            AIRecommendation.category,
            AIRecommendation.status,
        )
    )
    ai_rows = ai_agg.all()

    ai_by_severity: dict[str, int] = {}
    ai_by_category: dict[str, int] = {}
    ai_by_status: dict[str, int] = {}
    ai_savings = 0.0
    ai_risk = 0.0
    ai_total = 0
    ai_critical = 0

    for row in ai_rows:
        sev = row.severity or "unknown"
        cat = row.category or "unknown"
        st = row.status or "open"
        cnt = row.cnt or 0
        ai_by_severity[sev] = ai_by_severity.get(sev, 0) + cnt
        ai_by_category[cat] = ai_by_category.get(cat, 0) + cnt
        ai_by_status[st] = ai_by_status.get(st, 0) + cnt
        ai_total += cnt
        ai_savings += float(row.total_savings or 0)
        ai_risk += float(row.avg_risk or 0)
        if sev == "critical":
            ai_critical += cnt

    return CloudOverview(
        connection=CloudConnectionResponse.model_validate(conn),
        resource_summary=resource_summary,
        finding_summary=finding_summary,
        cost_summary=cost_summary,
        compliance_results=[CloudComplianceResultSchema.model_validate(c) for c in compliance_items],
        ai_recommendation_summary=CloudAIRecommendationSummary(
            total=ai_total,
            by_severity=ai_by_severity,
            by_category=ai_by_category,
            by_status=ai_by_status,
            total_monthly_savings=round(ai_savings, 2),
            avg_risk_reduction=round(ai_risk / max(ai_total, 1), 1),
            critical_count=ai_critical,
        ),
        security_score=conn.security_score or 0.0,
        estimated_monthly_cost=conn.estimated_monthly_cost or 0.0,
    )


@router.get("/connections/{connection_id}/resources")
async def get_resources(
    connection_id: str,
    service: str | None = Query(None),
    region: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _owned_connection(connection_id, user, db)
    query = select(CloudResource).where(CloudResource.connection_id == connection_id)
    if service:
        query = query.where(CloudResource.service == service)
    if region:
        query = query.where(CloudResource.region == region)
    query = query.order_by(CloudResource.service, CloudResource.resource_type)
    result = await db.execute(query)
    resources = result.scalars().all()
    return {
        "resources": [
            {
                "id": str(r.id),
                "service": r.service,
                "resource_id": r.resource_id,
                "resource_name": r.resource_name,
                "resource_type": r.resource_type,
                "region": r.region,
                "status": r.status,
                "configuration": r.configuration,
                "tags": r.tags,
                "cost_monthly": r.cost_monthly,
            }
            for r in resources
        ],
        "total": len(resources),
    }


@router.get("/connections/{connection_id}/findings")
async def get_findings(
    connection_id: str,
    severity: str | None = Query(None),
    category: str | None = Query(None),
    service: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _owned_connection(connection_id, user, db)
    query = select(CloudFinding).where(
        CloudFinding.connection_id == connection_id,
        CloudFinding.status.in_(["open", "in_progress"]),
    )
    if severity:
        query = query.where(CloudFinding.severity == severity)
    if category:
        query = query.where(CloudFinding.category == category)
    if service:
        query = query.where(CloudFinding.service == service)
    query = query.order_by(
        CloudFinding.severity.desc(),
        CloudFinding.created_at.desc(),
    )
    result = await db.execute(query)
    findings = result.scalars().all()
    return {
        "findings": [
            {
                "id": str(f.id),
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "rule_id": f.rule_id,
                "resource_type": f.resource_type,
                "resource_id": f.resource_id,
                "region": f.region,
                "service": f.service,
                "compliance_frameworks": f.compliance_frameworks,
                "remediation": f.remediation,
                "evidence": f.evidence,
                "status": f.status,
                "created_at": str(f.created_at) if f.created_at else None,
            }
            for f in findings
        ],
        "total": len(findings),
    }


@router.get("/connections/{connection_id}/costs")
async def get_costs(
    connection_id: str,
    priority: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _owned_connection(connection_id, user, db)
    query = select(CloudCostRecommendation).where(
        CloudCostRecommendation.connection_id == connection_id,
        CloudCostRecommendation.status == "open",
    )
    if priority:
        query = query.where(CloudCostRecommendation.priority == priority)
    query = query.order_by(CloudCostRecommendation.monthly_savings.desc())
    result = await db.execute(query)
    costs = result.scalars().all()
    return {
        "recommendations": [
            {
                "id": str(c.id),
                "title": c.title,
                "description": c.description,
                "monthly_savings": c.monthly_savings,
                "current_cost": c.current_cost,
                "priority": c.priority,
                "category": c.category,
                "service": c.service,
                "resource_type": c.resource_type,
                "resource_id": c.resource_id,
                "region": c.region,
                "recommendation_type": c.recommendation_type,
                "estimated_impact": c.estimated_impact,
            }
            for c in costs
        ],
        "total": len(costs),
        "total_monthly_savings": sum(c.monthly_savings or 0 for c in costs),
    }


@router.get("/connections/{connection_id}/compliance")
async def get_compliance(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _owned_connection(connection_id, user, db)
    result = await db.execute(
        select(CloudComplianceResult).where(
            CloudComplianceResult.connection_id == connection_id,
            CloudComplianceResult.status == "active",
        )
    )
    items = result.scalars().all()
    return {
        "results": [
            {
                "id": str(c.id),
                "framework": c.framework,
                "total_controls": c.total_controls,
                "passed": c.passed,
                "failed": c.failed,
                "warnings": c.warnings,
                "not_applicable": c.not_applicable,
                "score": c.score,
                "details": c.details,
            }
            for c in items
        ],
        "total_frameworks": len(items),
        "average_score": round(sum(c.score or 0 for c in items) / max(len(items), 1), 1),
    }


# ── AI Recommendations ──────────────────────────────────────

SERVICE_CATEGORY: dict[str, str] = {
    "ec2": "security",
    "s3": "storage",
    "iam": "iam",
    "lambda": "performance",
    "rds": "performance",
    "eks": "performance",
    "ecs": "performance",
    "elb": "networking",
    "vpc": "networking",
    "cloudfront": "networking",
    "kms": "security",
    "guardduty": "security",
    "securityhub": "security",
    "cloudtrail": "compliance",
    "config": "compliance",
    "cloudwatch": "security",
    "ecr": "performance",
    "sns": "networking",
    "sqs": "performance",
    "dynamodb": "performance",
    "ebs": "storage",
    "efs": "storage",
}


def _recommendation_to_dict(rec: AIRecommendation) -> dict[str, Any]:
    return {
        "recommendation_id": str(rec.recommendation_id),
        "connection_id": str(rec.connection_id),
        "scan_id": str(rec.scan_id) if rec.scan_id else None,
        "provider": rec.provider,
        "service": rec.service,
        "resource_id": rec.resource_id,
        "resource_name": rec.resource_name,
        "category": rec.category,
        "severity": rec.severity,
        "title": rec.title,
        "summary": rec.summary,
        "technical_explanation": rec.technical_explanation,
        "business_impact": rec.business_impact,
        "estimated_monthly_savings": rec.estimated_monthly_savings or 0,
        "estimated_risk_reduction": rec.estimated_risk_reduction or 0,
        "aws_cli_fix": rec.aws_cli_fix,
        "terraform_fix": rec.terraform_fix,
        "cloudformation_fix": rec.cloudformation_fix,
        "console_steps": rec.console_steps or [],
        "official_documentation_url": rec.official_documentation_url,
        "recommendation_source": rec.recommendation_source,
        "status": rec.status,
        "created_at": str(rec.created_at) if rec.created_at else None,
    }


@router.get("/connections/{connection_id}/recommendations")
async def get_recommendations(
    connection_id: str,
    severity: str | None = Query(None),
    category: str | None = Query(None),
    service: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _owned_connection(connection_id, user, db)
    stmt = (
        select(AIRecommendation)
        .where(AIRecommendation.connection_id == connection_id)
        .order_by(
            AIRecommendation.severity.desc(),
            AIRecommendation.created_at.desc(),
        )
    )
    if status:
        stmt = stmt.where(AIRecommendation.status == status)
    result = await db.execute(stmt)
    recs = result.scalars().all()

    items = []
    for r in recs:
        if severity and r.severity != severity:
            continue
        if category and r.category != category:
            continue
        if service and r.service != service:
            continue
        if search:
            q = search.lower()
            if q not in (r.title or "").lower() and q not in (r.summary or "").lower() and q not in r.service.lower():
                continue
        items.append(_recommendation_to_dict(r))

    logger.info(
        "recommendations_returned connection_id=%s count=%d",
        connection_id, len(items),
    )
    return {"recommendations": items, "total": len(items)}


@router.get("/connections/{connection_id}/recommendations/summary")
async def get_recommendations_summary(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CloudAIRecommendationSummary:
    await _owned_connection(connection_id, user, db)
    ai_agg = await db.execute(
        select(
            AIRecommendation.severity,
            AIRecommendation.category,
            AIRecommendation.status,
            func.count().label("cnt"),
            func.coalesce(func.sum(AIRecommendation.estimated_monthly_savings), 0).label("total_savings"),
            func.coalesce(func.avg(AIRecommendation.estimated_risk_reduction), 0).label("avg_risk"),
        ).where(
            AIRecommendation.connection_id == connection_id,
            AIRecommendation.status == "open",
        ).group_by(
            AIRecommendation.severity,
            AIRecommendation.category,
            AIRecommendation.status,
        )
    )
    ai_rows = ai_agg.all()

    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_savings = 0.0
    total_risk = 0.0
    total_count = 0
    critical_count = 0

    for row in ai_rows:
        sev = row.severity or "unknown"
        cat = row.category or "unknown"
        st = row.status or "open"
        cnt = row.cnt or 0
        by_severity[sev] = by_severity.get(sev, 0) + cnt
        by_category[cat] = by_category.get(cat, 0) + cnt
        by_status[st] = by_status.get(st, 0) + cnt
        total_count += cnt
        total_savings += float(row.total_savings or 0)
        total_risk = float(row.avg_risk or 0)
        if sev == "critical":
            critical_count += cnt

    return CloudAIRecommendationSummary(
        total=total_count,
        by_severity=by_severity,
        by_category=by_category,
        by_status=by_status,
        total_monthly_savings=round(total_savings, 2),
        avg_risk_reduction=round(total_risk / max(total_count, 1), 1),
        critical_count=critical_count,
    )


@router.patch("/connections/{connection_id}/recommendations/{recommendation_id}/status")
async def update_recommendation_status(
    connection_id: str,
    recommendation_id: str,
    status: str = Query(..., pattern=r"^(open|resolved|ignored)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await _owned_connection(connection_id, user, db)
    result = await db.execute(
        select(AIRecommendation).where(
            AIRecommendation.recommendation_id == recommendation_id,
            AIRecommendation.connection_id == connection_id,
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.status = status
    await db.commit()
    return {"status": status}


# ── Jira Integration ──


@router.post("/connections/{connection_id}/recommendations/{recommendation_id}/jira")
async def create_jira_ticket_for_recommendation(
    connection_id: str,
    recommendation_id: str,
    payload: CreateJiraTicketRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JiraTicketResponse:
    parse_uuid(connection_id, "connection_id")
    parse_uuid(recommendation_id, "recommendation_id")
    await _owned_connection(connection_id, user, db)
    result = await db.execute(
        select(AIRecommendation).where(
            AIRecommendation.recommendation_id == recommendation_id,
            AIRecommendation.connection_id == connection_id,
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    result_data = await create_jira_ticket(
        jira_url=payload.jira_url,
        email=payload.email,
        api_token=payload.api_token,
        project_key=payload.project_key,
        summary=payload.summary or f"[DevArchAI] {rec.title}",
        description=payload.description or f"{rec.summary}\n\n---\nTechnical Explanation:\n{rec.technical_explanation}\n\nBusiness Impact:\n{rec.business_impact}\n\nService: {rec.service}\nResource: {rec.resource_id}\nSeverity: {rec.severity}\nCategory: {rec.category}",
        issue_type=payload.issue_type,
    )

    return JiraTicketResponse(
        success=result_data["success"],
        ticket_url=result_data["ticket_url"],
        ticket_key=result_data["ticket_key"],
        error=result_data["error"],
    )


# ── Export PDF ──


@router.post("/connections/{connection_id}/recommendations/export-pdf")
async def export_recommendations_pdf(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _owned_connection(connection_id, user, db)

    result = await db.execute(
        select(AIRecommendation)
        .where(
            AIRecommendation.connection_id == connection_id,
            AIRecommendation.status == "open",
        )
        .order_by(AIRecommendation.severity.desc(), AIRecommendation.created_at.desc())
    )
    recs = result.scalars().all()

    if not recs:
        raise HTTPException(status_code=404, detail="No open recommendations to export")

    pdf_data = _generate_recommendations_pdf(recs)

    from fastapi.responses import Response

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="recommendations-{connection_id[:8]}.pdf"'},
    )


def _generate_recommendations_pdf(recs: list[AIRecommendation]) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch)

    styles = {
        "title": ParagraphStyle("title", fontSize=16, leading=20, spaceAfter=12, textColor=colors.HexColor("#0F172A")),
        "heading": ParagraphStyle("heading", fontSize=12, leading=15, spaceAfter=6, spaceBefore=10, textColor=colors.HexColor("#1E293B")),
        "body": ParagraphStyle("body", fontSize=9, leading=12, spaceAfter=4, textColor=colors.HexColor("#334155")),
        "label": ParagraphStyle("label", fontSize=7, leading=9, textColor=colors.HexColor("#64748B")),
    }

    story = []
    story.append(Paragraph(f"AI Recommendations Report ({len(recs)} items)", styles["title"]))
    story.append(Spacer(1, 8))

    severity_colors = {
        "critical": colors.HexColor("#FEE2E2"),
        "high": colors.HexColor("#FFEDD5"),
        "medium": colors.HexColor("#FEF3C7"),
        "low": colors.HexColor("#DCFCE7"),
    }

    for i, rec in enumerate(recs):
        if i > 0:
            story.append(PageBreak())

        bg = severity_colors.get(rec.severity, colors.HexColor("#F8FAFC"))
        title_text = f"#{i + 1}: {rec.title} ({rec.severity.upper()})"
        story.append(Paragraph(title_text, styles["heading"]))

        data = [
            [Paragraph(f"<b>Service</b>: {rec.service}", styles["body"]), Paragraph(f"<b>Category</b>: {rec.category}", styles["body"])],
            [Paragraph(f"<b>Resource</b>: {rec.resource_id or 'N/A'}", styles["body"]), Paragraph(f"<b>Source</b>: {rec.recommendation_source}", styles["body"])],
        ]
        if rec.estimated_monthly_savings:
            data.append([Paragraph(f"<b>Monthly Savings</b>: ${rec.estimated_monthly_savings:.2f}", styles["body"]), ""])

        t = Table(data, colWidths=[3.2 * inch, 3.2 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

        story.append(Paragraph(f"<b>Summary</b><br/>{rec.summary}", styles["body"]))
        story.append(Spacer(1, 4))

        if rec.technical_explanation:
            story.append(Paragraph(f"<b>Technical Explanation</b><br/>{rec.technical_explanation}", styles["body"]))
            story.append(Spacer(1, 4))

        if rec.business_impact:
            story.append(Paragraph(f"<b>Business Impact</b><br/>{rec.business_impact}", styles["body"]))

        if rec.aws_cli_fix or rec.terraform_fix or rec.cloudformation_fix:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Remediation</b>", styles["body"]))
            if rec.aws_cli_fix:
                story.append(Paragraph(f"AWS CLI: {rec.aws_cli_fix[:200]}...", styles["body"]))
            if rec.terraform_fix:
                story.append(Paragraph(f"Terraform: {rec.terraform_fix[:200]}...", styles["body"]))
            if rec.cloudformation_fix:
                story.append(Paragraph(f"CloudFormation: {rec.cloudformation_fix[:200]}...", styles["body"]))

        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<i>Recommendation ID: {rec.recommendation_id} | Generated: {rec.created_at}</i>", styles["label"]))

    doc.build(story)
    return buf.getvalue()


# ── Scan Comparison ──


@router.get("/connections/{connection_id}/compare")
async def compare_scans(
    connection_id: str,
    old_scan_id: str | None = Query(None, description="Previous scan ID. If omitted, uses the second-to-last completed scan."),
    new_scan_id: str | None = Query(None, description="Latest scan ID. If omitted, uses the last completed scan."),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanComparisonResponse:
    await _owned_connection(connection_id, user, db)

    # Resolve scan IDs if not provided
    if not old_scan_id or not new_scan_id:
        scans_result = await db.execute(
            select(CloudScanSession)
            .where(
                CloudScanSession.connection_id == connection_id,
                CloudScanSession.status == "completed",
            )
            .order_by(CloudScanSession.finished_at.desc())
            .limit(2)
        )
        scans = scans_result.scalars().all()
        if len(scans) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 completed scans to compare")
        old_scan_id = str(scans[1].id) if not old_scan_id else old_scan_id
        new_scan_id = str(scans[0].id) if not new_scan_id else new_scan_id

    # Load scan sessions
    old_scan_result = await db.execute(
        select(CloudScanSession).where(CloudScanSession.id == old_scan_id)
    )
    old_scan = old_scan_result.scalar_one_or_none()
    new_scan_result = await db.execute(
        select(CloudScanSession).where(CloudScanSession.id == new_scan_id)
    )
    new_scan = new_scan_result.scalar_one_or_none()

    if not old_scan or not new_scan:
        raise HTTPException(status_code=404, detail="One or both scan sessions not found")

    old_stats = await _compute_scan_snapshot(db, connection_id, old_scan_id)
    new_stats = await _compute_scan_snapshot(db, connection_id, new_scan_id)

    def delta(old_val: int, new_val: int) -> int:
        return new_val - old_val

    return ScanComparisonResponse(
        connection_id=connection_id,
        old_scan_id=old_scan_id,
        new_scan_id=new_scan_id,
        old_scan=CloudScanSessionSchema.model_validate(old_scan),
        new_scan=CloudScanSessionSchema.model_validate(new_scan),
        deltas=ScanComparisonSection(
            resources=ScanComparisonDelta(
                added=max(0, delta(old_stats["resources"], new_stats["resources"])),
                removed=max(0, delta(new_stats["resources"], old_stats["resources"])),
                changed=0,
            ),
            findings=ScanComparisonDelta(
                added=max(0, delta(old_stats["findings"], new_stats["findings"])),
                removed=max(0, delta(new_stats["findings"], old_stats["findings"])),
                changed=0,
            ),
            cost_recommendations=ScanComparisonDelta(
                added=max(0, delta(old_stats["costs"], new_stats["costs"])),
                removed=max(0, delta(new_stats["costs"], old_stats["costs"])),
                changed=0,
            ),
            compliance=ScanComparisonDelta(
                added=max(0, delta(old_stats["compliance"], new_stats["compliance"])),
                removed=max(0, delta(new_stats["compliance"], old_stats["compliance"])),
                changed=0,
            ),
            ai_recommendations=ScanComparisonDelta(
                added=max(0, delta(old_stats["ai_recs"], new_stats["ai_recs"])),
                removed=max(0, delta(new_stats["ai_recs"], old_stats["ai_recs"])),
                changed=0,
            ),
        ),
    )


async def _compute_scan_snapshot(
    db: AsyncSession, connection_id: str, scan_id: str | None,
) -> dict[str, int]:
    """Count active records at the time of a given scan."""
    counts: dict[str, int] = {"resources": 0, "findings": 0, "costs": 0, "compliance": 0, "ai_recs": 0}

    if not scan_id:
        return counts

    # AI recs use scan_id FK directly
    result = await db.execute(
        select(func.count(AIRecommendation.recommendation_id)).where(
            AIRecommendation.connection_id == connection_id,
            AIRecommendation.scan_id == scan_id,
        )
    )
    counts["ai_recs"] = result.scalar() or 0

    # Resources, findings, costs, compliance use last_scan_id
    from app.models.cloud import (
        CloudComplianceResult,
        CloudCostRecommendation,
        CloudFinding,
        CloudResource,
    )

    for model, key in [
        (CloudResource, "resources"),
        (CloudFinding, "findings"),
        (CloudCostRecommendation, "costs"),
        (CloudComplianceResult, "compliance"),
    ]:
        result = await db.execute(
            select(func.count(model.id)).where(
                model.connection_id == connection_id,
                model.last_scan_id == scan_id,
            )
        )
        counts[key] = result.scalar() or 0

    return counts


# ── WebSocket ──

@router.websocket("/ws/{connection_id}")
async def cloud_scan_websocket(websocket: WebSocket, connection_id: str) -> None:
    from app.core.websocket_auth import authenticate_cloud_websocket

    if not await authenticate_cloud_websocket(websocket, connection_id):
        return
    connected = await cloud_ws_manager.connect(connection_id, websocket)
    if not connected:
        return
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong","data":{}}')
    except WebSocketDisconnect:
        await cloud_ws_manager.disconnect(connection_id, websocket)


# ── summary builders ──

async def _build_resource_summary(db: AsyncSession, connection_id: str) -> CloudResourceSummary:
    result = await db.execute(
        select(CloudResource).where(
            CloudResource.connection_id == connection_id,
            CloudResource.status != "deleted",
        )
    )
    resources = result.scalars().all()

    by_service: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_region: dict[str, int] = {}
    total_cost = 0.0

    for r in resources:
        by_service[r.service] = by_service.get(r.service, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.region:
            by_region[r.region] = by_region.get(r.region, 0) + 1
        if r.cost_monthly:
            total_cost += r.cost_monthly

    return CloudResourceSummary(
        total=len(resources),
        by_service=by_service,
        by_status=by_status,
        by_region=by_region,
        total_monthly_cost=round(total_cost, 2),
    )


async def _build_finding_summary(db: AsyncSession, connection_id: str) -> CloudFindingSummary:
    result = await db.execute(
        select(CloudFinding).where(
            CloudFinding.connection_id == connection_id,
            CloudFinding.status.in_(["open", "in_progress"]),
        )
    )
    findings = result.scalars().all()

    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_service: dict[str, int] = {}

    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_category[f.category] = by_category.get(f.category, 0) + 1
        by_service[f.service] = by_service.get(f.service, 0) + 1

    return CloudFindingSummary(
        total=len(findings),
        by_severity=by_severity,
        by_category=by_category,
        by_service=by_service,
    )


async def _build_cost_summary(db: AsyncSession, connection_id: str) -> CloudCostSummary:
    result = await db.execute(
        select(CloudCostRecommendation).where(
            CloudCostRecommendation.connection_id == connection_id,
            CloudCostRecommendation.status == "open",
        )
    )
    costs = result.scalars().all()

    by_service: dict[str, float] = {}
    by_priority: dict[str, int] = {}
    total_savings = 0.0

    for c in costs:
        by_service[c.service] = by_service.get(c.service, 0) + (c.monthly_savings or 0)
        by_priority[c.priority] = by_priority.get(c.priority, 0) + 1
        total_savings += c.monthly_savings or 0

    return CloudCostSummary(
        total=len(costs),
        total_monthly_savings=round(total_savings, 2),
        by_service=by_service,
        by_priority=by_priority,
    )
