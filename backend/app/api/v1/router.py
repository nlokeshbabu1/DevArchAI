"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.aws_findings import router as aws_findings_router
from app.api.v1.aws.routes import router as aws_router
from app.api.v1.routes import (
    ai_suggestions,
    auth,
    billing,
    dashboard,
    findings,
    github,
    github_installations,
    github_webhook,
    gitlab,
    gitlab_auth,
    health,
    integrations,
    integrations_connect,
    knowledge,
    kubernetes,
    public_scans,
    pull_requests,
    repo_analysis,
    reports,
    repositories,
    scans,
    scan_ai,
    settings,
    unified_scan,
)
from app.api.v1.routes.repository_results import router as repository_results_router
from app.cloud.routes import router as cloud_router

api_router = APIRouter()

api_router.include_router(ai_suggestions.router)
api_router.include_router(auth.router)
api_router.include_router(billing.router)
api_router.include_router(dashboard.router)
api_router.include_router(findings.router)
api_router.include_router(github.router)
api_router.include_router(github_installations.router)
api_router.include_router(github_webhook.router)
api_router.include_router(gitlab.router)
api_router.include_router(gitlab_auth.router)
api_router.include_router(health.router)
api_router.include_router(integrations.router)
api_router.include_router(integrations_connect.router)
api_router.include_router(kubernetes.router)
api_router.include_router(knowledge.router)
api_router.include_router(pull_requests.router)
api_router.include_router(scans.router)
api_router.include_router(scan_ai.router)
api_router.include_router(scan_ai.findings_router)
api_router.include_router(repositories.router)
api_router.include_router(reports.router)
api_router.include_router(repo_analysis.router)
api_router.include_router(public_scans.router)
api_router.include_router(settings.router)
api_router.include_router(unified_scan.router)
api_router.include_router(repository_results_router)
api_router.include_router(aws_router)
api_router.include_router(aws_findings_router)
api_router.include_router(cloud_router)

__all__ = ["api_router"]
