"""YAML-based rule engine for DevOps production readiness — DEPRECATED.

This engine is NOT used by any production code path.
The canonical rule engine is app.rule_engine/ (app.rule_engine.base.RuleRegistry).

The only consumer was app.services.enhanced_scan_service.EnhancedScanService,
which is itself dead code (never imported by any production module).

DO NOT add new production code that uses this engine.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from app.rule_engine.base import Category, Rule, RuleFinding, Severity

logger = structlog.get_logger(__name__)


@dataclass
class YAMLRule:
    """Rule loaded from YAML."""

    id: str
    title: str
    severity: Severity
    category: Category
    description: str
    remediation: str
    check_logic: dict[str, Any]
    file_types: list[str]
    resource_kinds: list[str] = field(default_factory=list)
    resource_types: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_rule(self) -> Rule:
        """Convert to Rule object."""
        return Rule(
            id=self.id,
            name=self.title,
            description=self.description,
            recommendation=self.remediation,
            severity=self.severity,
            category=self.category,
            tags=self.tags,
        )


class ConditionOperator:
    """Condition operators for rule evaluation."""

    @staticmethod
    def exists(value: Any) -> bool:
        return value is not None

    @staticmethod
    def not_exists(value: Any) -> bool:
        return value is None

    @staticmethod
    def equals(value: Any, expected: Any) -> bool:
        return value == expected

    @staticmethod
    def not_equals(value: Any, expected: Any) -> bool:
        return value != expected

    @staticmethod
    def contains(value: Any, expected: Any) -> bool:
        if isinstance(value, str):
            return expected in value
        if isinstance(value, list):
            return expected in value
        return False

    @staticmethod
    def not_contains(value: Any, expected: Any) -> bool:
        return not ConditionOperator.contains(value, expected)

    @staticmethod
    def in_list(value: Any, expected: list[Any]) -> bool:
        return value in expected

    @staticmethod
    def not_in(value: Any, expected: list[Any]) -> bool:
        return value not in expected

    @staticmethod
    def greater_than(value: Any, expected: Any) -> bool:
        try:
            return float(value) > float(expected)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def less_than(value: Any, expected: Any) -> bool:
        try:
            return float(value) < float(expected)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def regex(value: str, pattern: str) -> bool:
        if not isinstance(value, str):
            return False
        return bool(re.match(pattern, value))

    @staticmethod
    def contains_secret_pattern(value: Any, patterns: list[str]) -> bool:
        """Check if value contains secret patterns."""
        if isinstance(value, dict):
            for key in value.keys():
                if any(p in key.lower() for p in patterns):
                    return True
        elif isinstance(value, str):
            return any(p in value.lower() for p in patterns)
        return False

    @staticmethod
    def has_apt_without_cleanup(value: Any) -> bool:
        """Check if apt-get install without cleanup."""
        if isinstance(value, list):
            for cmd in value:
                cmd_str = str(cmd) if isinstance(cmd, dict) else str(cmd)
                if "apt-get" in cmd_str and "install" in cmd_str:
                    if "clean" not in cmd_str and "rm" not in cmd_str:
                        return True
        return False

    @staticmethod
    def no_open_ssh(value: Any) -> bool:
        """Check for open SSH security group rules."""
        if isinstance(value, list):
            for rule in value:
                if isinstance(rule, dict):
                    from_port = rule.get("from_port", 0)
                    to_port = rule.get("to_port", 0)
                    cidr = rule.get("cidr_blocks", [])
                    if from_port <= 22 <= to_port and "0.0.0.0/0" in cidr:
                        return True  # Violation found
        return False  # No violation

    @staticmethod
    def has_required_tags(value: Any, required: list[str]) -> bool:
        """Check if all required tags are present."""
        if not isinstance(value, dict):
            return True  # Can't check, assume OK
        for tag in required:
            if tag not in value:
                return False  # Missing required tag
        return True


class YAMLRuleEngine:
    """Rule engine that evaluates YAML-defined rules."""

    def __init__(self, rules_dir: str | None = None):
        self.rules: dict[str, YAMLRule] = {}
        self.rules_by_file_type: dict[str, list[YAMLRule]] = {}
        self.rules_by_category: dict[str, list[YAMLRule]] = {}
        self.operators = ConditionOperator()

        if rules_dir:
            self.load_rules(rules_dir)

    def load_rules(self, rules_dir: str) -> int:
        """Load rules from YAML files."""
        rules_path = Path(rules_dir)
        loaded_count = 0

        if not rules_path.exists():
            logger.warning("Rules directory not found", path=rules_dir)
            return 0

        for yaml_file in rules_path.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                for rule_data in data.get("rules", []):
                    rule = self._parse_rule(rule_data)
                    if rule:
                        self.rules[rule.id] = rule
                        loaded_count += 1

                        # Index by file type
                        for file_type in rule.file_types:
                            if file_type not in self.rules_by_file_type:
                                self.rules_by_file_type[file_type] = []
                            self.rules_by_file_type[file_type].append(rule)

                        # Index by category
                        category = rule.category.value
                        if category not in self.rules_by_category:
                            self.rules_by_category[category] = []
                        self.rules_by_category[category].append(rule)

                logger.info("Loaded rules from file", file=str(yaml_file), count=loaded_count)

            except Exception as e:
                logger.error("Failed to load rules file", file=str(yaml_file), error=str(e))

        logger.info("Rule engine initialized", total_rules=len(self.rules))
        return loaded_count

    def _parse_rule(self, rule_data: dict[str, Any]) -> YAMLRule | None:
        """Parse rule from dictionary."""
        try:
            return YAMLRule(
                id=rule_data["id"],
                title=rule_data["title"],
                severity=Severity(rule_data["severity"]),
                category=Category(rule_data["category"]),
                description=rule_data["description"],
                remediation=rule_data["remediation"],
                check_logic=rule_data["check_logic"],
                file_types=rule_data.get("file_types", []),
                resource_kinds=rule_data.get("resource_kinds", []),
                resource_types=rule_data.get("resource_types", []),
                tags=rule_data.get("tags", []),
            )
        except KeyError as e:
            logger.error("Rule missing required field", rule_id=rule_data.get("id"), field=str(e))
            return None
        except ValueError as e:
            logger.error("Rule has invalid value", rule_id=rule_data.get("id"), error=str(e))
            return None

    def evaluate(
        self,
        resources: list[dict[str, Any]],
        file_path: str,
        file_type: str | None = None,
    ) -> list[RuleFinding]:
        """
        Evaluate rules against resources.

        Args:
            resources: List of parsed resources
            file_path: Path to the file
            file_type: Type of file (dockerfile, kubernetes, terraform, cicd)

        Returns:
            List of findings
        """
        findings = []

        # Get rules for this file type
        applicable_rules = []
        if file_type:
            applicable_rules = self.rules_by_file_type.get(file_type, [])
        else:
            applicable_rules = list(self.rules.values())

        for rule in applicable_rules:
            rule_findings = self._evaluate_rule(rule, resources, file_path)
            findings.extend(rule_findings)

        return findings

    def _evaluate_rule(
        self,
        rule: YAMLRule,
        resources: list[dict[str, Any]],
        file_path: str,
    ) -> list[RuleFinding]:
        """Evaluate a single rule against resources."""
        findings = []

        for resource in resources:
            # Check resource kind filter
            if rule.resource_kinds:
                resource_kind = resource.get("kind")
                if resource_kind and resource_kind not in rule.resource_kinds:
                    continue

            # Check resource type filter (for Terraform)
            if rule.resource_types:
                resource_type = resource.get("type")
                if resource_type and resource_type not in rule.resource_types:
                    continue

            # Evaluate check logic
            if self._check_violation(rule.check_logic, resource):
                findings.append(
                    RuleFinding(
                        rule_id=rule.id,
                        rule_name=rule.title,
                        severity=rule.severity,
                        category=rule.category,
                        description=rule.description,
                        recommendation=rule.remediation,
                        file_path=file_path,
                        confidence=1.0,
                    )
                )

        return findings

    def _check_violation(self, check_logic: dict[str, Any], resource: dict[str, Any]) -> bool:
        """
        Check if resource violates the rule.

        Returns True if VIOLATION is found.
        """
        field_path = check_logic.get("field", "")
        operator_name = check_logic.get("operator", "exists")
        expected_value = check_logic.get("value")

        # Extract field value
        value = self._extract_field(resource, field_path)

        # Get operator function
        operator_func = getattr(self.operators, operator_name, None)
        if not operator_func:
            logger.warning("Unknown operator", operator=operator_name)
            return False

        # Execute operator
        try:
            if expected_value is not None:
                result = operator_func(value, expected_value)
            else:
                result = operator_func(value)

            # For security checks, True means violation found
            # For existence checks, False means violation (field should exist)
            if operator_name in ["exists", "has_required_tags"]:
                return not result  # Violation if field doesn't exist
            elif operator_name in ["not_exists", "not_equals", "not_contains", "no_open_ssh"]:
                return result  # Violation if condition is true
            else:
                return result  # Default: True means violation

        except Exception as e:
            logger.warning(
                "Operator execution failed",
                operator=operator_name,
                field=field_path,
                error=str(e),
            )
            return False

    def _extract_field(self, resource: dict[str, Any], field_path: str) -> Any:
        """
        Extract value from resource using field path.

        Supports:
        - Simple field: "user"
        - Nested: "spec.template.spec.containers"
        - Array access: "containers[]"
        - Combined: "spec.template.spec.containers[].resources.limits"
        """
        if not field_path:
            return resource

        parts = field_path.split(".")
        value = resource

        for part in parts:
            if value is None:
                return None

            # Handle array notation: containers[]
            if "[]" in part:
                array_field = part.replace("[]", "")
                array_value = value.get(array_field, []) if isinstance(value, dict) else value

                if isinstance(array_value, list):
                    # Return list of extracted values
                    remaining_path = field_path.split("[]", 1)[1].lstrip(".") if "[]" in field_path else ""
                    if remaining_path:
                        results = []
                        for item in array_value:
                            if isinstance(item, dict):
                                results.append(self._extract_field(item, remaining_path))
                        return results
                    return array_value
                return None

            # Simple field access
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def get_rule(self, rule_id: str) -> YAMLRule | None:
        """Get rule by ID."""
        return self.rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> list[YAMLRule]:
        """Get rules by category."""
        return self.rules_by_category.get(category, [])

    def get_rule_count(self) -> dict[str, int]:
        """Get rule counts."""
        return {
            "total": len(self.rules),
            "by_file_type": {k: len(v) for k, v in self.rules_by_file_type.items()},
            "by_category": {k: len(v) for k, v in self.rules_by_category.items()},
        }
