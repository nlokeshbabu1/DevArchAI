"""DevOps Documentation Mapping Service.

Provides context-specific documentation URLs for each rule based on technology type.
All links point to official vendor documentation.
"""



class DevOpsDocumentation:
    """Maps rule IDs to official vendor documentation URLs."""

    # Base documentation URLs
    KUBERNETES_DOCS = "https://kubernetes.io/docs"
    DOCKER_DOCS = "https://docs.docker.com"
    TERRAFORM_DOCS = "https://developer.hashicorp.com/terraform"
    GITHUB_ACTIONS_DOCS = "https://docs.github.com/en/actions"
    GITLAB_CI_DOCS = "https://docs.gitlab.com/ee/ci"
    JENKINS_DOCS = "https://www.jenkins.io/doc"
    HELM_DOCS = "https://helm.sh/docs"
    PROMETHEUS_DOCS = "https://prometheus.io/docs"
    GRAFANA_DOCS = "https://grafana.com/docs"

    @classmethod
    def get_documentation_url(cls, rule_id: str, file_type: str | None = None) -> str | None:
        """
        Get official documentation URL for a specific rule.

        Args:
            rule_id: The rule identifier (e.g., 'K8S-SEC-001')
            file_type: Optional file type hint for disambiguation

        Returns:
            Official documentation URL or None if not found
        """
        # Kubernetes rules
        if rule_id.startswith('K8S-'):
            return cls._get_kubernetes_doc_url(rule_id)

        # Docker rules
        if rule_id.startswith('DKR-') or rule_id.startswith('DOCKER-'):
            return cls._get_docker_doc_url(rule_id)

        # Terraform rules
        if rule_id.startswith('TF-'):
            return cls._get_terraform_doc_url(rule_id)

        # CI/CD rules
        if rule_id.startswith('CI-'):
            return cls._get_cicd_doc_url(rule_id)

        # Helm rules
        if rule_id.startswith('HELM-'):
            return cls._get_helm_doc_url(rule_id)

        # Monitoring rules
        if rule_id.startswith('MON-') or rule_id.startswith('PROMETHEUS-'):
            return cls._get_monitoring_doc_url(rule_id)

        return None

    @classmethod
    def _get_kubernetes_doc_url(cls, rule_id: str) -> str:
        """Get Kubernetes-specific documentation URL."""
        k8s_docs = {
            # YAML-based rules (K8S-001 to K8S-012)
            'K8S-001': f'{cls.KUBERNETES_DOCS}/concepts/configuration/manage-resources-containers/',
            'K8S-002': f'{cls.KUBERNETES_DOCS}/concepts/scheduling-eviction/pod-priority-preemption/',
            'K8S-003': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/',
            'K8S-004': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/',
            'K8S-005': f'{cls.KUBERNETES_DOCS}/concepts/security/pod-security-standards/',
            'K8S-006': f'{cls.KUBERNETES_DOCS}/concepts/security/pod-security-standards/',
            'K8S-007': f'{cls.KUBERNETES_DOCS}/concepts/containers/images/',
            'K8S-008': f'{cls.KUBERNETES_DOCS}/concepts/storage/volumes/#hostpath',
            'K8S-009': f'{cls.KUBERNETES_DOCS}/tasks/run-application/horizontal-pod-autoscale/',
            'K8S-010': f'{cls.KUBERNETES_DOCS}/concepts/services-networking/network-policies/',
            'K8S-011': f'{cls.KUBERNETES_DOCS}/concepts/containers/images/',
            'K8S-012': f'{cls.KUBERNETES_DOCS}/concepts/configuration/secret/',

            # Security rules (K8S-SEC-*)
            'K8S-SEC-001': f'{cls.KUBERNETES_DOCS}/concepts/security/pod-security-policy/',
            'K8S-SEC-002': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/security-context/',
            'K8S-SEC-003': f'{cls.KUBERNETES_DOCS}/concepts/security/pod-security-standards/',
            'K8S-SEC-004': f'{cls.KUBERNETES_DOCS}/concepts/security/network-policies/',
            'K8S-SEC-005': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/configure-service-account/',
            'K8S-SEC-006': f'{cls.KUBERNETES_DOCS}/concepts/security/secrets/',
            'K8S-SEC-007': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/security-context/',
            'K8S-SEC-008': f'{cls.KUBERNETES_DOCS}/concepts/security/pod-security-standards/',
            'K8S-SEC-009': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/',
            'K8S-SEC-010': f'{cls.KUBERNETES_DOCS}/concepts/security/network-policies/',

            # Reliability rules (K8S-REL-*)
            'K8S-REL-001': f'{cls.KUBERNETES_DOCS}/concepts/workloads/controllers/replicaset/',
            'K8S-REL-002': f'{cls.KUBERNETES_DOCS}/concepts/workloads/pods/disruptions/',
            'K8S-REL-003': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/',
            'K8S-REL-004': f'{cls.KUBERNETES_DOCS}/tasks/configure-pod-container/assign-pod-node/',
            'K8S-REL-005': f'{cls.KUBERNETES_DOCS}/concepts/workloads/pods/pod-lifecycle/',
            'K8S-REL-006': f'{cls.KUBERNETES_DOCS}/concepts/configuration/manage-resources-containers/',
            'K8S-REL-007': f'{cls.KUBERNETES_DOCS}/concepts/cluster-administration/logging/',
            'K8S-REL-008': f'{cls.KUBERNETES_DOCS}/tasks/run-application/horizontal-pod-autoscale/',
            'K8S-REL-009': f'{cls.KUBERNETES_DOCS}/concepts/workloads/controllers/deployment/',
            'K8S-REL-010': f'{cls.KUBERNETES_DOCS}/tasks/administer-cluster/highly-available-master/',

            # Scalability rules (K8S-SCALE-*)
            'K8S-SCALE-001': f'{cls.KUBERNETES_DOCS}/tasks/run-application/horizontal-pod-autoscale/',
            'K8S-SCALE-002': f'{cls.KUBERNETES_DOCS}/concepts/cluster-administration/cluster-autoscaling/',

            # Cost rules (K8S-COST-*)
            'K8S-COST-001': f'{cls.KUBERNETES_DOCS}/concepts/configuration/manage-resources-containers/',
            'K8S-COST-002': f'{cls.KUBERNETES_DOCS}/tasks/administer-cluster/manage-resources/',
        }

        return k8s_docs.get(rule_id, f'{cls.KUBERNETES_DOCS}/')

    @classmethod
    def _get_docker_doc_url(cls, rule_id: str) -> str:
        """Get Docker-specific documentation URL."""
        docker_docs = {
            # YAML-based rules (DOCKER-001 to DOCKER-008)
            'DOCKER-001': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#user',
            'DOCKER-002': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#tags',
            'DOCKER-003': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#tags',
            'DOCKER-004': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#healthcheck',
            'DOCKER-005': f'{cls.DOCKER_DOCS}/develop/develop-images/multistage-build/',
            'DOCKER-006': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#secrets',
            'DOCKER-007': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#apt-get',
            'DOCKER-008': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#tags',

            # DKR-SEC-* rules
            'DKR-SEC-001': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#user',
            'DKR-SEC-002': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#tags',
            'DKR-SEC-003': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#secrets',
            'DKR-SEC-004': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#healthcheck',
            'DKR-SEC-005': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#content-trust',
            'DKR-SEC-006': f'{cls.DOCKER_DOCS}/develop/develop-images/multistage-build/',
            'DKR-SEC-007': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#entrypoint',
            'DKR-SEC-008': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#cmd',
            'DKR-SEC-009': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#apt-get',
            'DKR-SEC-010': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#add-or-copy',

            # DKR-REL-* rules
            'DKR-REL-001': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#healthcheck',
            'DKR-REL-002': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#labels',

            # DKR-SCALE-* rules
            'DKR-SCALE-001': f'{cls.DOCKER_DOCS}/develop/develop-images/dockerfile_best-practices/#layers',
        }

        return docker_docs.get(rule_id, f'{cls.DOCKER_DOCS}/')

    @classmethod
    def _get_terraform_doc_url(cls, rule_id: str) -> str:
        """Get Terraform-specific documentation URL."""
        tf_docs = {
            # YAML-based rules (TF-001 to TF-012)
            'TF-001': f'{cls.TERRAFORM_DOCS}/cdktf/aws/s3-bucket',
            'TF-002': f'{cls.TERRAFORM_DOCS}/cdktf/aws/security-group',
            'TF-003': f'{cls.TERRAFORM_DOCS}/cdktf/aws/s3-bucket-server-side-encryption-configuration',
            'TF-004': f'{cls.TERRAFORM_DOCS}/cdktf/aws/s3-bucket',
            'TF-005': f'{cls.TERRAFORM_DOCS}/cdktf/aws/iam-policy',
            'TF-006': f'{cls.TERRAFORM_DOCS}/language/settings/backends/',
            'TF-007': f'{cls.TERRAFORM_DOCS}/cdktf/aws/s3-bucket',
            'TF-008': f'{cls.TERRAFORM_DOCS}/language/resources/syntax/',
            'TF-009': f'{cls.TERRAFORM_DOCS}/cdktf/aws/db-instance',
            'TF-010': f'{cls.TERRAFORM_DOCS}/cdktf/aws/db-instance',
            'TF-011': f'{cls.TERRAFORM_DOCS}/cdktf/aws/db-instance',
            'TF-012': f'{cls.TERRAFORM_DOCS}/cdktf/aws/flow-log',

            # State management (TF-STATE-*)
            'TF-STATE-001': f'{cls.TERRAFORM_DOCS}/language/settings/backends/s3/',
            'TF-STATE-002': f'{cls.TERRAFORM_DOCS}/language/settings/backends/',
            'TF-STATE-003': f'{cls.TERRAFORM_DOCS}/language/settings/backends/s3/',
            'TF-STATE-004': f'{cls.TERRAFORM_DOCS}/language/settings/backends/s3/',

            # Provider rules (TF-PROV-*)
            'TF-PROV-001': f'{cls.TERRAFORM_DOCS}/language/providers/requirements/',
            'TF-PROV-002': f'{cls.TERRAFORM_DOCS}/language/providers/requirements/',

            # Security rules (TF-SEC-*)
            'TF-SEC-001': f'{cls.TERRAFORM_DOCS}/language/values/variables/',

            # Encryption rules (TF-ENC-*)
            'TF-ENC-001': f'{cls.TERRAFORM_DOCS}/cdktf/aws/s3-bucket-server-side-encryption-configuration',
            'TF-ENC-002': f'{cls.TERRAFORM_DOCS}/cdktf/aws/ebs-volume',
            'TF-ENC-003': f'{cls.TERRAFORM_DOCS}/cdktf/aws/db-instance',

            # Networking rules (TF-NET-*)
            'TF-NET-001': f'{cls.TERRAFORM_DOCS}/cdktf/aws/security-group',
            'TF-NET-002': f'{cls.TERRAFORM_DOCS}/cdktf/aws/db-instance',

            # IAM rules (TF-IAM-*)
            'TF-IAM-001': f'{cls.TERRAFORM_DOCS}/cdktf/aws/iam-policy',
            'TF-IAM-002': f'{cls.TERRAFORM_DOCS}/cdktf/aws/iam-policy',

            # Tagging rules (TF-TAG-*)
            'TF-TAG-001': f'{cls.TERRAFORM_DOCS}/language/resources/syntax/',

            # Module rules (TF-MOD-*)
            'TF-MOD-001': f'{cls.TERRAFORM_DOCS}/language/modules/develop/',
            'TF-MOD-002': f'{cls.TERRAFORM_DOCS}/language/modules/develop/',

            # Environment rules (TF-ENV-*)
            'TF-ENV-001': f'{cls.TERRAFORM_DOCS}/language/values/variables/',
            'TF-ENV-002': f'{cls.TERRAFORM_DOCS}/cli/config/',

            # CI/CD integration (TF-CICD-*)
            'TF-CICD-001': f'{cls.TERRAFORM_DOCS}/cloud-docs/team/continuous-integration',
            'TF-CICD-002': f'{cls.TERRAFORM_DOCS}/cli/commands/plan',
            'TF-CICD-003': f'{cls.TERRAFORM_DOCS}/cloud-docs/team/continuous-integration',
        }

        return tf_docs.get(rule_id, f'{cls.TERRAFORM_DOCS}/')

    @classmethod
    def _get_cicd_doc_url(cls, rule_id: str) -> str:
        """Get CI/CD-specific documentation URL."""
        cicd_docs = {
            # YAML-based rules (CI-001 to CI-010)
            'CI-001': f'{cls.GITHUB_ACTIONS_DOCS}/actions/automating-builds-and-tests/about-continuous-integration/',
            'CI-002': f'{cls.GITHUB_ACTIONS_DOCS}/code-security/supply-chain-security/understanding-your-software-supply-chain/',
            'CI-003': f'{cls.GITHUB_ACTIONS_DOCS}/packages/working-with-a-github-packages-registry/',
            'CI-004': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/security-hardening-for-github-actions/',
            'CI-005': f'{cls.GITHUB_ACTIONS_DOCS}/actions/using-workflows/about-workflows/',
            'CI-006': f'{cls.GITHUB_ACTIONS_DOCS}/actions/deployment/about-deployments/',
            'CI-007': f'{cls.GITHUB_ACTIONS_DOCS}/actions/managing-workflow-runs/approving-workflow-runs-from-public-repositories/',
            'CI-008': f'{cls.GITHUB_ACTIONS_DOCS}/actions/using-workflows/caching-dependencies-to-speed-up-workflows/',
            'CI-009': f'{cls.GITHUB_ACTIONS_DOCS}/repositories/managing-your-repositorys-settings-and-features/about-branch-protection-rules/',
            'CI-010': f'{cls.GITHUB_ACTIONS_DOCS}/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/',

            # Security rules (CI-SEC-*)
            'CI-SEC-001': f'{cls.GITHUB_ACTIONS_DOCS}/code-security/code-scanning/',
            'CI-SEC-002': f'{cls.GITHUB_ACTIONS_DOCS}/packages/working-with-a-github-packages-registry/',
            'CI-SEC-003': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/using-secrets-in-github-actions/',
            'CI-SEC-004': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/security-hardening-for-github-actions/',
            'CI-SEC-005': f'{cls.GITHUB_ACTIONS_DOCS}/code-security/supply-chain-security/',
            'CI-SEC-006': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/using-secrets-in-github-actions/',
            'CI-SEC-007': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/security-hardening-for-github-actions/',
            'CI-SEC-008': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/security-hardening-for-github-actions/',
            'CI-SEC-009': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/security-hardening-for-github-actions/',
            'CI-SEC-010': f'{cls.GITHUB_ACTIONS_DOCS}/actions/security-guides/security-hardening-for-github-actions/',

            # Scalability rules (CI-SCALE-*)
            'CI-SCALE-001': f'{cls.GITHUB_ACTIONS_DOCS}/actions/using-workflows/caching-dependencies-to-speed-up-workflows/',
            'CI-SCALE-002': f'{cls.GITHUB_ACTIONS_DOCS}/actions/using-jobs/using-a-matrix-for-your-jobs/',

            # Reliability rules (CI-REL-*)
            'CI-REL-001': f'{cls.GITHUB_ACTIONS_DOCS}/actions/using-workflows/',
            'CI-REL-002': f'{cls.GITHUB_ACTIONS_DOCS}/actions/automating-builds-and-tests/about-continuous-integration/',
        }

        return cicd_docs.get(rule_id, f'{cls.GITHUB_ACTIONS_DOCS}/')

    @classmethod
    def _get_helm_doc_url(cls, rule_id: str) -> str:
        """Get Helm-specific documentation URL."""
        helm_docs = {
            'HELM-SEC-001': f'{cls.HELM_DOCS}/intro/best_practices/',
            'HELM-SEC-002': f'{cls.HELM_DOCS}/intro/best_practices/',
            'HELM-REL-001': f'{cls.HELM_DOCS}/chart_template_guide/',
        }

        return helm_docs.get(rule_id, f'{cls.HELM_DOCS}/')

    @classmethod
    def _get_monitoring_doc_url(cls, rule_id: str) -> str:
        """Get monitoring-specific documentation URL."""
        monitoring_docs = {
            'MON-001': f'{cls.PROMETHEUS_DOCS}/prometheus/latest/getting_started/',
            'MON-002': f'{cls.GRAFANA_DOCS}/grafana/latest/dashboards/',
            'MON-003': f'{cls.PROMETHEUS_DOCS}/prometheus/latest/configuration/alerting_rules/',
            'MON-004': f'{cls.PROMETHEUS_DOCS}/prometheus/latest/configuration/configuration/',
        }

        return monitoring_docs.get(rule_id, f'{cls.PROMETHEUS_DOCS}/')


# Convenience function
def get_documentation_url(rule_id: str, file_type: str | None = None) -> str | None:
    """Get documentation URL for a rule."""
    return DevOpsDocumentation.get_documentation_url(rule_id, file_type)
