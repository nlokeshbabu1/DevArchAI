"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import auth, health, scans, repositories, reports, repo_analysis, github

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(scans.router)
api_router.include_router(repositories.router)
api_router.include_router(reports.router)
api_router.include_router(repo_analysis.router)
api_router.include_router(github.router)

__all__ = ["api_router"]
