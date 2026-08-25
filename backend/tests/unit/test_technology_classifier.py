"""Tests for the canonical technology classifier.

Verifies that every file/finding maps to EXACTLY ONE technology and that
Helm ownership always wins over Kubernetes (no double counting).
"""

from app.services.technology_classifier import (
    ANSIBLE,
    AWS,
    AZURE,
    AZURE_DEVOPS,
    CIRCLECI,
    CODE,
    DEPENDENCIES,
    DOCKER,
    DOCKER_COMPOSE,
    GCP,
    GITHUB_ACTIONS,
    GITLAB_CI,
    GRAFANA,
    HELM,
    JENKINS,
    KUBERNETES,
    PROMETHEUS,
    SECRETS,
    TERRAFORM,
    TRAVIS_CI,
    classify_technology,
)


def _assert(path, expected, scanner=""):
    assert classify_technology(path, scanner) == expected, (
        f"{path!r} (scanner={scanner!r}) -> {classify_technology(path, scanner)!r}, "
        f"expected {expected!r}"
    )


class TestHelmOwnership:
    """Helm owns chart files even when they live under kubernetes/ paths."""

    def test_chart_yaml_is_helm(self):
        _assert("Chart.yaml", HELM)
        _assert("charts/backend/Chart.yaml", HELM)
        _assert("kubernetes/Backend/charts/app/Chart.yaml", HELM)

    def test_values_yaml_is_helm(self):
        _assert("values.yaml", HELM)
        _assert("helm/backend/values.yaml", HELM)
        _assert("kubernetes/Backend/charts/app/values.yaml", HELM)

    def test_templates_directory_is_helm(self):
        _assert("kubernetes/Backend/templates/deployment.yaml", HELM)
        _assert("charts/app/templates/service.yaml", HELM)
        _assert("templates/ingress.yaml", HELM)

    def test_helmfile_is_helm(self):
        _assert("helmfile.yaml", HELM)
        _assert("deploy/helmfile.yml", HELM)


class TestHelmWinsOverKubernetes:
    """A Helm file must never be counted again as Kubernetes."""

    def test_template_with_kube_score_scanner(self):
        _assert("kubernetes/Backend/templates/deployment.yaml", HELM, "kube_score")

    def test_chart_yaml_with_kube_score_scanner(self):
        _assert("kubernetes/charts/backend/Chart.yaml", HELM, "kube_score")

    def test_values_yaml_in_kubernetes_dir(self):
        _assert("kubernetes/Backend/values.yaml", HELM, "kube_score")


class TestDockerOwnership:
    def test_dockerfile_variants(self):
        _assert("Dockerfile", DOCKER)
        _assert("Frontend/Dockerfile", DOCKER)
        _assert("services/api/Dockerfile.prod", DOCKER)
        _assert("Containerfile", DOCKER)
        _assert("deploy/Dockerfile.dev", DOCKER)

    def test_hadolint_scanner(self):
        _assert("Dockerfile", DOCKER, "hadolint")

    def test_compose_is_not_dockerfile(self):
        _assert("docker-compose.yml", DOCKER_COMPOSE)


class TestGitHubActionsOwnership:
    def test_workflow_files(self):
        _assert(".github/workflows/backend.yml", GITHUB_ACTIONS)
        _assert(".github/workflows/ci.yaml", GITHUB_ACTIONS)

    def test_non_workflow_yaml_is_not_actions(self):
        _assert("workflows/ci.yaml", CODE)


class TestTerraformOwnership:
    def test_tf_variants(self):
        _assert("infra/main.tf", TERRAFORM)
        _assert("modules/network/variables.tf", TERRAFORM)
        _assert("main.tf.json", TERRAFORM)
        _assert("terraform.tfvars", TERRAFORM)

    def test_tfsec_scanner(self):
        _assert("main.tf", TERRAFORM, "tfsec")

    def test_aws_tf_still_terraform(self):
        _assert("terraform/aws/main.tf", TERRAFORM)


