"""Rule engine base classes and registry."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
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
    tags: List[str] = field(default_factory=list)

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
            cls._instance._rules: Dict[str, BaseRule] = {}
            cls._instance._rules_by_category: Dict[str, List[BaseRule]] = {}
            cls._instance._rules_by_file_type: Dict[str, List[BaseRule]] = {}
        return cls._instance

    def register(self, rule_class: type[BaseRule], file_types: Optional[List[str]] = None) -> None:
        """Register a rule class."""
        try:
            rule_instance = rule_class()
            rule_id = rule_instance.rule.id

            self._rules[rule_id] = rule_instance

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

            logger.debug("Rule registered", rule_id=rule_id, category=category)
        except Exception as e:
            logger.error("Failed to register rule", rule_class=rule_class.__name__, error=str(e))

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[BaseRule]:
        """Get all rules for a category."""
        return self._rules_by_category.get(category, [])

    def get_rules_by_file_type(self, file_type: str) -> List[BaseRule]:
        """Get all rules for a file type."""
        return self._rules_by_file_type.get(file_type, [])

    def get_all_rules(self) -> List[BaseRule]:
        """Get all registered rules."""
        return list(self._rules.values())

    def evaluate_all(
        self,
        resources: List[Dict[str, Any]],
        file_path: str,
        file_type: Optional[str] = None,
    ) -> List[RuleFinding]:
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

    def count_rules(self) -> Dict[str, int]:
        """Get rule counts."""
        return {
            "total": len(self._rules),
            "by_category": {cat: len(rules) for cat, rules in self._rules_by_category.items()},
        }


# Global registry instance
registry = RuleRegistry()


def register_rule(file_types: Optional[List[str]] = None):
    """Decorator to register a rule."""

    def decorator(rule_class: type[BaseRule]) -> type[BaseRule]:
        registry.register(rule_class, file_types)
        return rule_class

    return decorator
