"""
CI/CD Security Rules - DevSecOps Rule Set (CI-SEC-001 to CI-SEC-010)

Production-grade CI/CD security scanning rules for DevArchAI.
"""

import re
from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["cicd"])
class CICDMissingSecurityScanRule(BaseRule):
    """CI-SEC-001: Check for missing security scanning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-001",
            name="Missing Security Scanning",
            description="CI/CD pipeline does not include security scanning (SAST/DAST/IAST)",
            recommendation="Add security scanning steps:\n\n- name: Security Scan\n  run: |\n    npm audit\n    pip-audit\n    trivy fs .",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "security", "sast", "dast"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        security_tools = [
            # SAST
            "sonarqube", "semgrep", "codeql", "snyk code", "checkmarx", "fortify",
            # DAST
            "zap", "owasp zap", "burp", "arachni",
            # General security
            "trivy", "snyk", "gitleaks", "bandit", "safety", "security-scan",
            "grype", "anchore", "clair", "defectdojo",
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps
            has_security_scan = False

            for step in all_steps:
                step_str = str(step).lower()
                step_name = str(step.get("name", "")).lower()
                step_run = str(step.get("run", "")).lower()

                if any(tool in step_str or tool in step_name or tool in step_run for tool in security_tools):
                    has_security_scan = True
                    break

            if not has_security_scan:
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


@register_rule(file_types=["cicd"])
class CICDMissingDependencyScanRule(BaseRule):
    """CI-SEC-002: Check for missing dependency scanning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-002",
            name="Missing Dependency Scanning",
            description="CI/CD pipeline does not scan dependencies for known vulnerabilities",
            recommendation="Add dependency scanning:\n\n- name: Dependency Scan\n  run: |\n    npm audit\n    pip-audit\n    cargo audit\n    gosec ./...",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "dependencies", "security", "sca"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        dependency_tools = [
            "npm audit", "yarn audit", "pnpm audit",
            "pip-audit", "safety", "pipenv check", "poetry check",
            "cargo audit", "cargo-deny",
            "gosec", "govulncheck",
            "bundle audit", "bundler-audit",
            "maven dependency-check", "owasp dependency-check",
            "dependabot", "renovate", "snyk test",
            "trivy fs", "grype",
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps
            has_dependency_scan = False

            for step in all_steps:
                step_str = str(step).lower()
                step_run = str(step.get("run", "")).lower()

                if any(tool in step_str or tool in step_run for tool in dependency_tools):
                    has_dependency_scan = True
                    break

            if not has_dependency_scan:
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


@register_rule(file_types=["cicd"])
class CICDHardcodedSecretsRule(BaseRule):
    """CI-SEC-003: Check for hardcoded secrets in pipeline."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-003",
            name="Hardcoded Secrets in Pipeline",
            description="Potential secrets are hardcoded in CI/CD pipeline configuration",
            recommendation="Use secret management:\n\n# GitHub Actions\nenv:\n  API_KEY: ${{ secrets.API_KEY }}\n\n# GitLab CI\nvariables:\n  API_KEY: $API_KEY",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["cicd", "secrets", "security", "credentials"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[A-Za-z0-9_-]{16,}["\']?', "API Key"),
            (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{6,}["\']?', "Password"),
            (r'(?i)(secret|secret_key)\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', "Secret"),
            (r'(?i)(token|auth_token|access_token)\s*[=:]\s*["\']?[A-Za-z0-9_-]{20,}["\']?', "Token"),
            (r'(?i)(credential|cred)\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', "Credential"),
            (r'(?i)(private[_-]?key|priv[_-]?key)\s*[=:]\s*["\']?[^\s"\']{20,}["\']?', "Private Key"),
            (r'(?i)(aws[_-]?access|aws[_-]?secret)\s*[=:]\s*["\']?[A-Za-z0-9/+=]{20,}["\']?', "AWS Credential"),
        ]
        # Patterns that indicate proper secret management
        safe_patterns = [
            r'\$\{\{\s*secrets\.',  # GitHub Actions
            r'\$\{.*\}',  # Variable interpolation
            r'\$[A-Z_]+',  # Environment variable
            r'\[\[.*\]\]',  # Template variable
            r'vault\.',  # Vault reference
            r'ssm:',  # AWS SSM reference
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            raw_content = resource.get("raw_content", "")

            for pattern, secret_type in secret_patterns:
                matches = re.finditer(pattern, raw_content)
                for match in matches:
                    matched_text = match.group()

                    # Check if it's properly managed
                    is_safe = any(re.search(safe, matched_text) for safe in safe_patterns)

                    # Skip placeholders and examples
                    if re.search(r'<.*?>|example|placeholder|your_.*?here|\*{3,}', matched_text, re.IGNORECASE):
                        continue

                    if not is_safe:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Potential {secret_type} detected in pipeline",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            line_number=raw_content[:match.start()].count('\n') + 1,
                            metadata={"secret_type": secret_type},
                        ))
                        break  # One finding per secret type

        return findings


@register_rule(file_types=["cicd"])
class CICDUntrustedActionsRule(BaseRule):
    """CI-SEC-004: Check for untrusted third-party actions."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-004",
            name="Untrusted Third-Party Actions",
            description="Pipeline uses third-party actions without pinning to specific commits or from untrusted sources",
            recommendation="Pin actions to full commit SHA:\n\nuses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "actions", "security", "supply-chain"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        trusted_sources = [
            "actions/",  # Official GitHub Actions
            "github/",  # GitHub
            "azure/",  # Microsoft Azure
            "aws-actions/",  # AWS
            "google-github-actions/",  # Google
            "docker/",  # Docker
            "hashicorp/",  # HashiCorp
            "slackapi/",  # Slack
            "sonarsource/",  # SonarSource
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps

            for step in all_steps:
                uses = step.get("uses", "")
                if not uses:
                    continue

                # Skip local actions
                if uses.startswith("./"):
                    continue

                # Check if pinned to SHA
                is_pinned = re.match(r'.+@[a-f0-9]{40}$', uses)

                # Check if from trusted source
                is_trusted = any(uses.lower().startswith(source) for source in trusted_sources)

                # Flag if not pinned and not from trusted source
                if not is_pinned and not is_trusted:
                    # Also flag trusted sources if not pinned (lower severity)
                    if is_trusted:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=Severity.MEDIUM,
                            category=self.rule.category,
                            description=f"Action '{uses}' not pinned to commit SHA",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            metadata={"action": uses},
                        ))
                    else:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Untrusted action '{uses}' not pinned to commit SHA",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            metadata={"action": uses},
                        ))

        return findings


