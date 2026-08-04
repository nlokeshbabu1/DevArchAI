from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


async def create_jira_ticket(
    jira_url: str,
    email: str,
    api_token: str,
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
) -> dict[str, Any]:
    """Create a Jira issue via the Jira REST API.

    Returns dict with keys:
      - success: bool
      - ticket_url: str | None
      - ticket_key: str | None
      - error: str | None
    """
    base_url = jira_url.rstrip("/")
    api_url = f"{base_url}/rest/api/3/issue"

    auth = httpx.BasicAuth(username=email, password=api_token)
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "text": description,
                                "type": "text",
                            }
                        ],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.JIRA_API_TIMEOUT) as client:
            resp = await client.post(api_url, json=payload, auth=auth)

        if resp.is_success:
            data = resp.json()
            ticket_key = data.get("key", "")
            ticket_url = f"{base_url}/browse/{ticket_key}"
            logger.info(
                "jira_ticket_created",
                ticket_key=ticket_key,
                project=project_key,
            )
            return {"success": True, "ticket_url": ticket_url, "ticket_key": ticket_key, "error": None}
        else:
            error_detail = resp.text[:500]
            logger.warning("jira_ticket_failed", status=resp.status_code, detail=error_detail)
            return {"success": False, "ticket_url": None, "ticket_key": None, "error": f"HTTP {resp.status_code}: {error_detail}"}

    except httpx.TimeoutException:
        logger.warning("jira_ticket_timeout", url=api_url)
        return {"success": False, "ticket_url": None, "ticket_key": None, "error": "Request timed out"}
    except Exception as exc:
        logger.warning("jira_ticket_error", error=str(exc))
        return {"success": False, "ticket_url": None, "ticket_key": None, "error": str(exc)}