class TestKubernetesOwnership:
    """Only native Kubernetes manifest filenames count as Kubernetes."""

    def test_native_manifest_filenames(self):
        for name in [
            "deployment.yaml",
            "service.yaml",
            "ingress.yaml",
            "daemonset.yaml",
            "statefulset.yaml",
            "configmap.yaml",
            "secret.yaml",
            "cronjob.yaml",
            "namespace.yaml",
            "kustomization.yaml",
        ]:
            _assert(f"kubernetes/Backend/{name}", KUBERNETES)
            _assert(f"manifests/backend-{name}", KUBERNETES)

    def test_kube_score_scanner(self):
        _assert("kubernetes/Backend/backend-deployemt.yaml", KUBERNETES, "kube_score")

    def test_non_manifest_yaml_is_not_kubernetes(self):
        _assert("kubernetes/Backend/random-config.yml", CODE)
        _assert("manifests/notes.yaml", CODE)


class TestDirectoryKindRescue:
    """Manifests with non-standard filenames are rescued by their directory.

    A YAML/JSON file living in a Kubernetes/Helm directory whose filename
    references a workload kind (deploy*, stateful*, ...) belongs to that
    technology even when the exact filename is misspelled or suffixed.
    """

    def test_misspelled_workload_manifests_in_kubernetes_dir(self):
        _assert("kubernetes/Backend/backend-deployemt.yaml", KUBERNETES)
        _assert("/kubernetes/Backend/backend-deployemt.yaml", KUBERNETES)
        _assert("kubernetes/DB-Service/statefullset.yaml", KUBERNETES)
        _assert("k8s/prod/web-deploy.yaml", KUBERNETES)

    def test_helm_directory_with_kind_stem(self):
        _assert("helm-chart/backend-deployemt.yaml", HELM)
        _assert("helm-charts/app/statefullset.yaml", HELM)

    def test_random_config_stays_code(self):
        # No workload-kind stem: directory alone must not claim the file.
        _assert("kubernetes/Backend/random-config.yml", CODE)
        _assert("k8s/notes.txt", CODE)

    def test_exact_filenames_still_win_over_directories(self):
        # A native manifest name beats an ambiguous directory hint.
        _assert("/helm-chart/ingress.yaml", KUBERNETES)
        # And Helm filenames beat a kubernetes directory.
        _assert("kubernetes/Backend/values.yaml", HELM)


class TestOtherTechnologies:
    def test_ci_platforms(self):
        _assert(".gitlab-ci.yml", GITLAB_CI)
        _assert("Jenkinsfile", JENKINS)
        _assert("Jenkinsfile-Backend", JENKINS)
        _assert(".circleci/config.yml", CIRCLECI)
        _assert("azure-pipelines.yml", AZURE_DEVOPS)
        _assert(".travis.yml", TRAVIS_CI)

    def test_config_families(self):
        _assert("docker-compose.yml", DOCKER_COMPOSE)
        _assert("compose.yaml", DOCKER_COMPOSE)
        _assert("ansible/playbooks/main.yml", ANSIBLE)
        _assert("roles/webserver/tasks/main.yml", ANSIBLE)
        _assert("infra/prometheus/prometheus.yml", PROMETHEUS)
        _assert("infra/grafana/dashboard.json", GRAFANA)

    def test_cloud_provider_fallbacks(self):
        _assert("terraform/aws/main.tf", TERRAFORM, "checkov")
        _assert("aws/credentials", AWS, "gitleaks")
        _assert("azure/aks/config.yml", AZURE)
        _assert("gcp/gke/cluster.yaml", GCP)


class TestScannerFallbacks:
    def test_secrets(self):
        _assert("src/config.py", SECRETS, "gitleaks")

    def test_dependencies(self):
        _assert("package-lock.json", DEPENDENCIES, "npm_audit")
        _assert("requirements.txt", DEPENDENCIES, "pip_audit")

    def test_file_ownership_wins_over_scanner(self):
        # A secret in a Helm values file is a Helm finding, not a secrets one.
        _assert("helm/backend/values.yaml", HELM, "gitleaks")
        _assert("Dockerfile", DOCKER, "gitleaks")


class TestExclusiveOwnership:
    """Each finding maps to exactly one technology."""

    def test_single_value_always(self):
        import random

        for path in [
            "Chart.yaml",
            "values.yaml",
            "Dockerfile",
            ".github/workflows/x.yml",
            "main.tf",
            "kubernetes/deployment.yaml",
            "helm/backend/templates/deployment.yaml",
            "Jenkinsfile",
            "docker-compose.yml",
            "src/main.py",
            "README.md",
        ]:
            for scanner in ["", "kube_score", "hadolint", "gitleaks", "tfsec"]:
                tech = classify_technology(path, scanner)
                assert isinstance(tech, str) and tech, (path, scanner)
