"""
Dockerfile Analysis Rules
"""

from typing import Any, Dict, List
from app.rules.base import BaseRule, Rule, RuleFinding, Severity, Category, register_rule


@register_rule
class DockerLatestTagRule(BaseRule):
    """Check if Docker image uses latest tag."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_latest_tag",
            name="Docker Image Uses Latest Tag",
            description="Using 'latest' tag for base image makes builds non-reproducible and may introduce unexpected changes",
            recommendation="Pin base images to specific version tags (e.g., node:18.17.0-alpine instead of node:latest)",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["docker", "image", "versioning"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            base_image = resource.get("base_image", {})
            if base_image and base_image.get("is_latest"):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Base image '{base_image.get('full', 'unknown')}' uses 'latest' tag",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"base_image": base_image.get("full")},
                ))

        return findings


@register_rule
class DockerRunsAsRootRule(BaseRule):
    """Check if Docker container runs as root."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_runs_as_root",
            name="Container Runs as Root User",
            description="Running containers as root increases security risk and potential for container escape attacks",
            recommendation="Add USER instruction to run as non-root user (e.g., USER appuser)",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["docker", "security", "user"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            user = resource.get("user")
            if not user or user == "root" or user == "0":
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


@register_rule
class DockerNoHealthcheckRule(BaseRule):
    """Check if Dockerfile has HEALTHCHECK instruction."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_no_healthcheck",
            name="Missing HEALTHCHECK Instruction",
            description="No HEALTHCHECK instruction defined, making it harder to detect container failures",
            recommendation="Add HEALTHCHECK instruction to monitor container health (e.g., HEALTHCHECK CMD curl -f http://localhost/ || exit 1)",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["docker", "healthcheck", "reliability"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

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


@register_rule
class DockerNoMultistageRule(BaseRule):
    """Check if Dockerfile uses multi-stage builds."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_no_multistage",
            name="Missing Multi-Stage Build",
            description="Multi-stage builds reduce image size and attack surface by excluding build tools from final image",
            recommendation="Use multi-stage builds with separate builder and runtime stages",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["docker", "multistage", "security"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            instructions = resource.get("instructions", [])
            from_count = sum(1 for i in instructions if i.get("instruction") == "FROM")

            if from_count < 2:
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


@register_rule
class DockerLargeBaseImageRule(BaseRule):
    """Check if Docker uses large base images."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_large_base_image",
            name="Large Base Image Detected",
            description="Using large base images increases attack surface and deployment time",
            recommendation="Use smaller base images like alpine variants (e.g., alpine, slim, distroless)",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["docker", "image", "size"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        large_images = ["ubuntu", "debian", "centos", "fedora", "node:", "python:", "openjdk"]
        small_indicators = ["alpine", "slim", "distroless", "scratch", "busybox"]

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            base_image = resource.get("base_image", {})
            image_full = base_image.get("full", "").lower()
            repository = base_image.get("repository", "").lower()

            # Check if it's a large image without small indicators
            is_large = any(large in image_full or large in repository for large in large_images)
            is_small = any(small in image_full for small in small_indicators)

            if is_large and not is_small:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Base image '{base_image.get('full')}' is large. Consider using alpine or slim variants.",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"base_image": base_image.get("full")},
                ))

        return findings


@register_rule
class DockerCopyAllContextRule(BaseRule):
    """Check if Dockerfile copies entire context."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_copy_all_context",
            name="COPY . . Without .dockerignore",
            description="Using 'COPY . .' without .dockerignore may include unnecessary or sensitive files",
            recommendation="Use specific COPY commands or ensure .dockerignore excludes unnecessary files",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["docker", "copy", "security"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            copy_commands = resource.get("copy_commands", [])
            for cmd in copy_commands:
                if cmd.get("source") == "." and cmd.get("destination"):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        line_number=cmd.get("line_number"),
                    ))

        return findings


@register_rule
class DockerExposesManyPortsRule(BaseRule):
    """Check if Dockerfile exposes too many ports."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_exposes_unnecessary_ports",
            name="Excessive Port Exposure",
            description="Exposing many ports increases attack surface and may indicate misconfiguration",
            recommendation="Only expose necessary ports and document why each port is needed",
            severity=Severity.LOW,
            category=Category.SECURITY,
            tags=["docker", "ports", "security"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            exposed_ports = resource.get("exposed_ports", [])
            if len(exposed_ports) > 5:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Dockerfile exposes {len(exposed_ports)} ports, which may be excessive",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"port_count": len(exposed_ports)},
                ))

        return findings


@register_rule
class DockerSecretInEnvRule(BaseRule):
    """Check for secrets in Dockerfile ENV variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="docker_secret_in_env",
            name="Potential Secret in ENV Variable",
            description="Potential secrets are exposed in Dockerfile ENV variables, which are visible in image history",
            recommendation="Use Docker secrets, build arguments, or runtime environment variables instead of hardcoding secrets",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["docker", "secrets", "security"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        secret_patterns = ["password", "secret", "key", "token", "credential", "api_key", "private"]

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            env_vars = resource.get("env_vars", {})
            for env_name in env_vars.keys():
                if any(pattern in env_name.lower() for pattern in secret_patterns):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Potential secret in ENV variable: {env_name}",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        metadata={"env_var": env_name},
                    ))

        return findings
