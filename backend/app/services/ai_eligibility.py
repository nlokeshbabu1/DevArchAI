"""Central policy: which normalized findings may receive LLM recommendation jobs."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.models.finding import Finding
from app.rule_engine.base import RuleFinding, Severity


def finding_severity_value(finding: Any) -> str:
    return _normalize_severity(getattr(finding, "severity", None))


def _normalize_severity(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Severity):
        return value.value.lower()
    if hasattr(value, "value"):
        return str(value.value).lower().strip()
    raw = str(value).lower().strip()
    if raw.startswith("severity."):
        return raw.split(".", 1)[-1]
    return raw


def include_low_severity_in_ai() -> bool:
    return bool(getattr(settings, "AI_ELIGIBILITY_INCLUDE_LOW", False))


def is_ai_eligible_finding(
    finding: RuleFinding | Finding | Any,
    *,
    include_low: bool | None = None,
) -> bool:
    """Return True when a finding should enter the AI recommendation pipeline."""
    severity = _normalize_severity(getattr(finding, "severity", None))
    if not severity:
        return True
    if severity == Severity.INFO.value:
        return False
    if severity == Severity.LOW.value:
        allow_low = include_low if include_low is not None else include_low_severity_in_ai()
        return allow_low
    return severity in {
        Severity.CRITICAL.value,
        Severity.HIGH.value,
        Severity.MEDIUM.value,
    }


def ai_eligibility_reason(finding: RuleFinding | Finding | Any) -> str | None:
    """Human-readable skip reason when not eligible (for metrics/UI)."""
    if is_ai_eligible_finding(finding):
        return None
    severity = _normalize_severity(getattr(finding, "severity", None))
    if severity == Severity.INFO.value:
        return "info_excluded"
    if severity == Severity.LOW.value:
        return "low_excluded_by_policy"
    return "ineligible"


def filter_ai_eligible_findings(
    findings: list[Any],
    *,
    include_low: bool | None = None,
) -> list[Any]:
    return [f for f in findings if is_ai_eligible_finding(f, include_low=include_low)]