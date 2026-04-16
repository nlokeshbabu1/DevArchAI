"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import (
    ai_suggestions,
    auth,
    billing,
    dashboard,
    findings,
    github,
    github_installations,
    github_webhook,
    health,
    public_scans,
    pull_requests,
    repo_analysis,
    reports,
    repositories,
    scans,
    unified_scan,
)

api_router = APIRouter()

api_router.include_router(ai_suggestions.router)
api_router.include_router(auth.router)
api_router.include_router(billing.router)
api_router.include_router(dashboard.router)
api_router.include_router(findings.router)
api_router.include_router(github.router)
api_router.include_router(github_installations.router)
api_router.include_router(github_webhook.router)
api_router.include_router(health.router)
api_router.include_router(pull_requests.router)
api_router.include_router(scans.router)
api_router.include_router(repositories.router)
api_router.include_router(reports.router)
api_router.include_router(repo_analysis.router)
api_router.include_router(public_scans.router)
api_router.include_router(unified_scan.router)

__all__ = ["api_router"]
