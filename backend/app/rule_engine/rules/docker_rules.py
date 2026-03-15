"""Docker rules for infrastructure analysis."""

from typing import Any

from app.rule_engine.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["dockerfile"])
class DockerRootUserRule(BaseRule):
    """Check if Docker container runs as root."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-001",
            name="Container Running as Root",
            description="Docker container runs as root user, increasing security risk",
            recommendation="Add USER instruction to run container as non-root user",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["docker", "security", "user"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            security_issues = resource.get("security_issues", [])
            for issue in security_issues:
                if issue.get("issue") == "running_as_root":
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=issue.get("description", self.rule.description),
                        recommendation=issue.get("recommendation", self.rule.recommendation),
                        file_path=file_path,
                    ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerSecretInEnvRule(BaseRule):
    """Check for secrets exposed in Dockerfile ENV variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-002",
            name="Secret in Dockerfile ENV",
            description="Potential secrets are exposed in Dockerfile ENV variables",
            recommendation="Use Docker secrets, build arguments, or runtime environment variables instead of hardcoding secrets",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["docker", "secrets", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            security_issues = resource.get("security_issues", [])
            for issue in security_issues:
                if issue.get("issue") == "secret_in_env":
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.CRITICAL,
                        category=self.rule.category,
                        description=issue.get("description", self.rule.description),
                        recommendation=issue.get("recommendation", self.rule.recommendation),
                        file_path=file_path,
                        line_number=issue.get("line_number"),
                    ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerLatestTagRule(BaseRule):
    """Check for use of 'latest' tag in Docker images."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SCALE-001",
            name="Using Latest Tag",
            description="Dockerfile uses 'latest' tag which can cause inconsistent deployments",
            recommendation="Pin base images to specific versions for reproducible builds",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["docker", "image", "versioning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            base_image = resource.get("base_image", {})
            if base_image and base_image.get("is_latest"):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Base image '{base_image.get('full')}' uses latest tag",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"image": base_image.get("full")},
                ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerMissingHealthcheckRule(BaseRule):
    """Check for missing HEALTHCHECK in Dockerfile."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-REL-001",
            name="Missing Docker HEALTHCHECK",
            description="Dockerfile does not have HEALTHCHECK instruction",
            recommendation="Add HEALTHCHECK to enable container health monitoring",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["docker", "health", "monitoring"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            healthcheck = resource.get("healthcheck")
            if not healthcheck or healthcheck.get("disabled"):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerLargeBaseImageRule(BaseRule):
    """Check for large base images."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-COST-001",
            name="Large Base Image",
            description="Using a large base image increases build time and storage costs",
            recommendation="Consider using Alpine or distroless base images to reduce size",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["docker", "image", "size", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        large_images = ["ubuntu", "debian", "centos", "fedora", "amazonlinux"]

        for resource in resources:
            base_image = resource.get("base_image", {})
            if base_image:
                repository = base_image.get("repository", "").lower()
                if any(large in repository for large in large_images):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Base image '{base_image.get('full')}' may be large",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        metadata={"image": base_image.get("full")},
                    ))

        return findings
