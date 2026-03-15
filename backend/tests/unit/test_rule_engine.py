"""Unit tests for the rule engine."""

from pathlib import Path

import pytest

from app.engines.rule_engine import ConditionOperator, YAMLRuleEngine
from app.rule_engine.base import Category, Severity


class TestConditionOperator:
    """Test condition operators."""

    def test_exists(self):
        assert ConditionOperator.exists("value") is True
        assert ConditionOperator.exists(None) is False
        assert ConditionOperator.exists("") is True
        assert ConditionOperator.exists(0) is True

    def test_not_exists(self):
        assert ConditionOperator.not_exists(None) is True
        assert ConditionOperator.not_exists("value") is False

    def test_equals(self):
        assert ConditionOperator.equals("test", "test") is True
        assert ConditionOperator.equals("test", "other") is False
        assert ConditionOperator.equals(1, 1) is True
        assert ConditionOperator.equals(1, 2) is False

    def test_not_equals(self):
        assert ConditionOperator.not_equals("test", "other") is True
        assert ConditionOperator.not_equals("test", "test") is False

    def test_contains(self):
        assert ConditionOperator.contains("hello world", "world") is True
        assert ConditionOperator.contains("hello world", "foo") is False
        assert ConditionOperator.contains(["a", "b", "c"], "b") is True

    def test_not_in(self):
        assert ConditionOperator.not_in("foo", ["bar", "baz"]) is True
        assert ConditionOperator.not_in("foo", ["foo", "bar"]) is False

    def test_greater_than(self):
        assert ConditionOperator.greater_than(10, 5) is True
        assert ConditionOperator.greater_than(5, 10) is False

    def test_less_than(self):
        assert ConditionOperator.less_than(5, 10) is True
        assert ConditionOperator.less_than(10, 5) is False

    def test_contains_secret_pattern(self):
        assert ConditionOperator.contains_secret_pattern(
            {"password": "secret"},
            ["password", "secret"]
        ) is True
        assert ConditionOperator.contains_secret_pattern(
            {"name": "test"},
            ["password", "secret"]
        ) is False


class TestYAMLRuleEngine:
    """Test YAML rule engine."""

    @pytest.fixture
    def rule_engine(self):
        """Create rule engine with test rules."""
        rules_dir = str(Path(__file__).parent.parent.parent / "app" / "rules" / "yaml")
        return YAMLRuleEngine(rules_dir=rules_dir)

    def test_load_rules(self, rule_engine):
        """Test loading rules from YAML files."""
        rule_count = rule_engine.get_rule_count()
        assert rule_count["total"] > 0
        assert "dockerfile" in rule_count["by_file_type"]
        assert "kubernetes" in rule_count["by_file_type"]
        assert "terraform" in rule_count["by_file_type"]

    def test_get_rule(self, rule_engine):
        """Test getting rule by ID."""
        rule = rule_engine.get_rule("DOCKER-001")
        assert rule is not None
        assert rule.id == "DOCKER-001"
        assert rule.severity == Severity.HIGH
        assert rule.category == Category.SECURITY

    def test_get_rules_by_category(self, rule_engine):
        """Test getting rules by category."""
        security_rules = rule_engine.get_rules_by_category("security")
        assert len(security_rules) > 0

    def test_evaluate_docker_root_rule(self, rule_engine):
        """Test Docker root user rule evaluation."""
        # Resource without user (should violate)
        resources = [{"file_type": "dockerfile"}]
        findings = rule_engine.evaluate(resources, "Dockerfile", "dockerfile")

        # Should find DOCKER-001 violation
        root_findings = [f for f in findings if f.rule_id == "DOCKER-001"]
        assert len(root_findings) > 0

    def test_evaluate_docker_with_user(self, rule_engine):
        """Test Docker rule with non-root user (should pass)."""
        resources = [{
            "file_type": "dockerfile",
            "user": "appuser"
        }]
        findings = rule_engine.evaluate(resources, "Dockerfile", "dockerfile")

        # Should not find DOCKER-001 violation
        root_findings = [f for f in findings if f.rule_id == "DOCKER-001"]
        assert len(root_findings) == 0

    def test_evaluate_docker_latest_tag(self, rule_engine):
        """Test Docker latest tag rule."""
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "is_latest": True,
                "full": "node:latest"
            }
        }]
        findings = rule_engine.evaluate(resources, "Dockerfile", "dockerfile")

        latest_findings = [f for f in findings if f.rule_id == "DOCKER-003"]
        assert len(latest_findings) > 0

    def test_extract_field_nested(self, rule_engine):
        """Test extracting nested field values."""
        resource = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "app", "image": "nginx"},
                            {"name": "sidecar", "image": "busybox"}
                        ]
                    }
                }
            }
        }

        # Extract containers
        containers = rule_engine._extract_field(
            resource,
            "spec.template.spec.containers[]"
        )
        assert len(containers) == 2
        assert containers[0]["name"] == "app"

    def test_finding_structure(self, rule_engine):
        """Test that findings have correct structure."""
        resources = [{"file_type": "dockerfile"}]
        findings = rule_engine.evaluate(resources, "Dockerfile", "dockerfile")

        if findings:
            finding = findings[0]
            assert finding.rule_id is not None
            assert finding.rule_name is not None
            assert finding.severity is not None
            assert finding.category is not None
            assert finding.description is not None
            assert finding.recommendation is not None