@register_rule(file_types=["cicd"])
class CICDMissingBranchProtectionRule(BaseRule):
    """CI-SEC-005: Check for missing branch protection."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-005",
            name="Missing Branch Protection",
            description="Pipeline does not enforce branch protection rules for main/production branches",
            recommendation="Configure branch protection:\n\n- Require pull request reviews\n- Require status checks to pass\n- Require branches to be up to date\n- Restrict who can push",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["cicd", "branch-protection", "security", "governance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        protected_branches = ["main", "master", "prod", "production", "release"]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})

            # Check for branch protection indicators
            on_push = properties.get("on_push", [])
            on_pull_request = properties.get("on_pull_request", [])

            # Check if workflow only runs on protected branches without PR
            has_direct_push = False
            for branch in protected_branches:
                if branch in str(on_push) and branch not in str(on_pull_request):
                    has_direct_push = True

            # Check for environment protection
            environments = properties.get("environments", [])
            has_protection = properties.get("has_environment_protection", False)

            if has_direct_push and not has_protection:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description="Workflow can be triggered by direct push to protected branch",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule(file_types=["cicd"])
class CICDMissingContainerScanRule(BaseRule):
    """CI-SEC-006: Check for missing container image scanning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-006",
            name="Missing Container Scanning",
            description="CI/CD pipeline does not scan container images for vulnerabilities",
            recommendation="Add container scanning:\n\n- name: Scan Container\n  run: |\n    docker build -t myapp .\n    trivy image myapp:latest",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "container", "docker", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        container_scan_tools = [
            "trivy", "trivy image",
            "snyk container", "snyk test --docker",
            "docker scan",
            "clair", "clair-scanner",
            "grype",
            "anchore", "anchore-cli",
            "container-scan", "container_scanning",
            "dagda", "harbor-scanner",
        ]
        has_docker_build = False

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps

            for step in all_steps:
                step_str = str(step).lower()
                step_run = str(step.get("run", "")).lower()

                if "docker build" in step_str or "docker build" in step_run:
                    has_docker_build = True

                if any(tool in step_str or tool in step_run for tool in container_scan_tools):
                    return findings  # Container scanning found

            if has_docker_build:
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


