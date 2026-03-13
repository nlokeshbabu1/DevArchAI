"""Repository Analysis routes."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException
from app.db.session import get_db
from app.models.repo_analysis import RepoAnalysis
from app.schemas.common import MessageResponse
from app.schemas.repo_analysis import (
    BestPracticesResponse,
    DevOpsStack,
    MissingBestPractice,
    RepoAnalysisListItem,
    RepoAnalysisListResponse,
    RepoAnalysisRequest,
    RepoAnalysisResponse,
)
from app.services.repo_analysis_service import RepoAnalysisService, get_analysis_service
from app.services.scan_service import ScanService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analyze", tags=["Repository Analysis"])


# Static routes MUST come before dynamic routes with path parameters
@router.post(
    "/repo/deep",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Deep Repository Analysis with Rule Engine",
    description="Analyze a GitHub repository with full rule engine execution and AI explanations.",
)
async def analyze_repository_deep(
    request: RepoAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Deep analysis of a GitHub repository.

    This endpoint:
    1. Clones the repository
    2. Parses Dockerfile, Terraform, Kubernetes, CI/CD files
    3. Runs rule engine (35+ rules)
    4. Generates AI explanations
    5. Calculates DevOps maturity score
    6. Returns detailed findings

    **Example:**
    ```json
    {
        "repo_url": "https://github.com/example/infra",
        "branch": "main"
    }
    ```
    """
    logger.info("Deep analysis requested", repo_url=request.repo_url, branch=request.branch)

    service = ScanService(db=db, include_ai_explanations=True)

    try:
        result = await service.analyze_repository_sync(
            repo_url=request.repo_url,
            branch=request.branch or "main",
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Analysis failed"),
            )

        logger.info(
            "Deep analysis completed",
            repo_url=request.repo_url,
            findings_count=len(result.get("findings", [])),
            score=result.get("scores", {}).get("overall"),
        )

        return result

    except InvalidRepositoryException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RepositoryNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Deep analysis failed", repo_url=request.repo_url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.post(
    "/repo",
    response_model=RepoAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze GitHub Repository",
    description="Analyze a GitHub repository to detect DevOps stack and calculate DevOps score.",
)
async def analyze_repository(
    request: RepoAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a GitHub repository for DevOps configuration.

    This endpoint:
    1. Validates the GitHub URL
    2. Fetches the repository file tree
    3. Detects DevOps tools (Docker, Terraform, Kubernetes, CI/CD, etc.)
    4. Calculates a DevOps maturity score
    5. Stores the analysis result

    **Example:**
    ```json
    {
        "repo_url": "https://github.com/torvalds/linux"
    }
    ```
    """
    service = get_analysis_service(db, settings.GITHUB_TOKEN)

    try:
        result = await service.analyze_repository(request.repo_url)

        return RepoAnalysisResponse(
            repo=result["repo"],
            repo_url=result["repo_url"],
            repo_owner=result["repo_owner"],
            repo_name=result["repo_name"],
            devops_stack=result["devops_stack"],
            devops_score=result["devops_score"],
            files_analyzed=result["files_analyzed"],
            analysis_id=result["analysis_id"],
            created_at=result["created_at"],
        )

    except InvalidRepositoryException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RepositoryNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Repository analysis failed", repo_url=request.repo_url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )
    finally:
        await service.close()


@router.get(
    "/repo/list",
    response_model=RepoAnalysisListResponse,
    summary="List Repository Analyses",
    description="Get recent repository analyses.",
)
async def list_analyses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List recent repository analyses."""
    offset = (page - 1) * page_size

    # Get total count
    count_query = select(func.count(RepoAnalysis.id))
    total = await db.scalar(count_query)

    # Get analyses
    result = await db.execute(
        select(RepoAnalysis)
        .order_by(RepoAnalysis.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    analyses = result.scalars().all()

    return RepoAnalysisListResponse(
        analyses=[
            RepoAnalysisListItem(
                id=a.id,
                repo_url=a.repo_url,
                repo_full_name=a.repo_full_name,
                devops_score=a.devops_score,
                has_docker=a.has_docker,
                has_terraform=a.has_terraform,
                has_kubernetes=a.has_kubernetes,
                has_cicd=a.has_cicd,
                cicd_type=a.cicd_type,
                created_at=a.created_at,
            )
            for a in analyses
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# Dynamic routes with path parameters MUST come AFTER static routes
@router.get(
    "/repo/{analysis_id}",
    response_model=RepoAnalysisResponse,
    summary="Get Analysis Result",
    description="Get a specific analysis result by ID.",
)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis result by ID."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    # Convert detected_stack JSON to DevOpsStack
    stack_data = analysis.detected_stack or {}

    return RepoAnalysisResponse(
        repo=analysis.repo_full_name,
        repo_url=analysis.repo_url,
        repo_owner=analysis.repo_owner,
        repo_name=analysis.repo_name,
        devops_stack=DevOpsStack(
            docker=stack_data.get("docker", False),
            docker_files=stack_data.get("docker_files", []),
            terraform=stack_data.get("terraform", False),
            terraform_files=stack_data.get("terraform_files", []),
            pulumi=stack_data.get("pulumi", False),
            pulumi_files=stack_data.get("pulumi_files", []),
            cloudformation=stack_data.get("cloudformation", False),
            cloudformation_files=stack_data.get("cloudformation_files", []),
            ansible=stack_data.get("ansible", False),
            ansible_files=stack_data.get("ansible_files", []),
            kubernetes=stack_data.get("kubernetes", False),
            kubernetes_files=stack_data.get("kubernetes_files", []),
            helm=stack_data.get("helm", False),
            helm_files=stack_data.get("helm_files", []),
            kustomize=stack_data.get("kustomize", False),
            kustomize_files=stack_data.get("kustomize_files", []),
            cicd=stack_data.get("cicd"),
            cicd_files=stack_data.get("cicd_files", []),
            monitoring=stack_data.get("monitoring", False),
            monitoring_files=stack_data.get("monitoring_files", []),
            prometheus=stack_data.get("prometheus", False),
            prometheus_files=stack_data.get("prometheus_files", []),
            grafana=stack_data.get("grafana", False),
            grafana_files=stack_data.get("grafana_files", []),
            datadog=stack_data.get("datadog", False),
            datadog_files=stack_data.get("datadog_files", []),
            service_mesh=stack_data.get("service_mesh", False),
            service_mesh_files=stack_data.get("service_mesh_files", []),
            istio=stack_data.get("istio", False),
            istio_files=stack_data.get("istio_files", []),
            security_scanning=stack_data.get("security_scanning", False),
            security_files=stack_data.get("security_files", []),
        ),
        devops_score=analysis.devops_score,
        files_analyzed=analysis.files_analyzed,
        analysis_id=analysis.id,
        created_at=analysis.created_at,
    )


@router.get(
    "/repo/{analysis_id}/best-practices",
    response_model=BestPracticesResponse,
    summary="Get Missing Best Practices",
    description="Get missing best practices for an analysis.",
)
async def get_missing_best_practices(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get missing best practices based on analysis."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    # Reconstruct stack result from stored data
    stack_data = analysis.detected_stack or {}

    # Create a simple object with the same interface
    class StackResult:
        def __init__(self, data):
            self.docker = data.get("docker", False)
            self.docker_files = data.get("docker_files", [])
            self.terraform = data.get("terraform", False)
            self.terraform_files = data.get("terraform_files", [])
            self.ansible = data.get("ansible", False)
            self.ansible_files = data.get("ansible_files", [])
            self.pulumi = data.get("pulumi", False)
            self.pulumi_files = data.get("pulumi_files", [])
            self.cloudformation = data.get("cloudformation", False)
            self.cloudformation_files = data.get("cloudformation_files", [])
            self.kubernetes = data.get("kubernetes", False)
            self.kubernetes_files = data.get("kubernetes_files", [])
            self.helm = data.get("helm", False)
            self.helm_files = data.get("helm_files", [])
            self.kustomize = data.get("kustomize", False)
            self.kustomize_files = data.get("kustomize_files", [])
            self.cicd = data.get("cicd")
            self.cicd_files = data.get("cicd_files", [])
            self.monitoring = data.get("monitoring", False)
            self.monitoring_files = data.get("monitoring_files", [])
            self.prometheus = data.get("prometheus", False)
            self.prometheus_files = data.get("prometheus_files", [])
            self.grafana = data.get("grafana", False)
            self.grafana_files = data.get("grafana_files", [])
            self.datadog = data.get("datadog", False)
            self.datadog_files = data.get("datadog_files", [])
            self.service_mesh = data.get("service_mesh", False)
            self.service_mesh_files = data.get("service_mesh_files", [])
            self.istio = data.get("istio", False)
            self.istio_files = data.get("istio_files", [])
            self.security_scanning = data.get("security_scanning", False)
            self.security_files = data.get("security_files", [])

    stack_result = StackResult(stack_data)
    service = RepoAnalysisService(db, settings.GITHUB_TOKEN)
    missing = service.get_missing_best_practices(stack_result)
    await service.close()

    return BestPracticesResponse(
        repo=analysis.repo_full_name,
        missing_practices=[
            MissingBestPractice(
                category=m["category"],
                title=m["title"],
                description=m["description"],
                severity=m["severity"],
                recommendation=m["recommendation"],
            )
            for m in missing
        ],
        total_missing=len(missing),
        score=analysis.devops_score or 0.0,
    )


@router.delete(
    "/repo/{analysis_id}",
    response_model=MessageResponse,
    summary="Delete Analysis",
    description="Delete a specific analysis result.",
)
async def delete_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete analysis result."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    await db.delete(analysis)
    await db.commit()

    return MessageResponse(message="Analysis deleted successfully", success=True)
