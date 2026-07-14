"""
DevSecOps Rules Package

Production-grade DevSecOps security scanning rules for DevArchAI.
50 rules across Docker, Kubernetes, CI/CD, and Observability.
"""

from app.rules.devsecops.cicd_security import *  # noqa: F401, F403
from app.rules.devsecops.docker_security import *  # noqa: F401, F403
from app.rules.devsecops.kubernetes_reliability import *  # noqa: F401, F403
from app.rules.devsecops.kubernetes_security import *  # noqa: F401, F403
from app.rules.devsecops.observability import *  # noqa: F401, F403

__all__ = [
    # Docker Security (10 rules)
    "DockerRootUserRule",
    "DockerLatestTagRule",
    "DockerSecretsInDockerfileRule",
    "DockerMissingUserInstructionRule",
    "DockerAddInsteadOfCopyRule",
    "DockerMissingHealthcheckRule",
    "DockerPrivilegedContainerRule",
    "DockerResourceLimitsRule",
    "DockerLargeBaseImageRule",
    "DockerSSHInstalledRule",
    # Kubernetes Security (10 rules)
    "K8sMissingNetworkPolicyRule",
    "K8sPrivilegedContainerRule",
    "K8sRunAsRootAllowedRule",
    "K8sMissingResourceLimitsRule",
    "K8sMissingLivenessProbeRule",
    "K8sMissingReadinessProbeRule",
    "K8sHostPathVolumeRule",
    "K8sPrivilegeEscalationAllowedRule",
    "K8sMissingPodSecurityContextRule",
    "K8sInsecureCapabilitiesRule",
    # Kubernetes Reliability (10 rules)
    "K8sMissingHPARule",
    "K8sMissingPDBRule",
    "K8sMissingReplicaConfigRule",
    "K8sNoRollingUpdateStrategyRule",
    "K8sMissingResourceRequestsRule",
    "K8sSingleReplicaDeploymentRule",
    "K8sMissingAntiAffinityRule",
    "K8sMissingNodeSelectorRule",
    "K8sMissingStartupProbeRule",
    "K8sMissingServiceRule",
    # CI/CD Security (10 rules)
    "CICDMissingSecurityScanRule",
    "CICDMissingDependencyScanRule",
    "CICDHardcodedSecretsRule",
    "CICDUntrustedActionsRule",
    "CICDMissingBranchProtectionRule",
    "CICDMissingContainerScanRule",
    "CICDNoArtifactSigningRule",
    "CICDSecretsInLogsRule",
    "CICDMissingStaticAnalysisRule",
    "CICDMissingInfraScanRule",
    # Observability (10 rules)
    "ObsMissingMonitoringStackRule",
    "ObsMissingMetricsEndpointRule",
    "ObsMissingLoggingRule",
    "ObsMissingTracingRule",
    "ObsMissingAlertingRule",
    "ObsMissingHealthEndpointRule",
    "ObsMissingApplicationLogsRule",
    "ObsMissingErrorTrackingRule",
    "ObsMissingSLAMonitoringRule",
    "ObsMissingPerformanceMetricsRule",
]

# Rule count by category
RULE_COUNTS = {
    "docker_security": 10,
    "kubernetes_security": 10,
    "kubernetes_reliability": 10,
    "cicd_security": 10,
    "observability": 10,
    "total": 50,
}
