"""Unit tests for the scoring engine."""

import pytest

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scoring.engine import ScoringEngine, ScoringWeights


class TestScoringEngine:
    """Test scoring engine calculations."""

    @pytest.fixture
    def scoring_engine(self):
        """Create scoring engine instance."""
        return ScoringEngine()

    def test_perfect_score(self, scoring_engine):
        """Test perfect score with no findings."""
        result = scoring_engine.calculate_scores([])

        assert result.score == 100.0
        assert result.grade == "A"
        assert result.total_findings == 0
        assert result.critical_findings == 0

    def test_single_critical_finding(self, scoring_engine):
        """Test score deduction for single critical finding."""
        findings = [
            RuleFinding(
                rule_id="TEST-001",
                rule_name="Test Rule",
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                description="Test finding",
                recommendation="Fix it",
            )
        ]

        result = scoring_engine.calculate_scores(findings)

        # Critical finding should deduct 20 points from security category
        # Security is 35% weight, so overall deduction is 20 * 0.35 = 7 points
        assert result.score < 100.0
        assert result.critical_findings == 1

    def test_multiple_findings_same_category(self, scoring_engine):
        """Test multiple findings in same category."""
        findings = [
            RuleFinding(
                rule_id="TEST-001",
                rule_name="Test Rule 1",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Finding 1",
                recommendation="Fix 1",
            ),
            RuleFinding(
                rule_id="TEST-002",
                rule_name="Test Rule 2",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Finding 2",
                recommendation="Fix 2",
            ),
            RuleFinding(
                rule_id="TEST-003",
                rule_name="Test Rule 3",
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description="Finding 3",
                recommendation="Fix 3",
            ),
        ]

        result = scoring_engine.calculate_scores(findings)

        assert result.total_findings == 3
        security_score = next(
            cs for cs in result.category_scores if cs.category == Category.SECURITY
        )
        # 2 high (10 each) + 1 medium (5) = 25 deduction
        assert security_score.score == 75.0

    def test_findings_across_categories(self, scoring_engine):
        """Test findings distributed across categories."""
        findings = [
            RuleFinding(
                rule_id="SEC-001",
                rule_name="Security Issue",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Security finding",
                recommendation="Fix security",
            ),
            RuleFinding(
                rule_id="REL-001",
                rule_name="Reliability Issue",
                severity=Severity.MEDIUM,
                category=Category.RELIABILITY,
                description="Reliability finding",
                recommendation="Fix reliability",
            ),
            RuleFinding(
                rule_id="SCALE-001",
                rule_name="Scalability Issue",
                severity=Severity.LOW,
                category=Category.SCALABILITY,
                description="Scalability finding",
                recommendation="Fix scalability",
            ),
        ]

        result = scoring_engine.calculate_scores(findings)

        assert result.total_findings == 3
        # Each category should have different scores based on findings
        security_score = next(
            cs for cs in result.category_scores if cs.category == Category.SECURITY
        )
        reliability_score = next(
            cs for cs in result.category_scores if cs.category == Category.RELIABILITY
        )
        scalability_score = next(
            cs for cs in result.category_scores if cs.category == Category.SCALABILITY
        )

        # Security: 1 high = 10 deduction -> 90
        assert security_score.score == 90.0
        # Reliability: 1 medium = 5 deduction -> 95
        assert reliability_score.score == 95.0
        # Scalability: 1 low = 2 deduction -> 98
        assert scalability_score.score == 98.0

    def test_grade_calculation(self, scoring_engine):
        """Test grade calculation based on score."""
        # Test grade A (>= 90)
        result = scoring_engine.calculate_scores([])
        assert result.grade == "A"

        # Create findings to get different grades
        # Grade B (>= 75): Need score between 75-89
        findings_b = [
            RuleFinding(
                rule_id="TEST-001",
                rule_name="Test",
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description="Test",
                recommendation="Fix",
            )
        ] * 3  # 3 medium findings in security

        result_b = scoring_engine.calculate_scores(findings_b)
        # 3 medium = 15 deduction in security (35% weight)
        # Security score: 85, weighted: 85 * 0.35 = 29.75
        # Other categories: 100 * 0.65 = 65
        # Total: 94.75 -> Grade A
        assert result_b.grade in ["A", "B"]

    def test_max_deduction_cap(self, scoring_engine):
        """Test that deductions are capped at 80% per category."""
        # Create many critical findings to exceed max deduction
        findings = [
            RuleFinding(
                rule_id=f"TEST-{i}",
                rule_name=f"Test Rule {i}",
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                description=f"Finding {i}",
                recommendation="Fix",
            )
            for i in range(10)  # 10 critical = 200 points, should cap at 80
        ]

        result = scoring_engine.calculate_scores(findings)

        security_score = next(
            cs for cs in result.category_scores if cs.category == Category.SECURITY
        )

        # Max deduction is 80%, so minimum score is 20
        assert security_score.score >= 20.0
        assert security_score.deductions <= 80.0

    def test_category_score_structure(self, scoring_engine):
        """Test category score data structure."""
        findings = [
            RuleFinding(
                rule_id="TEST-001",
                rule_name="Test",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Test",
                recommendation="Fix",
            )
        ]

        result = scoring_engine.calculate_scores(findings)

        security_score = next(
            cs for cs in result.category_scores if cs.category == Category.SECURITY
        )

        assert security_score.category == Category.SECURITY
        assert security_score.score >= 0
        assert security_score.max_score == 100.0
        assert security_score.deductions > 0
        assert security_score.findings_count == 1
        assert security_score.high_count == 1

    def test_score_interpretation(self, scoring_engine):
        """Test score interpretation."""
        interpretation = scoring_engine.get_score_interpretation(95)
        assert interpretation["status"] == "Excellent"
        assert interpretation["color"] == "green"

        interpretation = scoring_engine.get_score_interpretation(80)
        assert interpretation["status"] == "Good"
        assert interpretation["color"] == "blue"

        interpretation = scoring_engine.get_score_interpretation(65)
        assert interpretation["status"] == "Fair"
        assert interpretation["color"] == "yellow"

        interpretation = scoring_engine.get_score_interpretation(45)
        assert interpretation["status"] == "Critical"
        assert interpretation["color"] == "red"


class TestScoringWeights:
    """Test scoring weights configuration."""

    def test_default_weights_sum_to_one(self):
        """Test that default category weights sum to 1.0."""
        weights = ScoringWeights()
        total = sum(weights.CATEGORY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_custom_weights(self):
        """Test using custom weights."""
        custom_weights = ScoringWeights()
        custom_weights.CATEGORY_WEIGHTS[Category.SECURITY] = 0.50

        engine = ScoringEngine(weights=custom_weights)
        findings = [
            RuleFinding(
                rule_id="TEST-001",
                rule_name="Test",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Test",
                recommendation="Fix",
            )
        ]

        result = engine.calculate_scores(findings)

        # Security should have more impact with 50% weight
        assert result.score < 100.0
