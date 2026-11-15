"""Authoritative scan progress steps for ScanProgressStore and polling APIs.

Derived from ``ScanLifecycleStage`` — same labels as the WebSocket / overlay UI.
Scan completion is tracked on the scan record (status=completed), not as a sixth
store step; optional AI analysis after scan uses separate events.
"""

from __future__ import annotations

from app.services.scan_lifecycle import ScanLifecycleStage

# Ordered pipeline steps persisted in ScanProgressStore.steps
PROGRESS_STORE_STAGES: tuple[ScanLifecycleStage, ...] = (
    ScanLifecycleStage.CONNECTING_REPOSITORY,
    ScanLifecycleStage.CLONING,
    ScanLifecycleStage.DETECTING_TECHNOLOGIES,
    ScanLifecycleStage.SCANNING,
    ScanLifecycleStage.ANALYZING,
)

_TERMINAL_SCAN_STATUSES = frozenset({"completed", "failed", "cancelled"})

# Lifecycle stages that map onto a store step (including clone completion)
_LIFECYCLE_TO_STORE_STAGE: dict[ScanLifecycleStage, ScanLifecycleStage] = {
    ScanLifecycleStage.CONNECTING_REPOSITORY: ScanLifecycleStage.CONNECTING_REPOSITORY,
    ScanLifecycleStage.CLONING: ScanLifecycleStage.CLONING,
    ScanLifecycleStage.CLONED: ScanLifecycleStage.CLONING,
    ScanLifecycleStage.DETECTING_TECHNOLOGIES: ScanLifecycleStage.DETECTING_TECHNOLOGIES,
    ScanLifecycleStage.SCANNING: ScanLifecycleStage.SCANNING,
    ScanLifecycleStage.ANALYZING: ScanLifecycleStage.ANALYZING,
}

# Legacy test / UI strings → store stage
_LEGACY_STEP_ALIASES: dict[str, ScanLifecycleStage] = {
    "connecting to github": ScanLifecycleStage.CONNECTING_REPOSITORY,
    "fetching repository": ScanLifecycleStage.CLONING,
    "detecting technologies": ScanLifecycleStage.DETECTING_TECHNOLOGIES,
    "running security rules": ScanLifecycleStage.SCANNING,
    "generating ai suggestions": ScanLifecycleStage.ANALYZING,
    "calculating score": ScanLifecycleStage.ANALYZING,
}


def progress_store_step_labels() -> list[str]:
    """Human-readable step names in pipeline order."""
    meta = ScanLifecycleStage.metadata()
    return [meta[stage]["label"] for stage in PROGRESS_STORE_STAGES]


def progress_store_step_index(label: str) -> int | None:
    """Return 0-based index for a canonical step label, or None."""
    labels = progress_store_step_labels()
    try:
        return labels.index(label)
    except ValueError:
        return None


def lifecycle_to_store_step_label(lifecycle: ScanLifecycleStage | None) -> str | None:
    """Map a lifecycle stage to the store step label, if any."""
    if lifecycle is None:
        return None
    store_stage = _LIFECYCLE_TO_STORE_STAGE.get(lifecycle)
    if store_stage is None:
        return None
    return ScanLifecycleStage.metadata()[store_stage]["label"]


def normalize_progress_step_name(step_name: str) -> str | None:
    """
    Resolve lifecycle ids, internal stage values, labels, or legacy names
    to a canonical store step label.
    """
    if not step_name:
        return None

    labels = progress_store_step_labels()
    if step_name in labels:
        return step_name

    lowered = step_name.strip().lower()
    if lowered in _LEGACY_STEP_ALIASES:
        return ScanLifecycleStage.metadata()[_LEGACY_STEP_ALIASES[lowered]]["label"]

    try:
        lifecycle = ScanLifecycleStage(step_name)
    except ValueError:
        lifecycle = None

    if lifecycle is not None:
        return lifecycle_to_store_step_label(lifecycle)

    for stage in PROGRESS_STORE_STAGES:
        if ScanLifecycleStage.metadata()[stage]["label"].lower() == lowered:
            return ScanLifecycleStage.metadata()[stage]["label"]

    return None


def is_terminal_scan_status(status: str) -> bool:
    return status in _TERMINAL_SCAN_STATUSES
