"""
Finding Validator Service.

Validates findings before database insertion to ensure data integrity.
- Ensures NO NULL fields (summary, risk, impact, fix_code)
- Applies static fallback if AI failed to generate fields
- Logs validation failures for observability
- Returns validated findings ready for persistence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.rule_engine.base import RuleFinding, Severity

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Static fallback templates used when AI enrichment fails to produce content
# ---------------------------------------------------------------------------

_STATIC_FALLBACKS: dict[str, dict[str, str]] = {
    # -- Generic fallbacks keyed by severity --
    "_generic": {
        "summary": "Security issue detected that requires attention.",
        "risk": "This issue may expose the system to security vulnerabilities or operational risks.",
        "impact": "If left unaddressed, this issue could lead to security breaches, data loss, or service disruption.",
        "fix_code": "# Review the flagged code and apply security best practices.\n# Refer to the recommendation for guidance.",
    },
    # -- Severity-specific fallbacks --
    "critical": {
        "summary": "Critical security vulnerability detected requiring immediate remediation.",
        "risk": "This critical vulnerability could allow an attacker to gain unauthorized access, exfiltrate sensitive data, or cause complete service disruption. Immediate action is required.",
        "impact": "Exploitation of this vulnerability could result in full system compromise, data breach, regulatory non-compliance, and significant financial and reputational damage.",
        "fix_code": "# CRITICAL: Apply this fix immediately.\n# Review the recommendation and implement the secure configuration.\n# Test thoroughly before deploying to production.",
    },
    "high": {
        "summary": "High-severity security issue that should be addressed promptly.",
        "risk": "This high-severity issue could be exploited by an attacker to compromise security controls, access sensitive data, or disrupt services.",
        "impact": "If exploited, this issue could lead to unauthorized access, data exposure, or service degradation affecting users and business operations.",
        "fix_code": "# HIGH priority: Address this issue in the current sprint.\n# Apply the recommended secure configuration.\n# Verify the fix with security testing.",
    },
    "medium": {
        "summary": "Medium-severity security finding that should be reviewed and addressed.",
        "risk": "This issue represents a moderate security risk that could be leveraged as part of a broader attack chain or under specific conditions.",
        "impact": "While not immediately critical, this issue could contribute to security weaknesses that may be exploited over time or in combination with other vulnerabilities.",
        "fix_code": "# MEDIUM priority: Schedule remediation in the next release cycle.\n# Apply the recommended configuration change.\n# Document any exceptions with risk acceptance.",
    },
    "low": {
        "summary": "Low-severity security observation for awareness and improvement.",
        "risk": "This low-severity issue presents a minor security concern that has limited exploitability but should be addressed as part of defense-in-depth.",
        "impact": "The impact of this issue is limited in scope but addressing it contributes to overall security posture and best practices compliance.",
        "fix_code": "# LOW priority: Address when convenient as part of routine maintenance.\n# Apply the recommended improvement.\n# Consider bundling with other related changes.",
    },
    "info": {
        "summary": "Informational security note for awareness.",
        "risk": "This is an informational finding intended to raise awareness about security best practices.",
        "impact": "No immediate impact, but following this recommendation will improve overall security posture.",
        "fix_code": "# Informational: Review and consider applying this best practice.\n# No immediate action required.",
    },
}

# -- Rule-specific fallbacks for known rule IDs --
_RULE_FALLBACKS: dict[str, dict[str, str]] = {
    "TF-STATE-001": {
        "summary": "Terraform state is stored locally without remote backend configuration.",
        "risk": "Terraform state stored locally cannot be shared across team members or CI/CD pipelines, leading to state drift, failed applies, and potential infrastructure corruption.",
        "impact": "Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift and deployment failures.",
        "fix_code": 'terraform {\n  backend "s3" {\n    bucket         = "tf-state-prod"\n    key            = "terraform.tfstate"\n    region         = "us-east-1"\n    dynamodb_table = "terraform-lock"\n    encrypt        = true\n  }\n}',
    },
    "TF-STATE-002": {
        "summary": "Terraform is using local state storage instead of remote backend.",
        "risk": "Without remote backend, Terraform state is stored locally, preventing team collaboration and risking state loss if the local file is deleted.",
        "impact": "Team members cannot collaborate on infrastructure changes. State loss results in inability to manage existing resources.",
        "fix_code": 'terraform {\n  backend "s3" {\n    bucket         = "my-terraform-state-bucket"\n    key            = "project/terraform.tfstate"\n    region         = "us-east-1"\n    dynamodb_table = "terraform-state-lock"\n  }\n}',
    },
    "K8S-SEC-001": {
        "summary": "Kubernetes pod is running as root user.",
        "risk": "Running containers as root increases the attack surface. If an attacker escapes the container, they have root privileges on the host.",
        "impact": "Container breakout with root access could lead to full cluster compromise, lateral movement, and data exfiltration.",
        "fix_code": "securityContext:\n  runAsNonRoot: true\n  runAsUser: 1000\n  runAsGroup: 3000\n  fsGroup: 2000",
    },
    "K8S-SEC-002": {
        "summary": "Kubernetes container has privileged security context.",
        "risk": "Privileged containers have full access to the host, bypassing all container isolation. This is equivalent to running processes directly on the host.",
        "impact": "A compromised privileged container gives the attacker complete control over the host node and potentially the entire cluster.",
        "fix_code": "securityContext:\n  privileged: false\n  allowPrivilegeEscalation: false\n  capabilities:\n    drop:\n      - ALL",
    },
    "DOCKER-SEC-001": {
        "summary": "Docker container is running as root user.",
        "risk": "Running Docker containers as root increases the risk of container escape and host compromise.",
        "impact": "An attacker who compromises a root container may escape to the host with elevated privileges.",
        "fix_code": "USER 1000:1000",
    },
    "AWS-S3-001": {
        "summary": "S3 bucket has public read access enabled.",
        "risk": "Public S3 buckets expose data to the internet, potentially leaking sensitive information and incurring unexpected data transfer costs.",
        "impact": "Data breach, compliance violations, and unexpected AWS charges from public data access.",
        "fix_code": 'resource "aws_s3_bucket_public_access_block" "example" {\n  bucket = aws_s3_bucket.example.id\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n}',
    },
}


# ---------------------------------------------------------------------------
# Validation result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of validating a single finding."""

    finding: RuleFinding
    is_valid: bool
    fields_validated: list[str] = field(default_factory=list)
    fields_fallback_applied: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "rule_id": self.finding.rule_id,
            "is_valid": self.is_valid,
            "fields_validated": self.fields_validated,
            "fields_fallback_applied": self.fields_fallback_applied,
            "validation_errors": self.validation_errors,
        }


