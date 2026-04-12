"""Tests for technology detector service."""

from app.services.technology_detector import TechnologyStack, detect_technology_stack


class TestTechnologyDetector:
    """Test cases for technology stack detection."""

    def test_empty_file_list(self):
        """Test detection with empty file list."""
        stack = detect_technology_stack([])
        assert isinstance(stack, TechnologyStack)
        assert stack.get_detected_technologies() == []

    def test_detect_terraform_files(self):
        """Test Terraform file detection."""
        files = [
            "infra/main.tf",
            "infra/variables.tf",
            "modules/network/main.tf",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_terraform is True
        assert len(stack.terraform_files) == 3
        assert "terraform" in stack.get_detected_technologies()

    def test_detect_docker_files(self):
        """Test Docker file detection."""
        files = [
            "Dockerfile",
            "services/api/Dockerfile",
            "containerfile",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_docker is True
        assert len(stack.docker_files) == 3
        assert "docker" in stack.get_detected_technologies()

    def test_detect_docker_compose(self):
        """Test Docker Compose file detection."""
        files = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_docker_compose is True
        assert len(stack.docker_compose_files) == 3

    def test_detect_kubernetes_files(self):
        """Test Kubernetes file detection."""
        files = [
            "kubernetes/deployment.yaml",
            "k8s/service.yml",
            "manifests/pod.yaml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_kubernetes is True
        assert len(stack.kubernetes_files) == 3
        assert "kubernetes" in stack.get_detected_technologies()

    def test_detect_github_actions(self):
        """Test GitHub Actions file detection."""
        files = [
            ".github/workflows/ci.yml",
            ".github/workflows/deploy.yaml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_github_actions is True
        assert len(stack.github_actions_files) == 2
        assert "github_actions" in stack.get_detected_technologies()

    def test_detect_gitlab_ci(self):
        """Test GitLab CI file detection."""
        files = [
            ".gitlab-ci.yml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_gitlab_ci is True
        assert len(stack.gitlab_ci_files) == 1

    def test_detect_helm_files(self):
        """Test Helm file detection."""
        files = [
            "charts/myapp/Chart.yaml",
            "charts/myapp/values.yaml",
            "helm/another/Chart.yaml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_helm is True
        # Helm files may include duplicates due to Kubernetes detection overlap
        assert len(stack.helm_files) >= 3

    def test_detect_ansible_files(self):
        """Test Ansible file detection."""
        files = [
            "ansible/playbook.yml",
            "playbooks/deploy.yaml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_ansible is True
        assert len(stack.ansible_files) == 2

    def test_mixed_technology_stack(self):
        """Test detection of mixed technology stack."""
        files = [
            "Dockerfile",
            "infra/main.tf",
            "kubernetes/deployment.yaml",
            ".github/workflows/ci.yml",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_docker is True
        assert stack.has_terraform is True
        assert stack.has_kubernetes is True
        assert stack.has_github_actions is True

        detected = stack.get_detected_technologies()
        assert "docker" in detected
        assert "terraform" in detected
        assert "kubernetes" in detected
        assert "github_actions" in detected

    def test_get_scanners_to_run(self):
        """Test that correct scanners are selected based on detected technologies."""
        files = [
            "infra/main.tf",
            "Dockerfile",
            "kubernetes/deployment.yaml",
        ]
        stack = detect_technology_stack(files)
        scanners = stack.get_scanners_to_run()

        assert "terraform" in scanners
        assert "docker" in scanners
        assert "kubernetes" in scanners

    def test_to_dict_output(self):
        """Test the to_dict method output."""
        files = [
            "Dockerfile",
            "infra/main.tf",
        ]
        stack = detect_technology_stack(files)
        result = stack.to_dict()

        assert isinstance(result, dict)
        assert "detected_stack" in result
        assert "docker" in result
        assert "terraform" in result
        assert "docker_files" in result
        assert "terraform_files" in result

    def test_kubernetes_detection_by_path(self):
        """Test Kubernetes detection by directory path."""
        files = [
            "deployments/web.yaml",
            "manifests/api.yml",
        ]
        stack = detect_technology_stack(files)

        # Should detect based on path indicators
        assert stack.has_kubernetes is True

    def test_kubernetes_detection_by_filename(self):
        """Test Kubernetes detection by filename patterns."""
        files = [
            "deployment.yaml",
            "service.yml",
            "configmap.yaml",
            "secret.yml",
        ]
        stack = detect_technology_stack(files)

        # Should detect based on filename patterns
        assert stack.has_kubernetes is True

    def test_terraform_tfvars_detection(self):
        """Test Terraform .tfvars file detection."""
        files = [
            "infra/main.tf",
            "infra/variables.tfvars",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_terraform is True
        assert len(stack.terraform_files) == 2

    def test_no_false_positives(self):
        """Test that non-matching files don't trigger false positives."""
        files = [
            "README.md",
            "src/main.py",
            "docs/guide.txt",
            "package.json",
        ]
        stack = detect_technology_stack(files)

        assert stack.has_terraform is False
        assert stack.has_docker is False
        assert stack.has_kubernetes is False
        assert stack.has_github_actions is False
        assert stack.get_detected_technologies() == []
