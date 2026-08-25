"""Scan lifecycle stages for UI and WebSocket events.

Maps internal ``ScanStage`` values to user-facing lifecycle steps. Progress is
derived from completed lifecycle steps (and optional scanner sub-progress), not
hardcoded milestone percentages.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from app.models.scan import ScanStage


class ScanLifecycleStage(str, Enum):
    """User-facing scan lifecycle steps shown in the progress UI."""

    QUEUED = "queued"
    CONNECTING_REPOSITORY = "connecting_repository"
    CLONING = "cloning"
    CLONED = "cloned"
    SCANNING = "scanning"
    DETECTING_TECHNOLOGIES = "detecting_technologies"
    ANALYZING = "analyzing"
    SCAN_COMPLETED = "scan_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def metadata(cls) -> dict["ScanLifecycleStage", dict[str, Any]]:
        return {
            cls.QUEUED: {"label": "Queued", "icon": "clock", "order": 0, "kind": "base"},
            cls.CONNECTING_REPOSITORY: {
                "label": "Connect to repository",
                "icon": "git-branch",
                "order": 1,
                "kind": "base",
            },
            cls.CLONING: {"label": "Clone repository", "icon": "download", "order": 2, "kind": "base"},
            cls.CLONED: {"label": "Repository cloned", "icon": "check-circle", "order": 3, "kind": "base"},
            cls.DETECTING_TECHNOLOGIES: {
                "label": "Detect technologies",
                "icon": "search",
                "order": 4,
                "kind": "base",
            },
            cls.SCANNING: {"label": "Security scan", "icon": "shield", "order": 5, "kind": "base"},
            cls.ANALYZING: {"label": "Analyze findings", "icon": "filter", "order": 97, "kind": "base"},
            cls.SCAN_COMPLETED: {"label": "Scan complete", "icon": "check-circle", "order": 99, "kind": "base"},
            cls.FAILED: {"label": "Scan failed", "icon": "x-circle", "order": 100, "kind": "base"},
            cls.CANCELLED: {"label": "Scan cancelled", "icon": "x-circle", "order": 101, "kind": "base"},
        }

    @classmethod
    def ordered(cls) -> list["ScanLifecycleStage"]:
        return sorted(cls.metadata().keys(), key=lambda s: cls.metadata()[s]["order"])


# Internal stage → lifecycle step
_INTERNAL_TO_LIFECYCLE: dict[ScanStage, ScanLifecycleStage] = {
    ScanStage.CONNECTING: ScanLifecycleStage.CONNECTING_REPOSITORY,
    ScanStage.CLONING: ScanLifecycleStage.CLONING,
    ScanStage.TECHNOLOGY_DETECTION: ScanLifecycleStage.DETECTING_TECHNOLOGIES,
    ScanStage.SCANNER_SELECTION: ScanLifecycleStage.SCANNING,
    ScanStage.SCANNING: ScanLifecycleStage.SCANNING,
    ScanStage.NORMALIZATION: ScanLifecycleStage.ANALYZING,
    ScanStage.DEDUPLICATION: ScanLifecycleStage.ANALYZING,
    ScanStage.REPORT_GENERATION: ScanLifecycleStage.ANALYZING,
}

_BASE_STAGES = [
    ScanLifecycleStage.QUEUED,
    ScanLifecycleStage.CONNECTING_REPOSITORY,
    ScanLifecycleStage.CLONING,
    ScanLifecycleStage.CLONED,
    ScanLifecycleStage.DETECTING_TECHNOLOGIES,
    ScanLifecycleStage.SCANNING,
]

# Valid forward transitions for lifecycle steps (failure/cancel handled separately)
_LIFECYCLE_ORDER = ScanLifecycleStage.ordered()


def lifecycle_stage_for_internal(stage: ScanStage | None) -> ScanLifecycleStage | None:
    if stage is None:
        return None
    return _INTERNAL_TO_LIFECYCLE.get(stage)


def lifecycle_progress(
    lifecycle_stage: ScanLifecycleStage,
    *,
    scanners_completed: int = 0,
    scanners_total: int = 0,
) -> int | None:
    """Compute progress from lifecycle position. Returns None when not meaningful."""
    if lifecycle_stage in (ScanLifecycleStage.CLONING, ScanLifecycleStage.QUEUED):
        return None

    steps = _BASE_STAGES + [ScanLifecycleStage.ANALYZING, ScanLifecycleStage.SCAN_COMPLETED]
    try:
        idx = steps.index(lifecycle_stage)
    except ValueError:
        return None

    if scanners_total > 0 and lifecycle_stage == ScanLifecycleStage.SCANNING:
        step_base = idx / len(steps)
        step_width = 1 / len(steps)
        sub = min(1.0, scanners_completed / scanners_total)
        return min(99, int((step_base + sub * step_width) * 100))

    return min(99, int(((idx + 0.5) / len(steps)) * 100))


def technology_stage_metadata(tech_id: str, *, order_offset: int = 0) -> dict[str, Any]:
    return {
        "id": f"tech:{tech_id}",
        "label": format_technology_label(tech_id),
        "icon": tech_id.replace("_", "-"),
        "order": 50 + order_offset,
        "kind": "technology",
        "technology_id": tech_id,
    }


def lifecycle_stages_payload() -> list[dict[str, Any]]:
    """Base lifecycle stages only — technologies are inserted dynamically."""
    payload = []
    for stage in _BASE_STAGES + [ScanLifecycleStage.ANALYZING, ScanLifecycleStage.SCAN_COMPLETED]:
        meta = ScanLifecycleStage.metadata()[stage]
        payload.append(
            {
                "id": stage.value,
                "label": meta["label"],
                "icon": meta["icon"],
                "order": meta["order"],
                "kind": meta.get("kind", "base"),
            }
        )
    return payload


def format_technology_label(tech: str) -> str:
    """Human-readable technology name for events."""
    labels = {
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "helm": "Helm",
        "terraform": "Terraform",
        "github_actions": "GitHub Actions",
        "gitlab_ci": "GitLab CI",
        "jenkins": "Jenkins",
        "circleci": "CircleCI",
        "azure_devops": "Azure DevOps",
        "ansible": "Ansible",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "docker_compose": "Docker Compose",
    }
    return labels.get(tech, tech.replace("_", " ").title())
