"""
Production-grade CI/CD and DevOps tool rules.

Covers:
- Jenkins (Jenkinsfile, Jenkinsfile.*)
- GitLab CI (.gitlab-ci.yml)
- CircleCI (.circleci/*.yml)
- Azure DevOps (azure-pipelines.yml)
- Ansible (ansible.cfg, roles/*.yml, playbooks/*.yml)
- Helm (Chart.yaml, helmfile.yaml)
- Prometheus (prometheus.yml, prometheus.rules.yml)
- Grafana (grafana/*.yml, grafana/*.json)

Each tool has 15-25 production-grade rules covering:
- Security (secrets, credentials, access control)
- Reliability (health checks, rollback, HA)
- Performance (caching, parallelism, resource limits)
- Cost (resource optimization, retention)
- Best practices (GitOps, canary, zero-downtime)
"""

import re
from typing import Any

from app.rule_engine.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


# ============================================================================
# JENKINS RULES (20 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class JenkinsHardcodedSecretsRule(BaseRule):
    """JENKINS_001: Check for hardcoded secrets in Jenkinsfile."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_001",
            name="Hardcoded Secrets in Jenkinsfile",
            description="Hardcoded credentials or secrets detected in Jenkins pipeline",
            recommendation="Use Jenkins Credentials Binding or external secret managers (HashiCorp Vault, AWS Secrets Manager)",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["jenkins", "secrets", "security", "credentials"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            secret_patterns = [
                (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
                (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
                (r'(?i)(secret|token)\s*=\s*["\'][^"\']+["\']', "Hardcoded secret/token"),
                (r'(?i)aws_secret_access_key\s*=\s*["\'][^"\']+["\']', "Hardcoded AWS secret key"),
            ]
            for pattern, desc in secret_patterns:
                if re.search(pattern, content):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=desc,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                    ))
        return findings


@register_rule(file_types=["cicd"])
class JenkinsMissingApprovalRule(BaseRule):
    """JENKINS_002: Check for missing approval gates in production deployments."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_002",
            name="Missing Deployment Approval Gate",
            description="Production deployment pipeline lacks manual approval gate",
            recommendation="Add input step or approval gate before production deployments",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["jenkins", "approval", "deployment", "governance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'production' in content.lower() and 'input' not in content.lower() and 'approve' not in content.lower():
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
class JenkinsNoAgentLabelRule(BaseRule):
    """JENKINS_003: Check for missing agent labels."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_003",
            name="No Agent Label Specified",
            description="Pipeline runs on default agent without specific label, risking inconsistent environments",
            recommendation="Specify agent label to ensure consistent build environment",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["jenkins", "agent", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'agent' in content.lower() and 'label' not in content.lower():
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
class JenkinsMissingTimeoutRule(BaseRule):
    """JENKINS_004: Check for missing timeout in stages."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_004",
            name="Missing Stage Timeout",
            description="Pipeline stages lack timeout configuration, risking hung builds",
            recommendation="Add timeout() to all stages to prevent hung builds",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["jenkins", "timeout", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'stage' in content.lower() and 'timeout' not in content.lower():
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
class JenkinsNoRetryRule(BaseRule):
    """JENKINS_005: Check for missing retry logic."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_005",
            name="Missing Retry Logic",
            description="Pipeline lacks retry logic for flaky operations",
            recommendation="Add retry() blocks for network-dependent or flaky operations",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["jenkins", "retry", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'sh ' in content or 'bat ' in content:
                if 'retry' not in content.lower():
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
class JenkinsNoPostActionsRule(BaseRule):
    """JENKINS_006: Check for missing post-build actions."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_006",
            name="Missing Post-Build Actions",
            description="Pipeline lacks post-build notifications or cleanup",
            recommendation="Add post { always/failure/success } blocks for notifications and cleanup",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["jenkins", "post", "notifications"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'post' not in content.lower():
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
class JenkinsNoWorkspaceCleanupRule(BaseRule):
    """JENKINS_007: Check for missing workspace cleanup."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_007",
            name="Missing Workspace Cleanup",
            description="Pipeline does not clean up workspace after build",
            recommendation="Add cleanWs() in post { always { } } block",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["jenkins", "cleanup", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'cleanws' not in content.lower() and 'cleanWs' not in content:
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
class JenkinsNoParallelStagesRule(BaseRule):
    """JENKINS_008: Check for missing parallel stages."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_008",
            name="Missing Parallel Stage Execution",
            description="Pipeline runs stages sequentially instead of in parallel",
            recommendation="Use parallel { } block for independent stages to reduce build time",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["jenkins", "parallel", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'stage' in content.lower() and 'parallel' not in content.lower():
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
class JenkinsNoArtifactArchivingRule(BaseRule):
    """JENKINS_009: Check for missing artifact archiving."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_009",
            name="Missing Artifact Archiving",
            description="Pipeline does not archive build artifacts",
            recommendation="Use archiveArtifacts to preserve build outputs for debugging and auditing",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["jenkins", "artifacts", "audit"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'archiveartifacts' not in content.lower() and 'archiveArtifacts' not in content:
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
class JenkinsNoSCMCheckoutRule(BaseRule):
    """JENKINS_010: Check for missing SCM checkout."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_010",
            name="Missing SCM Checkout Configuration",
            description="Pipeline does not explicitly configure SCM checkout",
            recommendation="Use checkout scm with shallow clone for faster builds",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["jenkins", "scm", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'checkout' not in content.lower() and 'scm' not in content.lower():
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
class JenkinsNoDockerAgentRule(BaseRule):
    """JENKINS_011: Check for missing Docker agent."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_011",
            name="Not Using Docker Agent",
            description="Pipeline does not use Docker-based agent for consistent builds",
            recommendation="Use agent { docker { image '...' } } for reproducible build environments",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["jenkins", "docker", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'agent' in content.lower() and 'docker' not in content.lower():
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
class JenkinsNoCredentialsBindingRule(BaseRule):
    """JENKINS_012: Check for missing credentials binding."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_012",
            name="Missing Credentials Binding",
            description="Pipeline does not use withCredentials for sensitive operations",
            recommendation="Use withCredentials() block for all credential access",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["jenkins", "credentials", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if ('password' in content.lower() or 'secret' in content.lower()) and 'withcredentials' not in content.lower():
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
class JenkinsNoBuildDiscarderRule(BaseRule):
    """JENKINS_013: Check for missing build discard policy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_013",
            name="Missing Build Discarder Policy",
            description="Pipeline does not configure build retention, risking disk space exhaustion",
            recommendation="Add options { buildDiscarder(logRotator(...)) } to limit build history",
            severity=Severity.MEDIUM,
            category=Category.COST,
            tags=["jenkins", "retention", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'options' not in content.lower() and 'buildDiscarder' not in content:
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
class JenkinsNoTimestampsRule(BaseRule):
    """JENKINS_014: Check for missing timestamps."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_014",
            name="Missing Build Timestamps",
            description="Pipeline does not enable timestamps in console output",
            recommendation="Add options { timestamps() } for better log analysis",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["jenkins", "timestamps", "logging"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'timestamps' not in content.lower():
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
class JenkinsNoAnsiColorRule(BaseRule):
    """JENKINS_015: Check for missing ANSI color."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_015",
            name="Missing ANSI Color Output",
            description="Pipeline does not enable ANSI color for readable logs",
            recommendation="Add options { ansiColor('xterm') } for colored console output",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["jenkins", "ansi", "logging"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'ansicolor' not in content.lower():
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
class JenkinsNoTriggersRule(BaseRule):
    """JENKINS_016: Check for missing triggers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_016",
            name="Missing Pipeline Triggers",
            description="Pipeline does not configure triggers for automated builds",
            recommendation="Add triggers { pollSCM(...) } or { cron(...) } for automated builds",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["jenkins", "triggers", "automation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'triggers' not in content.lower():
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
class JenkinsNoSkipStagesRule(BaseRule):
    """JENKINS_017: Check for missing when conditions."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_017",
            name="Missing Stage Conditions",
            description="Pipeline stages lack when conditions for conditional execution",
            recommendation="Add when { } blocks to skip unnecessary stages",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["jenkins", "when", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'stage' in content.lower() and 'when' not in content.lower():
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
class JenkinsNoLibraryRule(BaseRule):
    """JENKINS_018: Check for missing shared libraries."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_018",
            name="Not Using Shared Libraries",
            description="Pipeline does not use Jenkins Shared Libraries for code reuse",
            recommendation="Use @Library('shared') for reusable pipeline code across projects",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["jenkins", "library", "reuse"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if '@library' not in content.lower() and '@Library' not in content:
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
class JenkinsNoErrorHandlingRule(BaseRule):
    """JENKINS_019: Check for missing error handling."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_019",
            name="Missing Error Handling",
            description="Pipeline lacks try/catch error handling",
            recommendation="Wrap critical operations in try/catch blocks with proper error reporting",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["jenkins", "error", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'try' not in content.lower() and 'catch' not in content.lower():
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
class JenkinsNoRollbackRule(BaseRule):
    """JENKINS_020: Check for missing rollback strategy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_020",
            name="Missing Rollback Strategy",
            description="Pipeline does not define rollback mechanism for failed deployments",
            recommendation="Add rollback stage or use rollback() in post { failure { } } block",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["jenkins", "rollback", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'deploy' in content.lower() and 'rollback' not in content.lower():
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
class JenkinsAWSStaticCredentialsRule(BaseRule):
    """JENKINS_021: Check for AWS static credentials instead of OIDC."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="JENKINS_021",
            name="AWS Static Credentials Instead of OIDC",
            description="Pipeline uses static AWS credentials (access key/secret key) instead of OIDC-based authentication",
            recommendation="Migrate to AWS OIDC authentication using IAM Roles for Service Accounts (IRSA) or AWS AssumeRoleWithWebIdentity. Avoid storing long-lived AWS credentials in Jenkins.",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["jenkins", "aws", "oidc", "credentials", "iam"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'jenkinsfile' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            # Check for AWS CLI usage (indicates static credentials are needed)
            aws_cli_patterns = [
                r'aws\s+ecr\s+get-login-password',
                r'aws\s+ecr\s+login',
                r'aws\s+s3\s+',
                r'aws\s+eks\s+',
                r'aws\s+sts\s+',
                r'aws\s+deploy\s+',
                r'aws\s+lambda\s+',
            ]
            has_aws_usage = any(re.search(p, content) for p in aws_cli_patterns)

            # Check for OIDC indicators
            oidc_indicators = [
                r'AssumeRoleWithWebIdentity',
                r'IRSA',
                r'iam\.roles\.anywhere',
                r'web-identity-token',
                r'AWS_WEB_IDENTITY_TOKEN_FILE',
            ]
            has_oidc = any(re.search(p, content) for p in oidc_indicators)

            # If AWS is used but no OIDC, flag it
            if has_aws_usage and not has_oidc:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description="AWS CLI commands detected without OIDC authentication. Pipeline likely relies on static AWS credentials (access key/secret key) configured in Jenkins.",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))
        return findings


# ============================================================================
# GITLAB CI RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class GitLabHardcodedSecretsRule(BaseRule):
    """GITLAB_001: Check for hardcoded secrets."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_001",
            name="Hardcoded Secrets in GitLab CI",
            description="Hardcoded credentials detected in .gitlab-ci.yml",
            recommendation="Use GitLab CI/CD Variables (Settings > CI/CD > Variables) for all secrets",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["gitlab", "secrets", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            secret_patterns = [
                r'(?i)(password|passwd|pwd)\s*:\s*["\']?[^\s$]+',
                r'(?i)(api_key|apikey|api_secret)\s*:\s*["\']?[^\s$]+',
                r'(?i)(secret|token)\s*:\s*["\']?[^\s$]+',
            ]
            for pattern in secret_patterns:
                if re.search(pattern, content):
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
class GitLabNoCacheRule(BaseRule):
    """GITLAB_002: Check for missing cache configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_002",
            name="Missing Cache Configuration",
            description="Pipeline does not configure caching, slowing down builds",
            recommendation="Add cache: key: and cache: paths: for dependencies",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["gitlab", "cache", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'cache:' not in content:
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
class GitLabNoArtifactExpiryRule(BaseRule):
    """GITLAB_003: Check for missing artifact expiry."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_003",
            name="Missing Artifact Expiry",
            description="Pipeline artifacts lack expiration, consuming storage",
            recommendation="Add expire_in to artifacts (e.g., expire_in: 1 week)",
            severity=Severity.MEDIUM,
            category=Category.COST,
            tags=["gitlab", "artifacts", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'artifacts:' in content and 'expire_in:' not in content:
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
class GitLabNoRulesRule(BaseRule):
    """GITLAB_004: Check for missing job rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_004",
            name="Missing Job Rules",
            description="Pipeline jobs lack rules/only/except conditions",
            recommendation="Add rules: or only: to control when jobs run",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["gitlab", "rules", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'job' in content.lower() and 'rules:' not in content and 'only:' not in content:
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
class GitLabNoRetryRule(BaseRule):
    """GITLAB_005: Check for missing retry."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_005",
            name="Missing Job Retry",
            description="Pipeline jobs lack retry configuration",
            recommendation="Add retry: max: 2 for flaky jobs",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["gitlab", "retry", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'retry:' not in content:
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
class GitLabNoTimeoutRule(BaseRule):
    """GITLAB_006: Check for missing timeout."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_006",
            name="Missing Job Timeout",
            description="Pipeline jobs lack timeout configuration",
            recommendation="Add timeout: to prevent hung jobs",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["gitlab", "timeout", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'timeout:' not in content:
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
class GitLabNoImageRule(BaseRule):
    """GITLAB_007: Check for missing Docker image."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_007",
            name="Missing Docker Image",
            description="Pipeline does not specify Docker image for jobs",
            recommendation="Add image: to ensure consistent build environment",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["gitlab", "docker", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'image:' not in content:
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
class GitLabNoServicesRule(BaseRule):
    """GITLAB_008: Check for missing services."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_008",
            name="Missing Service Dependencies",
            description="Pipeline does not define service dependencies (e.g., databases)",
            recommendation="Add services: for required dependencies like postgres, redis",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["gitlab", "services", "dependencies"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'services:' not in content:
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
class GitLabNoVariablesRule(BaseRule):
    """GITLAB_009: Check for missing variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_009",
            name="Missing Pipeline Variables",
            description="Pipeline does not define variables for configuration",
            recommendation="Add variables: block for reusable configuration",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["gitlab", "variables", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'variables:' not in content:
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
class GitLabNoIncludeRule(BaseRule):
    """GITLAB_010: Check for missing includes."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_010",
            name="Missing Pipeline Includes",
            description="Pipeline does not use include: for reusable templates",
            recommendation="Use include: to share common pipeline configurations",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["gitlab", "include", "reuse"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'include:' not in content:
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
class GitLabNoTriggerRule(BaseRule):
    """GITLAB_011: Check for missing triggers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_011",
            name="Missing Pipeline Triggers",
            description="Pipeline does not configure triggers",
            recommendation="Add rules: or only: to control pipeline execution",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["gitlab", "triggers", "automation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'trigger:' not in content and 'rules:' not in content:
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
class GitLabNoParallelRule(BaseRule):
    """GITLAB_012: Check for missing parallel execution."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_012",
            name="Missing Parallel Execution",
            description="Pipeline does not use parallel: for faster test execution",
            recommendation="Add parallel: matrix: for test parallelization",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["gitlab", "parallel", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'parallel:' not in content:
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
class GitLabNoNeedsRule(BaseRule):
    """GITLAB_013: Check for missing needs."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_013",
            name="Missing DAG Dependencies",
            description="Pipeline does not use needs: for DAG-based execution",
            recommendation="Add needs: to enable DAG-based job execution",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["gitlab", "needs", "dag"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'needs:' not in content:
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
class GitLabNoInterruptibleRule(BaseRule):
    """GITLAB_014: Check for missing interruptible."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_014",
            name="Missing Interruptible Jobs",
            description="Pipeline jobs are not marked as interruptible",
            recommendation="Add interruptible: true to allow pipeline cancellation",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["gitlab", "interruptible", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'interruptible:' not in content:
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
class GitLabNoResourceGroupRule(BaseRule):
    """GITLAB_015: Check for missing resource groups."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GITLAB_015",
            name="Missing Resource Groups",
            description="Pipeline does not use resource_group for deployment safety",
            recommendation="Add resource_group: to prevent concurrent deployments",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["gitlab", "resource_group", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.gitlab-ci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'deploy' in content.lower() and 'resource_group:' not in content:
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


# ============================================================================
# CIRCLECI RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class CircleCINoExecutorRule(BaseRule):
    """CIRCLECI_001: Check for missing executors."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_001",
            name="Missing Executor Definition",
            description="Pipeline does not define reusable executors",
            recommendation="Define executors: for consistent job environments",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["circleci", "executor", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'executors:' not in content and 'docker:' not in content:
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
class CircleCINoOrbsRule(BaseRule):
    """CIRCLECI_002: Check for missing orbs."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_002",
            name="Missing Orb Usage",
            description="Pipeline does not use CircleCI orbs for reusable functionality",
            recommendation="Use orbs: for common tasks like docker, aws, kubernetes",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["circleci", "orbs", "reuse"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'orbs:' not in content:
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
class CircleCINoWorkflowRule(BaseRule):
    """CIRCLECI_003: Check for missing workflows."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_003",
            name="Missing Workflow Definition",
            description="Pipeline does not define workflows for job orchestration",
            recommendation="Add workflows: to define job execution order",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["circleci", "workflows", "orchestration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'workflows:' not in content:
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
class CircleCINoContextRule(BaseRule):
    """CIRCLECI_004: Check for missing contexts."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_004",
            name="Missing Context Usage",
            description="Pipeline does not use CircleCI contexts for environment variables",
            recommendation="Use context: to share environment variables across jobs",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["circleci", "context", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'context:' not in content:
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
class CircleCINoFiltersRule(BaseRule):
    """CIRCLECI_005: Check for missing filters."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_005",
            name="Missing Branch Filters",
            description="Pipeline jobs lack branch filters",
            recommendation="Add filters: branches: to control job execution",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["circleci", "filters", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'filters:' not in content:
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
class CircleCINoResourceClassRule(BaseRule):
    """CIRCLECI_006: Check for missing resource class."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_006",
            name="Missing Resource Class",
            description="Pipeline does not specify resource_class for jobs",
            recommendation="Add resource_class: to control compute resources",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["circleci", "resource_class", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'resource_class:' not in content:
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
class CircleCINoParallelismRule(BaseRule):
    """CIRCLECI_007: Check for missing parallelism."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_007",
            name="Missing Test Parallelism",
            description="Pipeline does not use parallelism for test execution",
            recommendation="Add parallelism: to split tests across containers",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["circleci", "parallelism", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'parallelism:' not in content:
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
class CircleCINoWorkspaceRule(BaseRule):
    """CIRCLECI_008: Check for missing workspaces."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_008",
            name="Missing Workspace Usage",
            description="Pipeline does not use workspaces for artifact sharing",
            recommendation="Use persist_to_workspace: and attach_workspace: for job communication",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["circleci", "workspace", "artifacts"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'workspace' not in content.lower():
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
class CircleCINoApprovalRule(BaseRule):
    """CIRCLECI_009: Check for missing approval."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_009",
            name="Missing Deployment Approval",
            description="Production deployment lacks manual approval step",
            recommendation="Add type: approval to deployment jobs",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["circleci", "approval", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'deploy' in content.lower() and 'type: approval' not in content:
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
class CircleCINoSSHRule(BaseRule):
    """CIRCLECI_010: Check for SSH in production."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_010",
            name="SSH Enabled in Production",
            description="Pipeline has SSH enabled, posing security risk",
            recommendation="Remove ssh: true from production workflows",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["circleci", "ssh", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'ssh: true' in content or 'ssh:True' in content:
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
class CircleCINoStoreArtifactsRule(BaseRule):
    """CIRCLECI_011: Check for missing artifact storage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_011",
            name="Missing Artifact Storage",
            description="Pipeline does not store build artifacts",
            recommendation="Add store_artifacts: to preserve build outputs",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["circleci", "artifacts", "storage"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'store_artifacts:' not in content:
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
class CircleCINoSaveCacheRule(BaseRule):
    """CIRCLECI_012: Check for missing cache save."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_012",
            name="Missing Cache Save",
            description="Pipeline does not save caches between runs",
            recommendation="Add save_cache: to speed up subsequent builds",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["circleci", "cache", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'save_cache:' not in content:
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
class CircleCINoRestoreCacheRule(BaseRule):
    """CIRCLECI_013: Check for missing cache restore."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_013",
            name="Missing Cache Restore",
            description="Pipeline does not restore caches",
            recommendation="Add restore_cache: to reuse dependencies",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["circleci", "cache", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'restore_cache:' not in content:
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
class CircleCINoTimeoutRule(BaseRule):
    """CIRCLECI_014: Check for missing timeout."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_014",
            name="Missing Step Timeout",
            description="Pipeline steps lack timeout configuration",
            recommendation="Add no_output_timeout: to prevent hung steps",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["circleci", "timeout", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'no_output_timeout:' not in content:
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
class CircleCINoWhenRule(BaseRule):
    """CIRCLECI_015: Check for missing when conditions."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CIRCLECI_015",
            name="Missing When Conditions",
            description="Pipeline jobs lack when conditions for conditional execution",
            recommendation="Add when: to skip unnecessary jobs",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["circleci", "when", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and '.circleci' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'when:' not in content:
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


# ============================================================================
# AZURE DEVOPS RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class AzureNoPoolRule(BaseRule):
    """AZURE_001: Check for missing pool specification."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_001",
            name="Missing Agent Pool Specification",
            description="Pipeline does not specify agent pool",
            recommendation="Add pool: to control which agents run the pipeline",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "pool", "agents"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'pool:' not in content:
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
class AzureNoTriggerRule(BaseRule):
    """AZURE_002: Check for missing triggers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_002",
            name="Missing Pipeline Triggers",
            description="Pipeline does not define triggers",
            recommendation="Add trigger: to control pipeline execution",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "trigger", "automation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'trigger:' not in content:
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
class AzureNoVariablesRule(BaseRule):
    """AZURE_003: Check for missing variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_003",
            name="Missing Pipeline Variables",
            description="Pipeline does not define variables",
            recommendation="Add variables: for reusable configuration",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["azure", "variables", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'variables:' not in content:
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
class AzureNoStagesRule(BaseRule):
    """AZURE_004: Check for missing stages."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_004",
            name="Missing Stage Organization",
            description="Pipeline does not use stages for organization",
            recommendation="Add stages: to organize pipeline into logical phases",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "stages", "organization"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'stages:' not in content:
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
class AzureNoConditionsRule(BaseRule):
    """AZURE_005: Check for missing conditions."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_005",
            name="Missing Stage/Job Conditions",
            description="Pipeline stages/jobs lack conditions",
            recommendation="Add condition: to control stage/job execution",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["azure", "condition", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'condition:' not in content:
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
class AzureNoApprovalRule(BaseRule):
    """AZURE_006: Check for missing approvals."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_006",
            name="Missing Deployment Approval",
            description="Production deployment lacks approval check",
            recommendation="Add approval check in environment settings",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["azure", "approval", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'deploy' in content.lower() and 'environment:' not in content:
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
class AzureNoTimeoutRule(BaseRule):
    """AZURE_007: Check for missing timeout."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_007",
            name="Missing Timeout",
            description="Pipeline lacks timeout configuration",
            recommendation="Add timeoutInMinutes: to prevent hung pipelines",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "timeout", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'timeoutInMinutes:' not in content:
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
class AzureNoStrategyRule(BaseRule):
    """AZURE_008: Check for missing deployment strategy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_008",
            name="Missing Deployment Strategy",
            description="Pipeline does not define deployment strategy",
            recommendation="Add strategy: (canary, blue-green, rolling) for safe deployments",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["azure", "strategy", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'deploy' in content.lower() and 'strategy:' not in content:
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
class AzureNoCacheRule(BaseRule):
    """AZURE_009: Check for missing cache."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_009",
            name="Missing Cache Task",
            description="Pipeline does not use Cache@2 task",
            recommendation="Add Cache@2 task to speed up builds",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["azure", "cache", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'Cache@2' not in content and 'cache' not in content.lower():
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
class AzureNoPublishRule(BaseRule):
    """AZURE_010: Check for missing publish."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_010",
            name="Missing Artifact Publish",
            description="Pipeline does not publish build artifacts",
            recommendation="Add PublishPipelineArtifact@1 to preserve build outputs",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "publish", "artifacts"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'PublishPipelineArtifact' not in content:
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
class AzureNoDownloadRule(BaseRule):
    """AZURE_011: Check for missing download."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_011",
            name="Missing Artifact Download",
            description="Pipeline does not download artifacts from previous stages",
            recommendation="Add DownloadPipelineArtifact@2 to retrieve build outputs",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "download", "artifacts"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'DownloadPipelineArtifact' not in content:
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
class AzureNoTemplateRule(BaseRule):
    """AZURE_012: Check for missing templates."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_012",
            name="Missing Template Usage",
            description="Pipeline does not use templates for reusability",
            recommendation="Use template: references for reusable pipeline code",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["azure", "template", "reuse"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'template:' not in content and '- template:' not in content:
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
class AzureNoEnvironmentRule(BaseRule):
    """AZURE_013: Check for missing environments."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_013",
            name="Missing Environment Definition",
            description="Pipeline does not define environments for deployment tracking",
            recommendation="Add environment: to enable deployment tracking and approvals",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["azure", "environment", "tracking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'deploy' in content.lower() and 'environment:' not in content:
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
class AzureNoVariablesGroupRule(BaseRule):
    """AZURE_014: Check for missing variable groups."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_014",
            name="Missing Variable Groups",
            description="Pipeline does not use variable groups for configuration",
            recommendation="Add variable groups for centralized configuration management",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["azure", "variables", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'group:' not in content:
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
class AzureNoRetryRule(BaseRule):
    """AZURE_015: Check for missing retry."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="AZURE_015",
            name="Missing Retry Configuration",
            description="Pipeline tasks lack retry configuration",
            recommendation="Add retryCountOnTaskFailure: for resilient pipelines",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["azure", "retry", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'azure-pipelines' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'retryCountOnTaskFailure' not in content:
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


# ============================================================================
# ANSIBLE RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class AnsibleNoBecomeRule(BaseRule):
    """ANSIBLE_001: Check for missing become."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_001",
            name="Missing Privilege Escalation",
            description="Playbook lacks become configuration for privilege escalation",
            recommendation="Add become: yes for tasks requiring root privileges",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["ansible", "become", "privilege"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'become:' not in content and 'sudo:' not in content:
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
class AnsibleNoHandlerRule(BaseRule):
    """ANSIBLE_002: Check for missing handlers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_002",
            name="Missing Handlers",
            description="Playbook does not define handlers for service restarts",
            recommendation="Add handlers: to restart services only when config changes",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["ansible", "handlers", "services"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'notify:' in content and 'handlers:' not in content:
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
class AnsibleNoTagsRule(BaseRule):
    """ANSIBLE_003: Check for missing tags."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_003",
            name="Missing Task Tags",
            description="Playbook tasks lack tags for selective execution",
            recommendation="Add tags: to enable selective task execution with --tags",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "tags", "execution"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'tags:' not in content:
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
class AnsibleNoVarsRule(BaseRule):
    """ANSIBLE_004: Check for missing variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_004",
            name="Missing Variables",
            description="Playbook does not define variables",
            recommendation="Add vars: or use external variable files for configuration",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "variables", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'vars:' not in content and 'vars_files:' not in content:
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
class AnsibleNoRolesRule(BaseRule):
    """ANSIBLE_005: Check for missing roles."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_005",
            name="Missing Role Usage",
            description="Playbook does not use roles for organization",
            recommendation="Use roles: to organize and reuse Ansible code",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "roles", "organization"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'roles:' not in content:
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
class AnsibleNoCheckModeRule(BaseRule):
    """ANSIBLE_006: Check for missing check mode support."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_006",
            name="Missing Check Mode Support",
            description="Playbook may not support --check mode for dry runs",
            recommendation="Ensure all tasks support check_mode: yes for safe testing",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "check", "testing"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'check_mode' not in content and 'ansible_check_mode' not in content:
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
class AnsibleNoDiffRule(BaseRule):
    """ANSIBLE_007: Check for missing diff mode."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_007",
            name="Missing Diff Mode",
            description="Playbook does not enable diff mode for change visibility",
            recommendation="Add diff: yes to see what changes will be made",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "diff", "visibility"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'diff:' not in content:
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
class AnsibleNoSerialRule(BaseRule):
    """ANSIBLE_008: Check for missing serial execution."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_008",
            name="Missing Serial Execution",
            description="Playbook does not limit parallel execution on hosts",
            recommendation="Add serial: to control rolling updates",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["ansible", "serial", "rolling"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'hosts:' in content and 'serial:' not in content:
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
class AnsibleNoGatherFactsRule(BaseRule):
    """ANSIBLE_009: Check for missing gather_facts."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_009",
            name="Missing Facts Gathering Control",
            description="Playbook does not control facts gathering",
            recommendation="Add gather_facts: no if facts are not needed to speed up execution",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["ansible", "facts", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'gather_facts:' not in content:
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
class AnsibleNoIgnoreErrorsRule(BaseRule):
    """ANSIBLE_010: Check for ignore_errors."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_010",
            name="Ignoring Task Errors",
            description="Playbook uses ignore_errors which can mask failures",
            recommendation="Use failed_when: instead of ignore_errors: for proper error handling",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["ansible", "ignore_errors", "error"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'ignore_errors:' in content:
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
class AnsibleNoChangedWhenRule(BaseRule):
    """ANSIBLE_011: Check for missing changed_when."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_011",
            name="Missing Changed When",
            description="Playbook tasks lack changed_when for accurate reporting",
            recommendation="Add changed_when: to control when tasks report changes",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "changed", "reporting"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'changed_when:' not in content:
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
class AnsibleNoFailedWhenRule(BaseRule):
    """ANSIBLE_012: Check for missing failed_when."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_012",
            name="Missing Failed When",
            description="Playbook tasks lack failed_when for custom failure conditions",
            recommendation="Add failed_when: to define custom failure conditions",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["ansible", "failed", "error"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'failed_when:' not in content:
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
class AnsibleNoLoopRule(BaseRule):
    """ANSIBLE_013: Check for missing loops."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_013",
            name="Missing Loop Usage",
            description="Playbook does not use loops for repetitive tasks",
            recommendation="Use loop: or with_items: for repetitive tasks",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["ansible", "loop", "efficiency"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'loop:' not in content and 'with_items:' not in content:
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
class AnsibleNoBlockRule(BaseRule):
    """ANSIBLE_014: Check for missing blocks."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_014",
            name="Missing Block Usage",
            description="Playbook does not use blocks for task grouping",
            recommendation="Use block: with rescue: and always: for error handling",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["ansible", "block", "error"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'block:' not in content:
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
class AnsibleNoVaultRule(BaseRule):
    """ANSIBLE_015: Check for missing vault."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="ANSIBLE_015",
            name="Missing Ansible Vault",
            description="Playbook may contain sensitive data without encryption",
            recommendation="Use ansible-vault to encrypt sensitive variables",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["ansible", "vault", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('ansible' in file_path.lower() or file_path.endswith('.yml') or file_path.endswith('.yaml')):
            content = resources[0].get("raw_content", "") if resources else ""
            secret_patterns = [
                r'(?i)(password|passwd|pwd)\s*:\s*["\']?[^\s$]+',
                r'(?i)(secret|token)\s*:\s*["\']?[^\s$]+',
            ]
            for pattern in secret_patterns:
                if re.search(pattern, content):
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


# ============================================================================
# HELM RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class HelmNoReplicasRule(BaseRule):
    """HELM_001: Check for missing replicas."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_001",
            name="Missing Replica Count",
            description="Chart does not define replica count for high availability",
            recommendation="Add replicaCount: to values.yaml for HA configuration",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "replicas", "ha"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'replicaCount' not in content and 'replicas' not in content:
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
class HelmNoResourcesRule(BaseRule):
    """HELM_002: Check for missing resources."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_002",
            name="Missing Resource Limits",
            description="Chart does not define resource limits/requests",
            recommendation="Add resources: with limits and requests in values.yaml",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "resources", "limits"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'resources:' not in content:
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
class HelmNoLivenessRule(BaseRule):
    """HELM_003: Check for missing liveness probe."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_003",
            name="Missing Liveness Probe",
            description="Chart does not define liveness probe",
            recommendation="Add livenessProbe: to detect and restart unhealthy containers",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "liveness", "health"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'livenessProbe' not in content:
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
class HelmNoReadinessRule(BaseRule):
    """HELM_004: Check for missing readiness probe."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_004",
            name="Missing Readiness Probe",
            description="Chart does not define readiness probe",
            recommendation="Add readinessProbe: to control traffic routing",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "readiness", "traffic"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'readinessProbe' not in content:
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
class HelmNoImageTagRule(BaseRule):
    """HELM_005: Check for missing image tag."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_005",
            name="Missing Image Tag",
            description="Chart uses latest or missing image tag",
            recommendation="Pin image.tag to specific version for reproducible deployments",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "image", "version"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'image:' in content and ('latest' in content or 'tag:' not in content):
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
class HelmNoServiceRule(BaseRule):
    """HELM_006: Check for missing service."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_006",
            name="Missing Service Definition",
            description="Chart does not define Kubernetes Service",
            recommendation="Add service: template for network access",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["helm", "service", "network"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'Service' not in content and 'service:' not in content:
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
class HelmNoIngressRule(BaseRule):
    """HELM_007: Check for missing ingress."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_007",
            name="Missing Ingress Configuration",
            description="Chart does not define Ingress for external access",
            recommendation="Add ingress: template for HTTP/HTTPS routing",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["helm", "ingress", "routing"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'Ingress' not in content and 'ingress:' not in content:
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
class HelmNoConfigMapRule(BaseRule):
    """HELM_008: Check for missing ConfigMap."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_008",
            name="Missing ConfigMap Usage",
            description="Chart does not use ConfigMaps for configuration",
            recommendation="Use ConfigMap: for externalized configuration",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["helm", "configmap", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'ConfigMap' not in content and 'configMap' not in content:
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
class HelmNoSecretRule(BaseRule):
    """HELM_009: Check for missing secret management."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_009",
            name="Missing Secret Management",
            description="Chart does not use Kubernetes Secrets properly",
            recommendation="Use Secret: with external secret manager (Vault, Sealed Secrets)",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["helm", "secret", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'Secret' not in content and 'secret:' not in content:
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
class HelmNoPDBRule(BaseRule):
    """HELM_010: Check for missing PDB."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_010",
            name="Missing Pod Disruption Budget",
            description="Chart does not define PDB for high availability",
            recommendation="Add PodDisruptionBudget: to ensure minimum available pods",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "pdb", "ha"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'PodDisruptionBudget' not in content and 'pdb' not in content.lower():
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
class HelmNoHPARule(BaseRule):
    """HELM_011: Check for missing HPA."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_011",
            name="Missing Horizontal Pod Autoscaler",
            description="Chart does not define HPA for automatic scaling",
            recommendation="Add HorizontalPodAutoscaler: for automatic scaling",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["helm", "hpa", "scaling"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'HorizontalPodAutoscaler' not in content and 'hpa' not in content.lower():
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
class HelmNoRollingRule(BaseRule):
    """HELM_012: Check for missing rolling update strategy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_012",
            name="Missing Rolling Update Strategy",
            description="Chart does not define rolling update strategy",
            recommendation="Add strategy: rollingUpdate: for zero-downtime deployments",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["helm", "rolling", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'rollingUpdate' not in content and 'strategy:' not in content:
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
class HelmNoNotesRule(BaseRule):
    """HELM_013: Check for missing NOTES.txt."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_013",
            name="Missing NOTES.txt",
            description="Chart does not include NOTES.txt for post-install instructions",
            recommendation="Add NOTES.txt template with usage instructions",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["helm", "notes", "documentation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'NOTES' not in content:
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
class HelmNoTestRule(BaseRule):
    """HELM_014: Check for missing tests."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_014",
            name="Missing Chart Tests",
            description="Chart does not include test templates",
            recommendation="Add tests/ directory with helm test templates",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["helm", "tests", "quality"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'test' not in content.lower():
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
class HelmNoVersionRule(BaseRule):
    """HELM_015: Check for missing version."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="HELM_015",
            name="Missing Chart Version",
            description="Chart does not define version in Chart.yaml",
            recommendation="Add version: and appVersion: to Chart.yaml",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["helm", "version", "chart"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and ('helm' in file_path.lower() or 'chart.yaml' in file_path.lower()):
            content = resources[0].get("raw_content", "") if resources else ""
            if 'version:' not in content:
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


# ============================================================================
# PROMETHEUS RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class PrometheusNoAlertsRule(BaseRule):
    """PROMETHEUS_001: Check for missing alerting rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_001",
            name="Missing Alerting Rules",
            description="Prometheus configuration lacks alerting rules",
            recommendation="Add alerting rules for critical metrics (CPU, memory, disk, errors)",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["prometheus", "alerting", "monitoring"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'groups:' not in content and 'alert' not in content.lower():
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
class PrometheusNoRecordingRule(BaseRule):
    """PROMETHEUS_002: Check for missing recording rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_002",
            name="Missing Recording Rules",
            description="Prometheus configuration lacks recording rules",
            recommendation="Add recording rules for expensive queries",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["prometheus", "recording", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'record:' not in content:
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
class PrometheusNoRetentionRule(BaseRule):
    """PROMETHEUS_003: Check for missing retention."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_003",
            name="Missing Data Retention",
            description="Prometheus configuration lacks retention settings",
            recommendation="Add --storage.tsdb.retention.time and --storage.tsdb.retention.size",
            severity=Severity.MEDIUM,
            category=Category.COST,
            tags=["prometheus", "retention", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'retention' not in content.lower():
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
class PrometheusNoScrapeRule(BaseRule):
    """PROMETHEUS_004: Check for missing scrape configs."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_004",
            name="Missing Scrape Configurations",
            description="Prometheus configuration lacks scrape_configs",
            recommendation="Add scrape_configs: with job definitions for all targets",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["prometheus", "scrape", "targets"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'scrape_configs:' not in content:
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
class PrometheusNoTLSRule(BaseRule):
    """PROMETHEUS_005: Check for missing TLS."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_005",
            name="Missing TLS Configuration",
            description="Prometheus scrape configs lack TLS settings",
            recommendation="Add scheme: https and tls_config: for secure scraping",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["prometheus", "tls", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'scrape_configs:' in content and 'tls_config:' not in content:
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
class PrometheusNoAuthRule(BaseRule):
    """PROMETHEUS_006: Check for missing authentication."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_006",
            name="Missing Authentication",
            description="Prometheus scrape configs lack authentication",
            recommendation="Add basic_auth: or bearer_token_file: for secure access",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["prometheus", "auth", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'scrape_configs:' in content and 'basic_auth:' not in content and 'bearer_token' not in content:
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
class PrometheusNoRelabelRule(BaseRule):
    """PROMETHEUS_007: Check for missing relabeling."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_007",
            name="Missing Relabeling Configuration",
            description="Prometheus lacks relabeling for metric filtering",
            recommendation="Add metric_relabel_configs: to filter unwanted metrics",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["prometheus", "relabel", "filtering"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'metric_relabel_configs:' not in content:
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
class PrometheusNoFederationRule(BaseRule):
    """PROMETHEUS_008: Check for missing federation."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_008",
            name="Missing Federation",
            description="Prometheus lacks federation for multi-cluster setups",
            recommendation="Add honor_labels: true and federation scrape jobs",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["prometheus", "federation", "scalability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'honor_labels:' not in content:
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
class PrometheusNoRemoteRule(BaseRule):
    """PROMETHEUS_009: Check for missing remote storage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_009",
            name="Missing Remote Storage",
            description="Prometheus lacks remote write for long-term storage",
            recommendation="Add remote_write: for Thanos, Cortex, or VictoriaMetrics",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["prometheus", "remote", "storage"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'remote_write:' not in content:
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
class PrometheusNoServiceMonitorRule(BaseRule):
    """PROMETHEUS_010: Check for missing ServiceMonitor."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_010",
            name="Missing ServiceMonitor",
            description="Prometheus Operator lacks ServiceMonitor resources",
            recommendation="Add ServiceMonitor: CRDs for automatic target discovery",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["prometheus", "servicemonitor", "operator"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'ServiceMonitor' not in content:
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
class PrometheusNoPodMonitorRule(BaseRule):
    """PROMETHEUS_011: Check for missing PodMonitor."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_011",
            name="Missing PodMonitor",
            description="Prometheus Operator lacks PodMonitor resources",
            recommendation="Add PodMonitor: CRDs for pod-level metrics",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["prometheus", "podmonitor", "operator"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'PodMonitor' not in content:
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
class PrometheusNoRuleFileRule(BaseRule):
    """PROMETHEUS_012: Check for missing rule files."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_012",
            name="Missing Rule Files",
            description="Prometheus configuration lacks rule_files",
            recommendation="Add rule_files: for alerting and recording rules",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["prometheus", "rules", "files"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'rule_files:' not in content:
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
class PrometheusNoGlobalRule(BaseRule):
    """PROMETHEUS_013: Check for missing global config."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_013",
            name="Missing Global Configuration",
            description="Prometheus configuration lacks global settings",
            recommendation="Add global: with scrape_interval and evaluation_interval",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["prometheus", "global", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'global:' not in content:
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
class PrometheusNoExternalLabelsRule(BaseRule):
    """PROMETHEUS_014: Check for missing external labels."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_014",
            name="Missing External Labels",
            description="Prometheus lacks external labels for federation",
            recommendation="Add external_labels: with cluster and environment identifiers",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["prometheus", "labels", "federation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'external_labels:' not in content:
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
class PrometheusNoAlertManagerRule(BaseRule):
    """PROMETHEUS_015: Check for missing Alertmanager."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="PROMETHEUS_015",
            name="Missing Alertmanager Configuration",
            description="Prometheus lacks Alertmanager configuration",
            recommendation="Add alerting: with alertmanagers: for alert routing",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["prometheus", "alertmanager", "alerting"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'prometheus' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'alerting:' not in content and 'alertmanager' not in content.lower():
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


# ============================================================================
# GRAFANA RULES (15 rules)
# ============================================================================

@register_rule(file_types=["cicd"])
class GrafanaNoDatasourceRule(BaseRule):
    """GRAFANA_001: Check for missing datasource."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_001",
            name="Missing Datasource Configuration",
            description="Grafana configuration lacks datasource definitions",
            recommendation="Add datasources: with Prometheus, Loki, Tempo, etc.",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["grafana", "datasource", "configuration"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'datasources' not in content.lower():
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
class GrafanaNoDashboardRule(BaseRule):
    """GRAFANA_002: Check for missing dashboards."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_002",
            name="Missing Dashboard Provisioning",
            description="Grafana lacks dashboard provisioning configuration",
            recommendation="Add dashboard provisioning with configMaps or folders",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["grafana", "dashboard", "provisioning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'dashboard' not in content.lower():
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
class GrafanaNoAuthRule(BaseRule):
    """GRAFANA_003: Check for missing auth."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_003",
            name="Missing Authentication",
            description="Grafana configuration lacks authentication settings",
            recommendation="Configure auth.proxy, OAuth, or LDAP for secure access",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["grafana", "auth", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'auth' not in content.lower():
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
class GrafanaNoAlertingRule(BaseRule):
    """GRAFANA_004: Check for missing alerting."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_004",
            name="Missing Alerting Configuration",
            description="Grafana lacks alerting notification channels",
            recommendation="Add alerting notification channels (Slack, PagerDuty, Email)",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["grafana", "alerting", "notifications"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'alerting' not in content.lower() and 'notification' not in content.lower():
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
class GrafanaNoPluginsRule(BaseRule):
    """GRAFANA_005: Check for missing plugins."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_005",
            name="Missing Plugin Configuration",
            description="Grafana lacks plugin provisioning",
            recommendation="Add plugins: for extended functionality",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["grafana", "plugins", "functionality"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'plugins' not in content.lower():
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
class GrafanaNoSecurityRule(BaseRule):
    """GRAFANA_006: Check for missing security."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_006",
            name="Missing Security Settings",
            description="Grafana lacks security hardening",
            recommendation="Configure cookie_secure, allow_embedding, and disable signup",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["grafana", "security", "hardening"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'cookie_secure' not in content and 'allow_embedding' not in content:
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
class GrafanaNoLoggingRule(BaseRule):
    """GRAFANA_007: Check for missing logging."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_007",
            name="Missing Logging Configuration",
            description="Grafana lacks logging configuration",
            recommendation="Configure log mode, level, and format for observability",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["grafana", "logging", "observability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'log' not in content.lower():
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
class GrafanaNoBackupRule(BaseRule):
    """GRAFANA_008: Check for missing backup."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_008",
            name="Missing Backup Strategy",
            description="Grafana lacks backup configuration",
            recommendation="Configure database backup for Grafana dashboards and settings",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["grafana", "backup", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'backup' not in content.lower():
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
class GrafanaNoRBACRule(BaseRule):
    """GRAFANA_009: Check for missing RBAC."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_009",
            name="Missing Role-Based Access Control",
            description="Grafana lacks RBAC configuration",
            recommendation="Configure org roles and folder permissions",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["grafana", "rbac", "access"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'role' not in content.lower():
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
class GrafanaNoSnapshotsRule(BaseRule):
    """GRAFANA_010: Check for missing snapshots."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_010",
            name="Missing Snapshot Configuration",
            description="Grafana lacks snapshot settings",
            recommendation="Configure snapshot_enabled and external snapshot URL",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["grafana", "snapshots", "sharing"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'snapshot' not in content.lower():
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
class GrafanaNoSMTPRule(BaseRule):
    """GRAFANA_011: Check for missing SMTP."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_011",
            name="Missing SMTP Configuration",
            description="Grafana lacks SMTP for email notifications",
            recommendation="Configure SMTP settings for email alerts",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["grafana", "smtp", "email"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'smtp' not in content.lower():
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
class GrafanaNoProxyRule(BaseRule):
    """GRAFANA_012: Check for missing proxy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_012",
            name="Missing Reverse Proxy Configuration",
            description="Grafana lacks reverse proxy settings",
            recommendation="Configure root_url and serve_from_sub_path for reverse proxy",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["grafana", "proxy", "networking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'root_url' not in content and 'serve_from_sub_path' not in content:
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
class GrafanaNoAnalyticsRule(BaseRule):
    """GRAFANA_013: Check for missing analytics."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_013",
            name="Missing Analytics Configuration",
            description="Grafana lacks analytics reporting settings",
            recommendation="Configure reporting_enabled for usage analytics",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["grafana", "analytics", "reporting"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'reporting' not in content.lower():
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
class GrafanaNoUnifiedAlertingRule(BaseRule):
    """GRAFANA_014: Check for missing unified alerting."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_014",
            name="Missing Unified Alerting",
            description="Grafana lacks unified alerting configuration",
            recommendation="Enable unified_alerting for modern alerting features",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["grafana", "alerting", "modern"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'unified_alerting' not in content:
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
class GrafanaNoPublicDashboardsRule(BaseRule):
    """GRAFANA_015: Check for missing public dashboard settings."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="GRAFANA_015",
            name="Missing Public Dashboard Configuration",
            description="Grafana lacks public dashboard settings",
            recommendation="Configure public_dashboards settings for secure sharing",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["grafana", "public", "sharing"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        if file_path and 'grafana' in file_path.lower():
            content = resources[0].get("raw_content", "") if resources else ""
            if 'public' not in content.lower():
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
