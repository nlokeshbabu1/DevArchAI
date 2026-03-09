"""
Rule Engine - Base Classes and Registry
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


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
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        resource_name: Optional[str] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        ai_explanation: Optional[str] = None,
        impact_analysis: Optional[str] = None,
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

    def to_dict(self) -> Dict[str, Any]:
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
        tags: Optional[List[str]] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.recommendation = recommendation
        self.severity = severity
        self.category = category
        self.enabled = enabled
        self.tags = tags or []

    def to_dict(self) -> Dict[str, Any]:
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
        }


class BaseRule(ABC):
    """Abstract base class for all rules."""

    @property
    @abstractmethod
    def rule(self) -> Rule:
        """Return the rule definition."""
        pass

    @abstractmethod
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
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
            cls._instance._rules = {}
            cls._instance._rules_by_category = {}
        return cls._instance

    def register(self, rule_class: type[BaseRule]) -> None:
        """Register a rule class."""
        rule = rule_class()
        self._rules[rule.rule.id] = rule

        # Index by category
        category = rule.rule.category.value
        if category not in self._rules_by_category:
            self._rules_by_category[category] = []
        self._rules_by_category[category].append(rule)

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[BaseRule]:
        """Get all rules for a category."""
        return self._rules_by_category.get(category, [])

    def get_all_rules(self) -> List[BaseRule]:
        """Get all registered rules."""
        return list(self._rules.values())

    def evaluate_all(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        """Evaluate all rules against resources."""
        findings = []

        for rule in self._rules.values():
            if rule.rule.enabled:
                try:
                    rule_findings = rule.evaluate(resources, file_path)
                    findings.extend(rule_findings)
                except Exception as e:
                    # Log error but continue with other rules
                    findings.append(RuleFinding(
                        rule_id="INTERNAL",
                        rule_name="Rule Evaluation Error",
                        severity=Severity.INFO,
                        category=Category.SECURITY,
                        description=f"Error evaluating rule: {str(e)}",
                        recommendation="Check logs for details",
                        file_path=file_path,
                    ))

        return findings


# Global registry instance
registry = RuleRegistry()


def register_rule(rule_class: type[BaseRule]) -> type[BaseRule]:
    """Decorator to register a rule."""
    registry.register(rule_class)
    return rule_class
