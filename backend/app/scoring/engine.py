"""
Scoring Engine - Production Readiness Score Calculation
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from app.rule_engine.base import Severity, Category, RuleFinding
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CategoryScore:
    """Score for a specific category."""

    category: Category
    score: float
    max_score: float
    deductions: float
    findings_count: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


@dataclass
class OverallScore:
    """Overall production readiness score."""

    score: float
    grade: str
    category_scores: List[CategoryScore]
    total_findings: int
    critical_findings: int
    high_findings: int


class ScoringWeights:
    """Weights for different categories and severities."""

    # Category weights (must sum to 1.0)
    CATEGORY_WEIGHTS = {
        Category.SECURITY: 0.35,
        Category.SCALABILITY: 0.20,
        Category.RELIABILITY: 0.25,
        Category.COST: 0.10,
        Category.OBSERVABILITY: 0.10,
    }

    # Severity deduction multipliers - Using formula: score = 100 - (critical * 20 + high * 10 + medium * 5)
    SEVERITY_DEDUCTIONS = {
        Severity.CRITICAL: 20.0,
        Severity.HIGH: 10.0,
        Severity.MEDIUM: 5.0,
        Severity.LOW: 2.0,
        Severity.INFO: 0.0,
    }

    # Maximum deductions per category (as percentage of category score)
    MAX_CATEGORY_DEDUCTION = 0.8  # 80% max deduction


class ScoringEngine:
    """Engine for calculating production readiness scores."""

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def calculate_scores(
        self,
        findings: List[RuleFinding],
    ) -> OverallScore:
        """
        Calculate overall and category scores from findings.

        Uses formula: score = 100 - (critical * 20 + high * 10 + medium * 5)

        Args:
            findings: List of rule findings from analysis

        Returns:
            OverallScore with detailed breakdown
        """
        # Group findings by category
        findings_by_category: Dict[Category, List[RuleFinding]] = {}
        for finding in findings:
            category = finding.category
            if category not in findings_by_category:
                findings_by_category[category] = []
            findings_by_category[category].append(finding)

        # Calculate category scores
        category_scores = []
        total_weighted_score = 0.0

        for category, weight in self.weights.CATEGORY_WEIGHTS.items():
            category_findings = findings_by_category.get(category, [])
            category_score = self._calculate_category_score(category, category_findings)
            category_scores.append(category_score)

            # Weight the score
            total_weighted_score += category_score.score * weight

        # Calculate overall metrics
        total_findings = len(findings)
        critical_findings = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_findings = sum(1 for f in findings if f.severity == Severity.HIGH)

        # Determine grade
        grade = self._score_to_grade(total_weighted_score)

        return OverallScore(
            score=round(total_weighted_score, 1),
            grade=grade,
            category_scores=category_scores,
            total_findings=total_findings,
            critical_findings=critical_findings,
            high_findings=high_findings,
        )

    def _calculate_category_score(
        self,
        category: Category,
        findings: List[RuleFinding],
    ) -> CategoryScore:
        """
        Calculate score for a single category.
        
        Formula: score = 100 - (critical * 20 + high * 10 + medium * 5)
        """
        # Start with perfect score
        max_score = 100.0
        deductions = 0.0

        # Count by severity
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium_count = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == Severity.LOW)

        # Calculate deductions using the formula
        deductions += critical_count * self.weights.SEVERITY_DEDUCTIONS[Severity.CRITICAL]
        deductions += high_count * self.weights.SEVERITY_DEDUCTIONS[Severity.HIGH]
        deductions += medium_count * self.weights.SEVERITY_DEDUCTIONS[Severity.MEDIUM]
        deductions += low_count * self.weights.SEVERITY_DEDUCTIONS[Severity.LOW]

        # Cap deductions
        max_deduction = max_score * self.weights.MAX_CATEGORY_DEDUCTION
        deductions = min(deductions, max_deduction)

        # Calculate final score (minimum 0)
        final_score = max(0, max_score - deductions)

        return CategoryScore(
            category=category,
            score=round(final_score, 1),
            max_score=max_score,
            deductions=round(deductions, 1),
            findings_count=len(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def get_score_interpretation(self, score: float) -> Dict[str, Any]:
        """Get human-readable interpretation of score."""
        if score >= 90:
            return {
                "status": "Excellent",
                "description": "Infrastructure is production-ready with minor improvements needed",
                "color": "green",
            }
        elif score >= 75:
            return {
                "status": "Good",
                "description": "Infrastructure is mostly production-ready with some improvements needed",
                "color": "blue",
            }
        elif score >= 60:
            return {
                "status": "Fair",
                "description": "Infrastructure has several issues that should be addressed before production",
                "color": "yellow",
            }
        elif score >= 50:
            return {
                "status": "Poor",
                "description": "Infrastructure has significant issues and is not ready for production",
                "color": "orange",
            }
        else:
            return {
                "status": "Critical",
                "description": "Infrastructure has critical issues and should not be deployed to production",
                "color": "red",
            }


class ScoreTrendAnalyzer:
    """Analyze score trends over time."""

    def __init__(self):
        self.historical_scores: List[Dict[str, Any]] = []

    def add_score(self, score_data: Dict[str, Any]) -> None:
        """Add a historical score."""
        self.historical_scores.append(score_data)

    def get_trend(self) -> str:
        """Determine if scores are improving or declining."""
        if len(self.historical_scores) < 2:
            return "insufficient_data"

        recent = self.historical_scores[-1]["score"]
        previous = self.historical_scores[-2]["score"]

        if recent > previous + 5:
            return "improving"
        elif recent < previous - 5:
            return "declining"
        else:
            return "stable"

    def get_average_score(self) -> float:
        """Get average historical score."""
        if not self.historical_scores:
            return 0.0

        return sum(s["score"] for s in self.historical_scores) / len(self.historical_scores)
