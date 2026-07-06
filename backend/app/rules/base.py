"""
Rule Engine - Base Classes and Registry
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


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
        documentation_url: str | None = None,
        risk: str | None = None,
        impact: str | None = None,
        fix_example: str | None = None,
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
        # Documentation link
        self.documentation_url = documentation_url
        # Additional fields
        self.risk = risk
        self.impact = impact
        self.fix_example = fix_example

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
            "documentation_url": self.documentation_url,
            "risk": self.risk,
            "impact": self.impact,
            "fix_example": self.fix_example,
        }

    def __repr__(self) -> str:
        return f"RuleFinding(rule_id={self.rule_id}, severity={self.severity.value})"


class Rule:
    """Base rule definition."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        recommendation: str,
        severity: Severity,
        category: Category,
        enabled: bool = True,
        tags: list[str] | None = None,
        file_types: list[str] | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.recommendation = recommendation
        self.severity = severity
        self.category = category
        self.enabled = enabled
        self.tags = tags or []
        self.file_types = file_types or []  # File types this rule applies to

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
    """Registry for all rules with file-type based filtering."""

    _instance: Optional["RuleRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = {}
            cls._instance._rules_by_category = {}
            cls._instance._rules_by_file_type = {}
        return cls._instance

    def register(self, rule_class: type[BaseRule], file_types: list[str] | None = None) -> None:
        """
        Register a rule class.

        Args:
            rule_class: Rule class to register
            file_types: List of file types this rule applies to
        """
        rule = rule_class()
        self._rules[rule.rule.id] = rule

        # Store file types on the rule
        if file_types:
            rule.rule.file_types = file_types

        # Index by category
        category = rule.rule.category.value
        if category not in self._rules_by_category:
            self._rules_by_category[category] = []
        self._rules_by_category[category].append(rule)

        # Index by file type
        rule_file_types = file_types or self._infer_file_types_from_rule(rule_class)
        for file_type in rule_file_types:
            if file_type not in self._rules_by_file_type:
                self._rules_by_file_type[file_type] = []
            self._rules_by_file_type[file_type].append(rule)

    def _infer_file_types_from_rule(self, rule_class: type[BaseRule]) -> list[str]:
        """Infer file types from rule class module path."""
        module_path = rule_class.__module__.lower()

        if "terraform" in module_path:
            return ["terraform"]
        elif "docker" in module_path or "dockerfile" in module_path:
            return ["dockerfile", "docker_compose"]
        elif "kubernetes" in module_path or "k8s" in module_path:
            return ["kubernetes", "helm"]
        elif "cicd" in module_path or "ci_cd" in module_path:
            return ["cicd"]
        elif "security" in module_path:
            return ["terraform", "dockerfile", "kubernetes", "cicd"]
        elif "reliability" in module_path:
            return ["terraform", "kubernetes", "cicd"]
        elif "cost" in module_path:
            return ["terraform", "cicd"]
        elif "observability" in module_path:
            return ["terraform", "kubernetes", "cicd"]

        return []

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
    ) -> list[RuleFinding]:
        """
        Evaluate all rules against resources.

        Args:
            resources: List of parsed resources from file
            file_path: Path to the file being evaluated
            file_type: Type of file (terraform, dockerfile, kubernetes, cicd)

        Returns:
            List of findings
        """
        findings = []

        # Get rules for this file type
        if file_type:
            rules_to_evaluate = self.get_rules_by_file_type(file_type)
            # Also include rules with no file type restriction
            all_rules = self.get_all_rules()
            for rule in all_rules:
                if not rule.rule.file_types and rule not in rules_to_evaluate:
                    rules_to_evaluate.append(rule)
        else:
            rules_to_evaluate = self.get_all_rules()

        for rule in rules_to_evaluate:
            if rule.rule.enabled:
                try:
                    # Skip if rule has file type restrictions and this file doesn't match
                    if rule.rule.file_types:
                        if not file_type or file_type not in rule.rule.file_types:
                            continue

                    rule_findings = rule.evaluate(resources, file_path)
                    findings.extend(rule_findings)
                except Exception as e:
                    # Log error but continue with other rules
                    findings.append(RuleFinding(
                        rule_id="INTERNAL",
                        rule_name="Rule Evaluation Error",
                        severity=Severity.INFO,
                        category=Category.SECURITY,
                        description=f"Error evaluating rule {rule.rule.id}: {str(e)}",
                        recommendation="Check logs for details",
                        file_path=file_path,
                    ))

        return findings

    def count_rules(self) -> dict[str, int]:
        """Get rule counts."""
        return {
            "total": len(self._rules),
            "by_category": {cat: len(rules) for cat, rules in self._rules_by_category.items()},
            "by_file_type": {ft: len(rules) for ft, rules in self._rules_by_file_type.items()},
        }


# Global registry instance
registry = RuleRegistry()


def register_rule(file_types: list[str] | None = None):
    """
    Decorator to register a rule.

    Args:
        file_types: Optional list of file types this rule applies to.
                   If not provided, file types are inferred from module path.
    """
    def decorator(rule_class: type[BaseRule]) -> type[BaseRule]:
        registry.register(rule_class, file_types)
        return rule_class

    return decorator