@register_rule(file_types=["cicd"])
class CICDNoArtifactSigningRule(BaseRule):
    """CI-SEC-007: Check for missing artifact signing."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-007",
            name="No Artifact Signing",
            description="Build artifacts are not signed, risking supply chain attacks",
            recommendation="Sign artifacts for integrity verification:\n\n- name: Sign Container\n  uses: sigstore/cosign-installer@v3\n- name: Cosign Sign\n  run: cosign sign myapp:latest",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["cicd", "signing", "supply-chain", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        signing_tools = [
            "cosign", "sigstore",
            "gpg", "gpg --sign",
            "signify",
            "minisign",
            "artifact-sign", "sign-artifact",
            "docker trust", "docker content trust",
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps
            has_signing = False

            for step in all_steps:
                step_str = str(step).lower()
                step_run = str(step.get("run", "")).lower()

                if any(tool in step_str or tool in step_run for tool in signing_tools):
                    has_signing = True
                    break

            if not has_signing:
                # Check if there are build artifacts that should be signed
                has_artifacts = properties.get("artifacts") or \
                               any("docker build" in str(s).lower() for s in all_steps) or \
                               any("npm build" in str(s).lower() for s in all_steps)

                if has_artifacts:
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


@register_rule(file_types=["cicd"])
class CICDSecretsInLogsRule(BaseRule):
    """CI-SEC-008: Check for potential secrets exposure in logs."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-008",
            name="Secrets in Logs",
            description="Pipeline may expose secrets in logs through echo or debug commands",
            recommendation="Mask secrets and avoid printing sensitive values:\n\n# GitHub Actions\nenv:\n  API_KEY: ${{ secrets.API_KEY }}\n# Secrets are automatically masked\n\n# Avoid: echo $PASSWORD",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "secrets", "logging", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        dangerous_patterns = [
            r'echo\s+\$[A-Z_]*(SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL)[A-Z_]*',
            r'echo\s+".*\$[A-Z_]*(SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL)',
            r'printenv\s+[A-Z_]*(SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL)',
            r'env\s*\|.*(?:secret|key|token|password)',
            r'cat\s+.*\.(env|key|pem|crt)',
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            raw_content = resource.get("raw_content", "")

            for pattern in dangerous_patterns:
                if re.search(pattern, raw_content, re.IGNORECASE):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description="Pipeline may expose secrets in logs",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                    ))
                    break

        return findings


@register_rule(file_types=["cicd"])
class CICDMissingStaticAnalysisRule(BaseRule):
    """CI-SEC-009: Check for missing static code analysis."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-009",
            name="Missing Static Code Analysis",
            description="CI/CD pipeline does not include static code analysis (linting, code quality)",
            recommendation="Add static analysis:\n\n- name: Lint\n  run: |\n    eslint .\n    pylint src/\n    golangci-lint run",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["cicd", "static-analysis", "linting", "quality"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        lint_tools = [
            # JavaScript/TypeScript
            "eslint", "tslint", "prettier --check",
            # Python
            "pylint", "flake8", "black --check", "ruff", "mypy",
            # Go
            "golangci-lint", "golint", "go vet",
            # Java
            "checkstyle", "pmd", "spotbugs",
            # General
            "sonarqube", "codeclimate", "codacy",
            # Shell
            "shellcheck",
            # Terraform
            "tflint", "terraform validate",
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps
            has_linting = False

            for step in all_steps:
                step_str = str(step).lower()
                step_run = str(step.get("run", "")).lower()
                step_name = str(step.get("name", "")).lower()

                if any(tool in step_str or tool in step_name or tool in step_run for tool in lint_tools):
                    has_linting = True
                    break

            if not has_linting:
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


@register_rule(file_types=["cicd"])
class CICDMissingInfraScanRule(BaseRule):
    """CI-SEC-010: Check for missing infrastructure scanning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-010",
            name="Missing Infrastructure Scanning",
            description="CI/CD pipeline does not scan infrastructure-as-code for security issues",
            recommendation="Add IaC scanning:\n\n- name: Scan Terraform\n  run: |\n    tfsec .\n    checkov -d .\n    terrascan scan",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "iac", "terraform", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str, has_terraform: bool = False) -> list[RuleFinding]:
        findings = []
        iac_scan_tools = [
            "tfsec", "checkov", "terrascan", "tflint",
            "terraform validate", "terraform fmt -check",
            "cfn-nag", "cfn-lint",  # CloudFormation
            "kube-score", "kube-linter", "kubeconform",  # Kubernetes
            "polaris", "datree",  # K8s
            "infracost",  # Cost + security
        ]

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            steps = properties.get("steps", [])

            all_steps = jobs + steps
            has_iac_scan = False

            for step in all_steps:
                step_str = str(step).lower()
                step_run = str(step.get("run", "")).lower()

                if any(tool in step_str or tool in step_run for tool in iac_scan_tools):
                    has_iac_scan = True
                    break

            # Only flag if there's terraform in the repo
            if not has_iac_scan and has_terraform:
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
