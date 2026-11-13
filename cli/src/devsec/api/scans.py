"""Unified scan API calls."""

from __future__ import annotations

from devsec.api.client import ApiClient
from devsec.models.scan import (
    ScanResultsResponse,
    ScanStartRequest,
    ScanStartResponse,
    ScanStateResponse,
    ScanStatusResponse,
)
from devsec.utils.errors import AuthError, ScanError, UsageError


def _require_auth(client: ApiClient) -> None:
    if not client._config.token:  # noqa: SLF001 - intentional guard
        raise AuthError(
            "Authentication required.",
            hint="Run 'devsec auth login' or set DEVSEC_API_KEY.",
        )


def start_scan(
    client: ApiClient,
    *,
    repository_url: str,
    repository_id: str | None = None,
    branch: str | None = None,
    include_ai: bool = True,
) -> ScanStartResponse:
    """Start a unified background scan."""
    _require_auth(client)
    url = repository_url.strip()
    if not url:
        raise UsageError("Repository URL cannot be empty.")
    payload = ScanStartRequest(
        repository_url=url,
        repository_id=repository_id,
        branch=branch,
        include_ai_explanations=include_ai,
    )
    body = payload.model_dump(exclude_none=True)
    data = client.post_json("/scan/start", payload=body)
    return ScanStartResponse.model_validate(data)


def get_scan_status(client: ApiClient, scan_id: str) -> ScanStatusResponse:
    """Fetch real-time scan progress."""
    _require_auth(client)
    scan_id = scan_id.strip()
    if not scan_id:
        raise UsageError("Scan ID cannot be empty.")
    data = client.get_json(f"/scan/status/{scan_id}")
    return ScanStatusResponse.model_validate(data)


def get_scan_state(client: ApiClient, scan_id: str) -> ScanStateResponse:
    """Fetch authoritative scan state (lifecycle, technologies, AI status)."""
    _require_auth(client)
    scan_id = scan_id.strip()
    if not scan_id:
        raise UsageError("Scan ID cannot be empty.")
    data = client.get_json(f"/scan/state/{scan_id}")
    return ScanStateResponse.model_validate(data)


def get_scan_results(client: ApiClient, scan_id: str) -> ScanResultsResponse:
    """Fetch completed scan results."""
    _require_auth(client)
    scan_id = scan_id.strip()
    if not scan_id:
        raise UsageError("Scan ID cannot be empty.")
    data = client.get_json(f"/scan/results/{scan_id}")
    return ScanResultsResponse.model_validate(data)


def evaluate_scan_outcome(
    results: ScanResultsResponse,
    *,
    fail_on: str = "high",
) -> tuple[bool, str | None]:
    """Return (passed, reason) based on findings severity threshold."""
    if results.status.lower() == "failed":
        return False, results.error_message or "Scan failed"

    threshold = fail_on.lower()
    if threshold in {"", "none", "off"}:
        return True, None

    failing = results.count_at_or_above(threshold)
    if failing > 0:
        return False, f"{failing} finding(s) at or above {threshold.upper()} severity"
    return True, None


def _scan_failure_hint(message: str | None) -> str:
    if not message:
        return "Check scan logs with 'devsec scan status <scan-id>'."
    lowered = message.lower()
    if "no analyzable files" in lowered:
        return (
            f"{message} "
            "Add Terraform, Kubernetes, Docker, Helm, or CI/CD files to the repository, "
            "or scan a repo that contains infrastructure code."
        )
    if "clone" in lowered or "access" in lowered:
        return f"{message} Check repository access and that the URL is correct."
    return message


def ensure_scan_completed(status: ScanStatusResponse) -> None:
    """Raise ScanError when a scan did not complete successfully."""
    normalized = status.status.lower()
    if normalized == "completed":
        return
    if normalized in {"failed", "cancelled"}:
        raise ScanError(
            f"Scan {status.scan_id} {normalized}.",
            hint=_scan_failure_hint(status.error_message),
        )
    raise ScanError(
        f"Scan {status.scan_id} is not complete (status: {status.status}).",
        hint="Wait for completion or run 'devsec scan status'.",
    )
