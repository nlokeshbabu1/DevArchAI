"""
Repository Analysis Service
Orchestrates GitHub repository analysis for DevOps stack detection.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.github_validator import GitHubValidator, ValidationResult
from app.services.github_scanner import GitHubScanner, fetch_repo_files
from app.services.devops_detector import DevOpsDetector, detect_devops_stack, DevOpsStackResult
from app.models.repo_analysis import RepoAnalysis
from app.schemas.repo_analysis import DevOpsStack
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException

logger = structlog.get_logger(__name__)


class RepoAnalysisService:
    """Service for analyzing GitHub repositories."""

    def __init__(self, db: AsyncSession, github_token: Optional[str] = None):
        self.db = db
        self.github_token = github_token
        self.validator = GitHubValidator()
        self.scanner = GitHubScanner(token=github_token)
        self.detector = DevOpsDetector()

    async def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Analyze a GitHub repository for DevOps stack.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Analysis result dictionary

        Raises:
            InvalidRepositoryException: If URL is invalid
            RepositoryNotFoundException: If repository doesn't exist
        """
        # Step 1: Validate URL
        validation = self.validator.validate_github_repo(repo_url)

        if not validation.valid:
            raise InvalidRepositoryException(f"Invalid GitHub URL: {validation.error_message}")

        # Step 2: Fetch repository files
        try:
            files = await self.scanner.fetch_file_tree(repo_url)
        except Exception as e:
            logger.error("Failed to fetch repository files", repo_url=repo_url, error=str(e))
            raise RepositoryNotFoundException(f"Failed to fetch repository: {str(e)}")

        # Step 3: Detect DevOps stack
        stack_result = self.detector.detect(files)

        # Step 4: Calculate DevOps score
        score = self._calculate_devops_score(stack_result)

        # Step 5: Get repository info
        try:
            repo_info = await self.scanner.get_repository_info(repo_url)
        except Exception:
            repo_info = {
                "full_name": f"{validation.owner}/{validation.repo}",
                "description": None,
            }

        # Step 6: Save to database
        analysis = await self._save_analysis(
            repo_url=repo_url,
            validation=validation,
            stack_result=stack_result,
            score=score,
            files_count=len(files),
            repo_info=repo_info,
        )

        logger.info(
            "Repository analysis completed",
            repo=validation.owner + "/" + validation.repo,
            score=score,
            files=len(files),
        )

        return {
            "repo": f"{validation.owner}/{validation.repo}",
            "repo_url": repo_url,
            "repo_owner": validation.owner,
            "repo_name": validation.repo,
            "devops_stack": self._convert_stack_to_schema(stack_result),
            "devops_score": score,
            "files_analyzed": len(files),
            "analysis_id": analysis.id,
            "created_at": analysis.created_at,
        }

    def _calculate_devops_score(self, stack_result: DevOpsStackResult) -> float:
        """
        Calculate DevOps maturity score based on detected stack.

        Scoring:
        - Docker: 15 points
        - Terraform: 20 points
        - Kubernetes: 20 points
        - CI/CD: 20 points
        - Monitoring: 15 points
        - Helm: 10 points
        - Security scanning: 10 points
        - Ansible: 10 points
        """
        score = 0.0

        # Containers (15 points)
        if stack_result.docker:
            score += 15

        # Infrastructure as Code (20 points for Terraform, 10 for others)
        if stack_result.terraform:
            score += 20
        elif stack_result.ansible:
            score += 10
        elif stack_result.pulumi or stack_result.cloudformation:
            score += 15

        # Kubernetes (20 points)
        if stack_result.kubernetes:
            score += 20
            # Bonus for Helm (5 points)
            if stack_result.helm:
                score += 5

        # CI/CD (20 points)
        if stack_result.cicd:
            score += 20
            # Bonus for GitHub Actions (5 points - modern choice)
            if stack_result.cicd == "github_actions":
                score += 5

        # Monitoring (15 points)
        if stack_result.monitoring:
            score += 15

        # Security (10 points)
        if stack_result.security_scanning:
            score += 10

        # Cap at 100
        return min(100.0, score)

    def _convert_stack_to_schema(self, stack_result: DevOpsStackResult) -> DevOpsStack:
        """Convert detection result to Pydantic schema."""
        return DevOpsStack(
            docker=stack_result.docker,
            docker_files=stack_result.docker_files,
            terraform=stack_result.terraform,
            terraform_files=stack_result.terraform_files,
            pulumi=stack_result.pulumi,
            pulumi_files=stack_result.pulumi_files,
            cloudformation=stack_result.cloudformation,
            cloudformation_files=stack_result.cloudformation_files,
            ansible=stack_result.ansible,
            ansible_files=stack_result.ansible_files,
            kubernetes=stack_result.kubernetes,
            kubernetes_files=stack_result.kubernetes_files,
            helm=stack_result.helm,
            helm_files=stack_result.helm_files,
            kustomize=stack_result.kustomize,
            kustomize_files=stack_result.kustomize_files,
            cicd=stack_result.cicd,
            cicd_files=stack_result.cicd_files,
            monitoring=stack_result.monitoring,
            monitoring_files=stack_result.monitoring_files,
            prometheus=stack_result.prometheus,
            prometheus_files=stack_result.prometheus_files,
            grafana=stack_result.grafana,
            grafana_files=stack_result.grafana_files,
            datadog=stack_result.datadog,
            datadog_files=stack_result.datadog_files,
            service_mesh=stack_result.service_mesh,
            service_mesh_files=stack_result.service_mesh_files,
            istio=stack_result.istio,
            istio_files=stack_result.istio_files,
            security_scanning=stack_result.security_scanning,
            security_files=stack_result.security_files,
        )

    async def _save_analysis(
        self,
        repo_url: str,
        validation: ValidationResult,
        stack_result: DevOpsStackResult,
        score: float,
        files_count: int,
        repo_info: Dict[str, Any],
    ) -> RepoAnalysis:
        """Save analysis result to database."""
        analysis = RepoAnalysis(
            repo_url=repo_url,
            repo_owner=validation.owner,
            repo_name=validation.repo,
            repo_full_name=f"{validation.owner}/{validation.repo}",
            detected_stack=stack_result.to_dict(),
            has_docker=stack_result.docker,
            has_terraform=stack_result.terraform,
            has_kubernetes=stack_result.kubernetes,
            has_cicd=bool(stack_result.cicd),
            has_monitoring=stack_result.monitoring,
            has_helm=stack_result.helm,
            has_ansible=stack_result.ansible,
            cicd_type=stack_result.cicd,
            devops_score=score,
            files_analyzed=files_count,
            status="completed",
        )

        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)

        return analysis

    async def get_analysis_by_id(self, analysis_id: int) -> Optional[RepoAnalysis]:
        """Get analysis by ID."""
        result = await self.db.execute(
            select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_analyses_by_repo(self, repo_url: str, limit: int = 10) -> List[RepoAnalysis]:
        """Get recent analyses for a repository."""
        result = await self.db.execute(
            select(RepoAnalysis)
            .where(RepoAnalysis.repo_url == repo_url)
            .order_by(RepoAnalysis.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_analyses(self, limit: int = 20) -> List[RepoAnalysis]:
        """Get recent analyses."""
        result = await self.db.execute(
            select(RepoAnalysis)
            .order_by(RepoAnalysis.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_missing_best_practices(self, stack_result: DevOpsStackResult) -> List[Dict[str, Any]]:
        """
        Identify missing best practices based on detected stack.

        Returns list of recommendations.
        """
        missing = []

        # If no Docker
        if not stack_result.docker:
            missing.append({
                "category": "Containers",
                "title": "No Docker Configuration",
                "description": "No Dockerfile or docker-compose.yml detected",
                "severity": "high",
                "recommendation": "Add Dockerfile to containerize your application for consistent deployments",
            })

        # If no IaC
        if not stack_result.terraform and not stack_result.ansible and not stack_result.pulumi:
            missing.append({
                "category": "Infrastructure as Code",
                "title": "No Infrastructure as Code",
                "description": "No Terraform, Ansible, or Pulumi configuration detected",
                "severity": "high",
                "recommendation": "Use Terraform or Ansible to manage infrastructure declaratively",
            })

        # If no Kubernetes
        if not stack_result.kubernetes:
            missing.append({
                "category": "Orchestration",
                "title": "No Kubernetes Configuration",
                "description": "No Kubernetes manifests detected",
                "severity": "medium",
                "recommendation": "Consider using Kubernetes for container orchestration in production",
            })

        # If no CI/CD
        if not stack_result.cicd:
            missing.append({
                "category": "CI/CD",
                "title": "No CI/CD Pipeline",
                "description": "No GitHub Actions, GitLab CI, Jenkins, or other CI/CD detected",
                "severity": "critical",
                "recommendation": "Set up automated CI/CD pipeline for continuous integration and deployment",
            })

        # If no monitoring
        if not stack_result.monitoring:
            missing.append({
                "category": "Monitoring",
                "title": "No Monitoring Configuration",
                "description": "No Prometheus, Grafana, or Datadog configuration detected",
                "severity": "high",
                "recommendation": "Implement monitoring with Prometheus and Grafana for observability",
            })

        # If no security scanning
        if not stack_result.security_scanning:
            missing.append({
                "category": "Security",
                "title": "No Security Scanning",
                "description": "No security scanning configuration detected",
                "severity": "medium",
                "recommendation": "Add security scanning (Trivy, Snyk, Checkov) to your CI/CD pipeline",
            })

        # If Docker but no Helm
        if stack_result.docker and not stack_result.helm and stack_result.kubernetes:
            missing.append({
                "category": "Kubernetes",
                "title": "No Helm Charts",
                "description": "Docker and Kubernetes detected but no Helm charts",
                "severity": "low",
                "recommendation": "Use Helm to package and manage Kubernetes applications",
            })

        return missing

    async def close(self):
        """Close scanner client."""
        await self.scanner.close()


# Convenience function for creating service
def get_analysis_service(db: AsyncSession, github_token: Optional[str] = None) -> RepoAnalysisService:
    """Get repository analysis service instance."""
    return RepoAnalysisService(db, github_token)
