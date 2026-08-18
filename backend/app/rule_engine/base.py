"""Rule engine base classes and registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class Severity(str, Enum):
    """Rule severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Rule categories."""

    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    COST = "cost"
    OBSERVABILITY = "observability"


class RuleFinding:
    """Represents a finding from rule evaluation."""

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        severity: Severity,
        category: Category,
        description: str,
        recommendation: str,
        file_path: str | None = None,
        line_number: int | None = None,
        resource_name: str | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
        ai_explanation: str | None = None,
        impact_analysis: str | None = None,
        # AI Fix Generator fields (production-grade)
        summary: str | None = None,
        risk: str | None = None,
        impact: str | None = None,
        fix_code: str | None = None,
        fix_example: str | None = None,
        full_example: str | None = None,
        best_practices: list[str] | None = None,
        documentation_url: str | None = None,
        ai_generated: bool = False,
        # Scanner metadata fields (for external scanner integration)
        scanner_name: str | None = None,
        scanner_rule_id: str | None = None,
        package: str | None = None,
        installed_version: str | None = None,
        fixed_version: str | None = None,
        cve: str | None = None,
        cwe: str | None = None,
        references: list[str] | None = None,
        evidence: str | None = None,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.severity = severity
        self.category = category
        self.description = description
        self.recommendation = recommendation
        self.file_path = file_path
        self.line_number = line_number
        self.resource_name = resource_name
        self.confidence = confidence
        self.metadata = metadata or {}
        # AI enhancements
        self.ai_explanation = ai_explanation
        self.impact_analysis = impact_analysis
        # AI Fix Generator fields
        self.summary = summary
        self.risk = risk
        self.impact = impact
        self.fix_code = fix_code
        self.fix_example = fix_example
        self.full_example = full_example
        self.best_practices = best_practices or []
        self.documentation_url = documentation_url
        self.ai_generated = ai_generated
        # Scanner metadata fields
        self.scanner_name = scanner_name
        self.scanner_rule_id = scanner_rule_id
        self.package = package
        self.installed_version = installed_version
        self.fixed_version = fixed_version
        self.cve = cve
        self.cwe = cwe
        self.references = references or []
        self.evidence = evidence

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "category": self.category.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "resource_name": self.resource_name,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "ai_explanation": self.ai_explanation,
            "impact_analysis": self.impact_analysis,
            # AI Fix Generator fields
            "summary": self.summary,
            "risk": self.risk,
            "impact": self.impact,
            "fix_code": self.fix_code,
            "fix_example": self.fix_example,
            "full_example": self.full_example,
            "best_practices": self.best_practices,
            "documentation_url": self.documentation_url,
            "ai_generated": self.ai_generated,
            # Scanner metadata fields
            "scanner_name": self.scanner_name,
            "scanner_rule_id": self.scanner_rule_id,
            "package": self.package,
            "installed_version": self.installed_version,
            "fixed_version": self.fixed_version,
            "cve": self.cve,
            "cwe": self.cwe,
            "references": self.references,
            "evidence": self.evidence,
        }

    def __repr__(self) -> str:
        return f"RuleFinding(rule_id={self.rule_id}, severity={self.severity.value})"


@dataclass
class Rule:
    """Base rule definition."""

    id: str
    name: str
    description: str
    recommendation: str
    severity: Severity
    category: Category
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    file_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "recommendation": self.recommendation,
            "severity": self.severity.value,
            "category": self.category.value,
            "enabled": self.enabled,
            "tags": self.tags,
            "file_types": self.file_types,
        }


class BaseRule(ABC):
    """Abstract base class for all rules."""

    @property
    @abstractmethod
    def rule(self) -> Rule:
        """Return the rule definition."""
        pass

    @abstractmethod
    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        """
        Evaluate the rule against parsed resources.

        Args:
            resources: List of parsed resources from file
            file_path: Path to the file being evaluated

        Returns:
            List of findings (empty if rule passes)
        """
        pass


class RuleRegistry:
    """Registry for all rules."""

    _instance: Optional["RuleRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules: dict[str, BaseRule] = {}
            cls._instance._rules_by_category: dict[str, list[BaseRule]] = {}
            cls._instance._rules_by_file_type: dict[str, list[BaseRule]] = {}
        return cls._instance

    def register(self, rule_class: type[BaseRule], file_types: list[str] | None = None) -> None:
        """Register a rule class."""
        try:
            rule_instance = rule_class()
            rule_id = rule_instance.rule.id

            self._rules[rule_id] = rule_instance

            # Store file_types on the rule instance
            if file_types:
                rule_instance.rule.file_types = file_types

            # Index by category
            category = rule_instance.rule.category.value
            if category not in self._rules_by_category:
                self._rules_by_category[category] = []
            self._rules_by_category[category].append(rule_instance)

            # Index by file type if specified
            if file_types:
                for file_type in file_types:
                    if file_type not in self._rules_by_file_type:
                        self._rules_by_file_type[file_type] = []
                    self._rules_by_file_type[file_type].append(rule_instance)

            logger.debug("Rule registered", rule_id=rule_id, category=category, file_types=file_types)
        except Exception as e:
            logger.error("Failed to register rule", rule_class=rule_class.__name__, error=str(e))

    def get_rule(self, rule_id: str) -> BaseRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> list[BaseRule]:
        """Get all rules for a category."""
        return self._rules_by_category.get(category, [])

    def get_rules_by_file_type(self, file_type: str) -> list[BaseRule]:
        """Get all rules for a file type."""
        return self._rules_by_file_type.get(file_type, [])

    def get_all_rules(self) -> list[BaseRule]:
        """Get all registered rules."""
        return list(self._rules.values())

    def evaluate_all(
        self,
        resources: list[dict[str, Any]],
        file_path: str,
        file_type: str | None = None,
        has_terraform: bool = False,
    ) -> list[RuleFinding]:
        """Evaluate all rules against resources."""
        findings = []

        # Get rules to evaluate
        rules_to_evaluate = self.get_all_rules()
        if file_type:
            # Filter rules by file type if available
            type_specific_rules = self.get_rules_by_file_type(file_type)
            if type_specific_rules:
                rules_to_evaluate = type_specific_rules

        for rule in rules_to_evaluate:
            if rule.rule.enabled:
                try:
                    # Pass has_terraform parameter for rules that support it
                    # (Terraform CI/CD rules need this to skip when no .tf files exist)
                    import inspect
                    sig = inspect.signature(rule.evaluate)
                    params = list(sig.parameters.keys())

                    if 'has_terraform' in params:
                        rule_findings = rule.evaluate(resources, file_path, has_terraform)
                    else:
                        rule_findings = rule.evaluate(resources, file_path)

                    findings.extend(rule_findings)
                except Exception as e:
                    logger.error(
                        "Rule evaluation failed",
                        rule_id=rule.rule.id,
                        file_path=file_path,
                        error=str(e),
                    )

        return findings

    def count_rules(self) -> dict[str, int]:
        """Get rule counts."""
        return {
            "total": len(self._rules),
            "by_category": {cat: len(rules) for cat, rules in self._rules_by_category.items()},
        }


# Global registry instance
registry = RuleRegistry()


def register_rule(file_types: list[str] | None = None):
    """Decorator to register a rule."""

    def decorator(rule_class: type[BaseRule]) -> type[BaseRule]:
        registry.register(rule_class, file_types)
        return rule_class

    return decorator