@dataclass
class BatchValidationStats:
    """Aggregate statistics for a batch validation run."""

    total_findings: int = 0
    valid_findings: int = 0
    findings_with_fallbacks: int = 0
    total_fallbacks_applied: int = 0
    validation_errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_findings": self.total_findings,
            "valid_findings": self.valid_findings,
            "findings_with_fallbacks": self.findings_with_fallbacks,
            "total_fallbacks_applied": self.total_fallbacks_applied,
            "validation_errors": self.validation_errors,
            "fallback_rate_pct": round(
                self.findings_with_fallbacks / max(self.total_findings, 1) * 100, 1
            ),
        }


# ---------------------------------------------------------------------------
# Validator service
# ---------------------------------------------------------------------------

class FindingValidator:
    """
    Validates findings before database insertion.

    Ensures that all required fields are populated.  When AI enrichment
    fails to generate a field, a static fallback is applied based on the
    rule_id or severity level.
    """

    # Fields that must never be NULL / None
    _REQUIRED_FIELDS: list[str] = ["summary", "risk", "impact", "fix_code"]

    def __init__(self, *, strict_mode: bool = False) -> None:
        """
        Initialise the validator.

        Args:
            strict_mode: When True, findings with validation errors are
                         excluded from the returned list instead of being
                         repaired with fallbacks.
        """
        self.strict_mode = strict_mode
        self.batch_stats = BatchValidationStats()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        finding: RuleFinding,
    ) -> ValidationResult:
        """
        Validate a single finding and apply fallbacks where needed.

        Args:
            finding: The finding to validate.

        Returns:
            A ValidationResult describing what was checked and repaired.
        """
        result = ValidationResult(
            finding=finding,
            is_valid=True,
        )

        self._hydrate_from_scanner_source(finding)

        for field_name in self._REQUIRED_FIELDS:
            current_value = getattr(finding, field_name, None)

            if current_value and str(current_value).strip():
                # Field is populated -- mark as validated
                result.fields_validated.append(field_name)
            else:
                # Field is missing / empty -- try fallback
                fallback_value = self._get_fallback(finding, field_name)

                if fallback_value:
                    setattr(finding, field_name, fallback_value)
                    result.fields_fallback_applied.append(field_name)
                    logger.info(
                        "Finding fallback applied",
                        rule_id=finding.rule_id,
                        field=field_name,
                        fallback_source=self._fallback_source(finding.rule_id),
                    )
                else:
                    # No fallback available -- record error
                    result.is_valid = False
                    result.validation_errors.append(
                        f"Field '{field_name}' is empty and no fallback available"
                    )
                    logger.warning(
                        "Finding validation failure -- no fallback",
                        rule_id=finding.rule_id,
                        field=field_name,
                    )

        return result

    def validate_batch(
        self,
        findings: list[RuleFinding],
    ) -> tuple[list[RuleFinding], BatchValidationStats]:
        """
        Validate a batch of findings, applying fallbacks where needed.

        Args:
            findings: List of findings to validate.

        Returns:
            A tuple of (validated findings list, batch validation stats).
            In strict mode, findings that cannot be repaired are excluded.
        """
        self.batch_stats = BatchValidationStats(total_findings=len(findings))
        validated: list[RuleFinding] = []

        for finding in findings:
            result = self.validate(finding)

            if result.is_valid:
                validated.append(finding)
                self.batch_stats.valid_findings += 1

                if result.fields_fallback_applied:
                    self.batch_stats.findings_with_fallbacks += 1
                    self.batch_stats.total_fallbacks_applied += len(
                        result.fields_fallback_applied
                    )
            elif not self.strict_mode:
                # Non-strict mode: include the finding even with errors
                validated.append(finding)
                self.batch_stats.valid_findings += 1
                self.batch_stats.validation_errors += len(result.validation_errors)
            else:
                # Strict mode: exclude invalid findings
                self.batch_stats.validation_errors += len(result.validation_errors)
                logger.warning(
                    "Finding excluded in strict validation mode",
                    rule_id=finding.rule_id,
                    errors=result.validation_errors,
                )

        logger.info(
            "Batch validation complete",
            total=self.batch_stats.total_findings,
            valid=self.batch_stats.valid_findings,
            fallbacks_applied=self.batch_stats.total_fallbacks_applied,
            errors=self.batch_stats.validation_errors,
        )

        return validated, self.batch_stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _hydrate_from_scanner_source(self, finding: RuleFinding) -> None:
        """Prefer scanner-native text before static severity templates."""
        description = (finding.description or "").strip()
        recommendation = (finding.recommendation or "").strip()
        guideline = ""
        refs = finding.references or []
        if refs:
            guideline = next((str(r).strip() for r in refs if r and str(r).strip()), "")

        if not (finding.summary or "").strip():
            if description:
                finding.summary = description
            elif recommendation:
                finding.summary = recommendation
            elif finding.scanner_rule_id:
                finding.summary = f"{finding.scanner_name or 'Scanner'} check {finding.scanner_rule_id}"

        if finding.severity == Severity.INFO:
            if not (finding.risk or "").strip() and description:
                finding.risk = description
            if not (finding.impact or "").strip():
                finding.impact = (
                    "Informational observation from the scanner; no immediate remediation required."
                )
            if not (finding.fix_code or "").strip():
                if guideline:
                    finding.fix_code = f"# Reference: {guideline}"
                elif recommendation:
                    finding.fix_code = f"# {recommendation}"
                else:
                    finding.fix_code = "# Review this observation when updating related configuration."

    def _get_fallback(
        self,
        finding: RuleFinding,
        field_name: str,
    ) -> str | None:
        """
        Retrieve a fallback value for a missing field.

        Lookup order:
        1. Rule-specific fallback (by rule_id)
        2. Severity-specific fallback
        3. Generic fallback

        Args:
            finding: The finding being validated.
            field_name: The name of the field needing a fallback.

        Returns:
            A fallback string value, or None if no fallback is available.
        """
        # 1. Rule-specific fallback
        rule_fallbacks = _RULE_FALLBACKS.get(finding.rule_id)
        if rule_fallbacks and field_name in rule_fallbacks:
            return rule_fallbacks[field_name]

        # 2. Severity-specific fallback (skip generic info copy when scanner text exists)
        severity = finding.severity.value if finding.severity else "medium"
        if severity == Severity.INFO.value and field_name == "summary":
            desc = (finding.description or finding.recommendation or "").strip()
            if desc:
                return desc
        severity_fallbacks = _STATIC_FALLBACKS.get(severity)
        if severity_fallbacks and field_name in severity_fallbacks:
            return severity_fallbacks[field_name]

        # 3. Generic fallback
        generic = _STATIC_FALLBACKS.get("_generic", {})
        return generic.get(field_name)

    def _fallback_source(self, rule_id: str) -> str:
        """Return a human-readable description of where the fallback came from."""
        if rule_id in _RULE_FALLBACKS:
            return f"rule-specific ({rule_id})"
        return "severity-based"


# ------------------------------------------------------------------
# Module-level convenience function
# ------------------------------------------------------------------

def validate_findings(
    findings: list[RuleFinding],
    *,
    strict_mode: bool = False,
) -> tuple[list[RuleFinding], BatchValidationStats]:
    """
    Convenience function to validate a batch of findings.

    Args:
        findings: List of findings to validate.
        strict_mode: When True, exclude findings that cannot be fully repaired.

    Returns:
        A tuple of (validated findings, batch validation stats).
    """
    validator = FindingValidator(strict_mode=strict_mode)
    return validator.validate_batch(findings)
