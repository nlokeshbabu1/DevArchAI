"""API v1 router aggregation."""

from fastapi import APIRouter

from devarchai.api.v1.endpoints import (
    auth,
    health,
    organizations,
    repositories,
    scans,
    findings,
    reports,
    dashboard,
    billing,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(organizations.router)
api_router.include_router(repositories.router)
api_router.include_router(scans.router)
api_router.include_router(findings.router)
api_router.include_router(reports.router)
api_router.include_router(dashboard.router)
api_router.include_router(billing.router)

__all__ = ["api_router"]
