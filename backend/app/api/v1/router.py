"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import auth, billing, github, health, public_scans, repo_analysis, reports, repositories, scans

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(billing.router)
api_router.include_router(health.router)
api_router.include_router(scans.router)
api_router.include_router(repositories.router)
api_router.include_router(reports.router)
api_router.include_router(repo_analysis.router)
api_router.include_router(github.router)
api_router.include_router(public_scans.router)

__all__ = ["api_router"]
