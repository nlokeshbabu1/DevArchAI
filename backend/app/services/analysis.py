"""
Analysis Service - Orchestrates the analysis pipeline
"""

import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import structlog

from app.parsers.base import ParserRegistry, ParsedFile
from app.parsers.terraform import TerraformParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.cicd import CICDParser
from app.rules.base import RuleRegistry, RuleFinding, Severity, Category
from app.rules import security, scalability, reliability, cost, observability
from app.ai.engine import get_llm_provider, BaseLLMProvider
from app.scoring.engine import ScoringEngine, OverallScore
from app.models.schemas import AnalysisReport, CategoryScore as SchemaCategoryScore
from app.config import settings

logger = structlog.get_logger(__name__)


class AnalysisService:
    """Main service for orchestrating repository analysis."""
    
    def __init__(self):
        self.parser_registry = self._setup_parsers()
        self.rule_registry = RuleRegistry()
        self.scoring_engine = ScoringEngine()
        self.llm_provider: Optional[BaseLLMProvider] = None
    
    def _setup_parsers(self) -> ParserRegistry:
        """Initialize and register all parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        return registry
    
    async def analyze_repository(
        self,
        repo_path: str,
        include_ai_explanations: bool = True,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> AnalysisReport:
        """
        Analyze a repository and generate a report.
        
        Args:
            repo_path: Path to the cloned repository
            include_ai_explanations: Whether to generate AI explanations
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            Complete AnalysisReport
        """
        start_time = time.time()
        report_id = str(uuid.uuid4())
        
        def update_progress(progress: int):
            if progress_callback:
                progress_callback(progress)
        
        update_progress(20)
        
        # Initialize LLM provider if needed
        if include_ai_explanations:
            self.llm_provider = get_llm_provider()
        
        # Scan repository for files
        logger.info("Scanning repository for analyzable files", path=repo_path)
        files_to_analyze = self._scan_repository(repo_path)
        
        update_progress(30)
        
        # Parse all files
        logger.info("Parsing files", count=len(files_to_analyze))
        parsed_files = self._parse_files(files_to_analyze)
        
        update_progress(50)
        
        # Run rule engine
        logger.info("Running rule engine")
        all_findings = self._run_rules(parsed_files)
        
        update_progress(70)
        
        # Generate AI explanations
        if include_ai_explanations and self.llm_provider:
            logger.info("Generating AI explanations")
            all_findings = await self._add_ai_explanations(all_findings)
        
        update_progress(85)
        
        # Calculate scores
        logger.info("Calculating scores")
        overall_score = self.scoring_engine.calculate_scores(all_findings)
        
        # Generate AI summary
        executive_summary = None
        risk_analysis = None
        prioritized_recommendations = None
        
        if include_ai_explanations and self.llm_provider:
            logger.info("Generating AI summary")
            findings_dict = [self._finding_to_dict(f) for f in all_findings]
            scores_dict = {
                cs.category.value: cs.score for cs in overall_score.category_scores
            }
            
            executive_summary = await self.llm_provider.generate_executive_summary(
                findings_dict, scores_dict
            )
            risk_analysis = await self.llm_provider.generate_risk_analysis(findings_dict)
            prioritized_recommendations = await self.llm_provider.generate_prioritized_recommendations(
                findings_dict
            )
        
        update_progress(95)
        
        # Build report
        analysis_duration = time.time() - start_time
        
        # Convert findings to schema format
        schema_findings = [self._finding_to_schema(f) for f in all_findings]
        
        # Calculate summary
        summary = {
            "critical": sum(1 for f in all_findings if f.severity == Severity.CRITICAL),
            "high": sum(1 for f in all_findings if f.severity == Severity.HIGH),
            "medium": sum(1 for f in all_findings if f.severity == Severity.MEDIUM),
            "low": sum(1 for f in all_findings if f.severity == Severity.LOW),
            "info": sum(1 for f in all_findings if f.severity == Severity.INFO),
        }
        
        # Category scores
        category_scores = [
            SchemaCategoryScore(
                category=cs.category,
                score=cs.score,
                findings_count=cs.findings_count,
                critical_count=cs.critical_count,
                high_count=cs.high_count,
                medium_count=cs.medium_count,
                low_count=cs.low_count,
            )
            for cs in overall_score.category_scores
        ]
        
        report = AnalysisReport(
            id=report_id,
            repository_url="",  # Will be set by caller
            repository_name=repo_path.split("/")[-1],
            overall_score=overall_score.score,
            category_scores=category_scores,
            findings=schema_findings,
            summary=summary,
            executive_summary=executive_summary,
            risk_analysis=risk_analysis,
            prioritized_recommendations=prioritized_recommendations,
            files_analyzed=[str(f.file_path) for f in parsed_files],
            analysis_duration_seconds=round(analysis_duration, 2),
            created_at=datetime.utcnow(),
        )
        
        update_progress(100)
        
        logger.info(
            "Analysis complete",
            report_id=report_id,
            score=overall_score.score,
            findings=len(all_findings),
            duration=analysis_duration,
        )
        
        return report
    
    def _scan_repository(self, repo_path: str) -> List[Path]:
        """Scan repository for analyzable files."""
        files = []
        repo = Path(repo_path)
        
        # Directories to scan
        scan_dirs = [
            repo,
            repo / "terraform",
            repo / "kubernetes",
            repo / "k8s",
            repo / "manifests",
            repo / ".github" / "workflows",
            repo / "deployments",
        ]
        
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            
            for file_path in scan_dir.rglob("*"):
                if file_path.is_file():
                    if self.parser_registry.get_parser(file_path):
                        files.append(file_path)
        
        return files
    
    def _parse_files(self, files: List[Path]) -> List[ParsedFile]:
        """Parse all files using appropriate parsers."""
        parsed_files = []
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                parsed = self.parser_registry.parse_file(file_path, content)
                if parsed:
                    parsed_files.append(parsed)
            except Exception as e:
                logger.warning(
                    "Failed to parse file",
                    file=str(file_path),
                    error=str(e),
                )
        
        return parsed_files
    
    def _run_rules(self, parsed_files: List[ParsedFile]) -> List[RuleFinding]:
        """Run all rules against parsed files."""
        all_findings = []
        
        for parsed_file in parsed_files:
            # Extract resources for rule evaluation
            resources = parsed_file.parsed_data  # Simplified - parsers should extract resources
            
            # Run all rules
            file_findings = self.rule_registry.evaluate_all(
                [resources],
                str(parsed_file.file_path),
            )
            all_findings.extend(file_findings)
        
        return all_findings
    
    async def _add_ai_explanations(
        self,
        findings: List[RuleFinding],
    ) -> List[RuleFinding]:
        """Add AI explanations to findings."""
        if not self.llm_provider:
            return findings
        
        # Process findings in batches to avoid rate limits
        for finding in findings[:20]:  # Limit to top 20 findings
            try:
                explanation = await self.llm_provider.generate_explanation(
                    finding.description,
                    {
                        "rule_id": finding.rule_id,
                        "category": finding.category.value,
                        "severity": finding.severity.value,
                        "file_path": finding.file_path,
                    },
                )
                
                finding.ai_explanation = explanation.explanation
                finding.impact_analysis = explanation.impact_analysis
                finding.recommendation = "; ".join(explanation.remediation_steps) or finding.recommendation
                
            except Exception as e:
                logger.warning(
                    "Failed to generate AI explanation",
                    rule_id=finding.rule_id,
                    error=str(e),
                )
        
        return findings
    
    def _finding_to_dict(self, finding: RuleFinding) -> Dict[str, Any]:
        """Convert RuleFinding to dictionary for AI processing."""
        return {
            "rule_id": finding.rule_id,
            "rule_name": finding.rule_name,
            "severity": finding.severity.value,
            "category": finding.category.value,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "file_path": finding.file_path,
        }
    
    def _finding_to_schema(self, finding: RuleFinding):
        """Convert RuleFinding to API schema."""
        from app.models.schemas import RuleFinding as SchemaRuleFinding
        
        return SchemaRuleFinding(
            rule_id=finding.rule_id,
            rule_name=finding.rule_name,
            severity=finding.severity,
            category=finding.category,
            description=finding.description,
            recommendation=finding.recommendation,
            file_path=finding.file_path,
            line_number=finding.line_number,
            ai_explanation=finding.ai_explanation,
            impact_analysis=finding.impact_analysis,
            confidence_score=finding.confidence,
        )
