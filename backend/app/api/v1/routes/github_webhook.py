"""GitHub App webhook endpoint."""

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.github_app_webhook import GitHubAppWebhookHandler

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/github", tags=["GitHub App Webhooks"])


@router.post("/webhook")
async def github_app_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    GitHub App webhook endpoint.

    Receives webhook events from GitHub App installations:
    - installation.created/deleted
    - installation.suspend/unsuspend
    - installation_repositories.added/removed
    - ping (verification)
    """
    try:
        handler = GitHubAppWebhookHandler(db)
        result = await handler.handle_webhook(request)
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except HTTPException:
        raise
    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": "Invalid JSON payload"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception("GitHub App webhook processing failed")
        return JSONResponse(
            content={"error": "Webhook processing failed"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
