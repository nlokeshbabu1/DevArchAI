"""
Docker Security Rules - DevSecOps Rule Set (DKR-SEC-001 to DKR-SEC-010)

Production-grade Docker security scanning rules for DevArchAI.
"""

import re
from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["dockerfile"])
class DockerRootUserRule(BaseRule):
    """DKR-SEC-001: Check if container runs as root."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-001",
            name="Container Running as Root",
            description="Container runs as root user which can lead to container breakout attacks and host compromise",
            recommendation="Add a non-root user to the Dockerfile:\n\nRUN addgroup -S app && adduser -S app -G app\nUSER app",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["docker", "security", "user", "root"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            user = resource.get("user")
            # No USER instruction or explicitly root
            if not user or user == "root" or user == "0":
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={},
                    impact_analysis="Attackers gaining root access can escape the container and compromise the host system",
                ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerLatestTagRule(BaseRule):
    """DKR-SEC-002: Check if Docker image uses latest tag."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-002",
            name="Latest Tag Used",
            description="Using the 'latest' tag can introduce unpredictable behavior and security risks due to uncontrolled updates",
            recommendation="Pin base images to specific version tags:\n\nFROM node:18-alpine\nFROM python:3.11-slim",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["docker", "image", "versioning", "tag"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
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
                    description=f"Base image '{base_image.get('full')}' uses 'latest' tag",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"base_image": base_image.get("full")},
                    
                    
                    
                ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerSecretsInDockerfileRule(BaseRule):
    """DKR-SEC-003: Check for secrets in Dockerfile."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-003",
            name="Secrets in Dockerfile",
            description="Hardcoded secrets inside Dockerfiles can leak sensitive credentials through image layers",
            recommendation="Use environment variables, Docker secrets, or secret managers:\n\nARG API_KEY (use build-time only)\nUse runtime secrets or mounted volumes",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["docker", "secrets", "security", "credentials"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)[\s=]+[A-Za-z0-9_]{16,}', "API Key"),
            (r'(?i)(password|passwd|pwd)[\s=]+[^\s"\']{4,}', "Password"),
            (r'(?i)(secret|secret_key)[\s=]+[^\s"\']{8,}', "Secret"),
            (r'(?i)(token|auth_token|access_token)[\s=]+[A-Za-z0-9_-]{16,}', "Token"),
            (r'(?i)(credential|cred)[\s=]+[^\s"\']{8,}', "Credential"),
            (r'(?i)private[_-]?key[\s=]+[^\s"\']{20,}', "Private Key"),
        ]

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            instructions = resource.get("instructions", [])
            for instruction in instructions:
                cmd = instruction.get("instruction", "")
                args = instruction.get("arguments", "")
                full_line = f"{cmd} {args}"

                for pattern, secret_type in secret_patterns:
                    if re.search(pattern, full_line):
                        # Skip if it's clearly a placeholder
                        if re.search(r'<.*?>|\$\{.*\}|\$[A-Z_]+', args):
                            continue

                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Potential {secret_type} detected in Dockerfile",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            line_number=instruction.get("line_number"),
                            metadata={"secret_type": secret_type},
                        ))
                        break

        return findings


@register_rule(file_types=["dockerfile"])
class DockerMissingUserInstructionRule(BaseRule):
    """DKR-SEC-004: Check if Dockerfile lacks USER instruction."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-004",
            name="Missing USER Instruction",
            description="Dockerfiles without USER instruction default to root execution, increasing security risks",
            recommendation="Define a non-root user:\n\nRUN addgroup -S app && adduser -S app -G app\nUSER app",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["docker", "security", "user"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            instructions = resource.get("instructions", [])
            has_user = any(i.get("instruction") == "USER" for i in instructions)

            if not has_user:
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
class DockerAddInsteadOfCopyRule(BaseRule):
    """DKR-SEC-005: Check for ADD usage instead of COPY."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-005",
            name="ADD Used Instead of COPY",
            description="The ADD command may unintentionally extract archives or fetch remote URLs, introducing security risks",
            recommendation="Use COPY unless archive extraction is required:\n\nCOPY ./app /app\n# Instead of: ADD ./app.tar.gz /app/",
            severity=Severity.LOW,
            category=Category.SECURITY,
            tags=["docker", "copy", "add", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            instructions = resource.get("instructions", [])
            for instruction in instructions:
                if instruction.get("instruction") == "ADD":
                    args = instruction.get("arguments", "")
                    # Get source file (first argument)
                    source = args.split()[0] if args.split() else ""
                    # Allow ADD for remote URLs or tar extraction (documented use cases)
                    is_remote = source.startswith("http://") or source.startswith("https://")
                    is_archive = source.endswith(".tar.gz") or source.endswith(".tar") or source.endswith(".tgz") or source.endswith(".tar.bz2")
                    
                    if not (is_remote or is_archive):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"ADD instruction used: '{args[:50]}...'. Consider using COPY instead",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            line_number=instruction.get("line_number"),
                            metadata={"arguments": args},
                            
                            
                        ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerMissingHealthcheckRule(BaseRule):
    """DKR-SEC-006: Check for missing HEALTHCHECK instruction."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-006",
            name="Missing HEALTHCHECK",
            description="Without health checks, orchestrators cannot determine container health status",
            recommendation="Add a health check command:\n\nHEALTHCHECK --interval=30s --timeout=3s \\\n  CMD curl -f http://localhost:3000/health || exit 1",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["docker", "healthcheck", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            instructions = resource.get("instructions", [])
            has_healthcheck = any(i.get("instruction") == "HEALTHCHECK" for i in instructions)
            healthcheck_disabled = any(
                i.get("instruction") == "HEALTHCHECK" and "NONE" in i.get("arguments", "")
                for i in instructions
            )

            if not has_healthcheck or healthcheck_disabled:
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


@register_rule(file_types=["dockerfile", "kubernetes"])
class DockerPrivilegedContainerRule(BaseRule):
    """DKR-SEC-007: Check for privileged containers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-007",
            name="Privileged Container",
            description="Privileged containers can access host-level resources, bypassing container isolation",
            recommendation="Remove privileged mode and use specific capabilities instead:\n\ncapabilities:\n  add: [\"NET_ADMIN\"]  # Only what's needed",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["docker", "kubernetes", "privileged", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            file_type = resource.get("file_type")
            
            if file_type == "dockerfile":
                # Check for privileged runtime hints
                instructions = resource.get("instructions", [])
                for instruction in instructions:
                    args = instruction.get("arguments", "").lower()
                    if "privileged" in args or "--privileged" in args:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=self.rule.description,
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            line_number=instruction.get("line_number"),
                            
                            
                            
                        ))

            elif file_type == "kubernetes":
                if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet"]:
                    containers = resource.get("properties", {}).get("containers", [])
                    for container in containers:
                        security_context = container.get("security_context", {})
                        if security_context.get("privileged"):
                            findings.append(RuleFinding(
                                rule_id=self.rule.id,
                                rule_name=self.rule.name,
                                severity=self.rule.severity,
                                category=self.rule.category,
                                description=f"Container '{container.get('name')}' runs in privileged mode",
                                recommendation=self.rule.recommendation,
                                file_path=file_path,
                                resource_name=container.get("name"),
                                
                                
                            ))

        return findings


@register_rule(file_types=["dockerfile", "kubernetes"])
class DockerResourceLimitsRule(BaseRule):
    """DKR-SEC-008: Check for missing resource limits."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-008",
            name="No Resource Limits",
            description="Containers without resource limits can exhaust host resources, causing denial of service",
            recommendation="Define resource constraints:\n\n# Docker\ndocker run --memory=512m --cpus=1.0\n\n# Kubernetes\nresources:\n  limits:\n    memory: \"512Mi\"\n    cpu: \"1\"",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["docker", "kubernetes", "resources", "limits"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            file_type = resource.get("file_type")
            
            if file_type == "kubernetes":
                if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet"]:
                    containers = resource.get("properties", {}).get("containers", [])
                    for container in containers:
                        resources_config = container.get("resources", {})
                        limits = resources_config.get("limits", {})

                        if not limits.get("cpu") or not limits.get("memory"):
                            findings.append(RuleFinding(
                                rule_id=self.rule.id,
                                rule_name=self.rule.name,
                                severity=self.rule.severity,
                                category=self.rule.category,
                                description=f"Container '{container.get('name')}' has no resource limits",
                                recommendation=self.rule.recommendation,
                                file_path=file_path,
                                resource_name=container.get("name"),
                                metadata={"container": container.get("name")},
                                
                                
                            ))

        return findings


@register_rule(file_types=["dockerfile"])
class DockerLargeBaseImageRule(BaseRule):
    """DKR-SEC-009: Check for large base images."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-009",
            name="Large Base Image",
            description="Large base images increase attack surface and deployment time",
            recommendation="Use minimal base images:\n\nFROM alpine:3.18\nFROM gcr.io/distroless/static-debian11\nFROM python:3.11-slim",
            severity=Severity.LOW,
            category=Category.SECURITY,
            tags=["docker", "image", "size", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        large_images = ["ubuntu", "debian", "centos", "fedora"]
        small_indicators = ["alpine", "slim", "distroless", "scratch", "busybox", "micro"]

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


@register_rule(file_types=["dockerfile"])
class DockerSSHInstalledRule(BaseRule):
    """DKR-SEC-010: Check for SSH installation in container."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="DKR-SEC-010",
            name="SSH Installed in Container",
            description="SSH inside containers increases attack vectors and goes against container best practices",
            recommendation="Avoid SSH in containers. Use kubectl exec, docker exec, or remote management tools instead",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["docker", "ssh", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        ssh_patterns = ["openssh", "ssh-server", "sshd", "ssh-service"]

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            instructions = resource.get("instructions", [])
            for instruction in instructions:
                if instruction.get("instruction") == "RUN":
                    args = instruction.get("arguments", "").lower()
                    if any(ssh in args for ssh in ssh_patterns):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description="SSH server detected in container image",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            line_number=instruction.get("line_number"),
                            
                            
                            
                        ))
                        break

        return findings
