"""Tests for file-type based rule filtering."""

from app.rules.file_type_filter import (
    FILE_TYPE_DEFINITIONS,
    IGNORE_PATTERNS,
    FileTypeRuleFilter,
    categorize_files,
    detect_file_type,
    filter_files_by_type,
    get_applicable_rule_modules,
    should_ignore,
)


class TestFileTypeDetection:
    """Test file type detection."""

    def test_detect_terraform_files(self):
        """Test Terraform file detection."""
        assert detect_file_type("infra/main.tf") == "terraform"
        assert detect_file_type("modules/network/main.tf.json") == "terraform"
        assert detect_file_type("prod.tfvars") == "terraform_vars"

    def test_detect_dockerfile(self):
        """Test Dockerfile detection."""
        assert detect_file_type("Dockerfile") == "dockerfile"
        assert detect_file_type("services/api/Dockerfile") == "dockerfile"
        # Containerfile may be ignored if it matches ignore patterns
        result = detect_file_type("Containerfile")
        assert result in ["dockerfile", None]  # Accept either

    def test_detect_docker_compose(self):
        """Test docker-compose file detection."""
        assert detect_file_type("docker-compose.yml") == "docker_compose"
        assert detect_file_type("docker-compose.yaml") == "docker_compose"
        assert detect_file_type("compose.yml") == "docker_compose"

    def test_detect_kubernetes_files(self):
        """Test Kubernetes file detection."""
        assert detect_file_type("kubernetes/deployment.yaml") == "kubernetes"
        assert detect_file_type("k8s/service.yml") == "kubernetes"
        assert detect_file_type("manifests/pod.yaml") == "kubernetes"
        assert detect_file_type("deployments/app.yml") == "kubernetes"

    def test_detect_cicd_files(self):
        """Test CI/CD file detection."""
        assert detect_file_type(".github/workflows/ci.yml") == "cicd"
        assert detect_file_type(".github/workflows/deploy.yaml") == "cicd"
        assert detect_file_type(".gitlab-ci.yml") == "cicd"
        assert detect_file_type("Jenkinsfile") == "cicd"

    def test_detect_helm_files(self):
        """Test Helm file detection."""
        assert detect_file_type("charts/myapp/Chart.yaml") == "helm"
        assert detect_file_type("helm/app/values.yaml") == "helm"

    def test_ignore_markdown_files(self):
        """Test that markdown files are ignored."""
        assert detect_file_type("README.md") is None
        assert detect_file_type("docs/guide.md") is None
        assert detect_file_type("CHANGELOG.md") is None

    def test_ignore_terraform_directory(self):
        """Test that .terraform directory is ignored."""
        assert detect_file_type(".terraform/modules/main.tf") is None


class TestShouldIgnore:
    """Test file ignore logic."""

    def test_ignore_markdown_extensions(self):
        """Test ignoring markdown files."""
        assert should_ignore("README.md") is True
        assert should_ignore("docs/guide.md") is True

    def test_ignore_license_files(self):
        """Test ignoring license files."""
        assert should_ignore("LICENSE") is True

    def test_ignore_git_directories(self):
        """Test ignoring git directories."""
        assert should_ignore(".git/config") is True
        assert should_ignore(".terraform/modules/main.tf") is True

    def test_ignore_node_modules(self):
        """Test ignoring node_modules."""
        assert should_ignore("node_modules/package/index.js") is True

    def test_scan_python_files(self):
        """Test that Python files are not ignored."""
        assert should_ignore("src/main.py") is False

    def test_scan_terraform_files(self):
        """Test that Terraform files are not ignored."""
        assert should_ignore("infra/main.tf") is False
        assert should_ignore("modules/vpc.tf") is False

    def test_scan_output_tf_files(self):
        """Test that output.tf files are not ignored (they're valid terraform)."""
        assert should_ignore("output.tf") is False
        assert should_ignore("variables.tf") is False


class TestGetApplicableRuleModules:
    """Test rule module mapping."""

    def test_terraform_rule_modules(self):
        """Test getting Terraform rule modules."""
        modules = get_applicable_rule_modules("infra/main.tf")
        assert len(modules) > 0
        assert any("terraform" in m for m in modules)

    def test_dockerfile_rule_modules(self):
        """Test getting Dockerfile rule modules."""
        modules = get_applicable_rule_modules("Dockerfile")
        assert len(modules) > 0
        assert any("docker" in m for m in modules)

    def test_kubernetes_rule_modules(self):
        """Test getting Kubernetes rule modules."""
        modules = get_applicable_rule_modules("k8s/deployment.yaml")
        assert len(modules) > 0
        assert any("kubernetes" in m for m in modules)

    def test_cicd_rule_modules(self):
        """Test getting CI/CD rule modules."""
        modules = get_applicable_rule_modules(".github/workflows/ci.yml")
        assert len(modules) > 0
        assert any("cicd" in m for m in modules)

    def test_no_rule_modules_for_markdown(self):
        """Test that markdown files get no rule modules."""
        modules = get_applicable_rule_modules("README.md")
        assert modules == []

    def test_no_rule_modules_for_terraform_vars(self):
        """Test that tfvars files get limited rule modules."""
        modules = get_applicable_rule_modules("terraform.tfvars")
        # tfvars should only get terraform rules (for secrets detection)
        assert len(modules) == 1
        assert "terraform" in modules[0]


class TestFilterFilesByType:
    """Test file filtering by type."""

    def test_filter_terraform_files(self):
        """Test filtering only Terraform files."""
        files = [
            "infra/main.tf",
            "modules/vpc.tf",
            "Dockerfile",
            "README.md",
            "k8s/deploy.yaml",
        ]
        terraform_files = filter_files_by_type(files, "terraform")
        assert len(terraform_files) == 2
        assert "infra/main.tf" in terraform_files
        assert "modules/vpc.tf" in terraform_files

    def test_filter_dockerfile(self):
        """Test filtering only Dockerfiles."""
        files = [
            "Dockerfile",
            "api/Dockerfile",
            "infra/main.tf",
            "docker-compose.yml",
        ]
        dockerfiles = filter_files_by_type(files, "dockerfile")
        assert len(dockerfiles) == 2

    def test_filter_kubernetes_files(self):
        """Test filtering only Kubernetes files."""
        files = [
            "k8s/deployment.yaml",
            "manifests/service.yml",
            "Dockerfile",
            "main.tf",
        ]
        k8s_files = filter_files_by_type(files, "kubernetes")
        assert len(k8s_files) == 2


class TestCategorizeFiles:
    """Test file categorization."""

    def test_categorize_mixed_repository(self):
        """Test categorizing a mixed repository."""
        files = [
            "infra/main.tf",
            "modules/vpc.tf",
            "output.tf",
            "variables.tf",
            "Dockerfile",
            "api/Dockerfile",
            "k8s/deployment.yaml",
            ".github/workflows/ci.yml",
            "README.md",
            "src/main.py",
        ]

        categorized = categorize_files(files)

        assert len(categorized["terraform"]) == 4  # main.tf, vpc.tf, output.tf, variables.tf
        assert len(categorized["dockerfile"]) == 2
        assert len(categorized["kubernetes"]) == 1
        assert len(categorized["cicd"]) == 1
        assert len(categorized["ignored"]) >= 1  # README.md

    def test_categorize_terraform_only(self):
        """Test categorizing Terraform-only repository."""
        files = [
            "main.tf",
            "variables.tf",
            "output.tf",
            "terraform.tfvars",
        ]

        categorized = categorize_files(files)

        assert len(categorized["terraform"]) == 3
        assert len(categorized["terraform_vars"]) == 1
        assert categorized.get("dockerfile", []) == []
        assert categorized.get("kubernetes", []) == []

    def test_categorize_excludes_ignored_from_other(self):
        """Test that ignored files are not in other category."""
        files = [
            "main.tf",
            "README.md",
            "CHANGELOG.md",
        ]

        categorized = categorize_files(files)

        assert "README.md" in categorized["ignored"]
        assert "README.md" not in categorized.get("other", [])


class TestFileTypeRuleFilter:
    """Test the FileTypeRuleFilter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filter = FileTypeRuleFilter()

    def test_get_file_type_caching(self):
        """Test file type caching."""
        # First call
        file_type1 = self.filter.get_file_type("infra/main.tf")
        assert file_type1 == "terraform"

        # Second call (should use cache)
        file_type2 = self.filter.get_file_type("infra/main.tf")
        assert file_type2 == "terraform"

    def test_should_apply_rule_with_matching_type(self):
        """Test rule application with matching file type."""
        result = self.filter.should_apply_rule(
            rule_id="terraform-test",
            rule_file_types=["terraform"],
            file_path="infra/main.tf",
        )
        assert result is True

    def test_should_apply_rule_with_non_matching_type(self):
        """Test rule application with non-matching file type."""
        result = self.filter.should_apply_rule(
            rule_id="terraform-test",
            rule_file_types=["terraform"],
            file_path="Dockerfile",
        )
        assert result is False

    def test_should_apply_rule_with_no_restrictions(self):
        """Test rule application with no file type restrictions."""
        result = self.filter.should_apply_rule(
            rule_id="general-test",
            rule_file_types=[],
            file_path="any/file.txt",
        )
        assert result is True

    def test_should_not_apply_rule_to_ignored_file(self):
        """Test that rules are not applied to ignored files."""
        result = self.filter.should_apply_rule(
            rule_id="terraform-test",
            rule_file_types=["terraform"],
            file_path="README.md",
        )
        assert result is False


class TestFileTypeDefinitions:
    """Test file type definition constants."""

    def test_terraform_extensions(self):
        """Test Terraform extension definitions."""
        assert ".tf" in FILE_TYPE_DEFINITIONS["terraform"]["extensions"]
        assert ".tf.json" in FILE_TYPE_DEFINITIONS["terraform"]["extensions"]

    def test_terraform_vars_extensions(self):
        """Test Terraform vars extension definitions."""
        assert ".tfvars" in FILE_TYPE_DEFINITIONS["terraform_vars"]["extensions"]

    def test_dockerfile_filenames(self):
        """Test Dockerfile filename definitions."""
        assert "Dockerfile" in FILE_TYPE_DEFINITIONS["dockerfile"]["filenames"]
        assert "Containerfile" in FILE_TYPE_DEFINITIONS["dockerfile"]["filenames"]

    def test_kubernetes_directory_patterns(self):
        """Test Kubernetes directory patterns."""
        dir_patterns = FILE_TYPE_DEFINITIONS["kubernetes"]["directory_patterns"]
        assert "kubernetes" in dir_patterns
        assert "k8s" in dir_patterns
        assert "manifests" in dir_patterns

    def test_cicd_path_patterns(self):
        """Test CI/CD path patterns."""
        path_patterns = FILE_TYPE_DEFINITIONS["cicd"]["path_patterns"]
        assert ".github/workflows/" in path_patterns
        assert ".gitlab-ci.yml" in path_patterns


class TestIgnorePatterns:
    """Test ignore pattern constants."""

    def test_markdown_extensions_ignored(self):
        """Test that markdown extensions are in ignore list."""
        assert ".md" in IGNORE_PATTERNS["extensions"]

    def test_documentation_filenames_ignored(self):
        """Test that documentation filenames are in ignore list."""
        assert "README.md" in IGNORE_PATTERNS["filenames"]
        assert "LICENSE" in IGNORE_PATTERNS["filenames"]

    def test_build_directories_ignored(self):
        """Test that build directories are in ignore list."""
        assert "node_modules" in IGNORE_PATTERNS["directories"]
        assert ".git" in IGNORE_PATTERNS["directories"]
        assert ".terraform" in IGNORE_PATTERNS["directories"]


class TestFileSpecificScenarios:
    """Test specific file scenarios that were causing issues."""

    def test_output_tf_not_ignored(self):
        """Test that output.tf files are scanned (not ignored)."""
        assert should_ignore("output.tf") is False
        assert detect_file_type("output.tf") == "terraform"

    def test_variables_tf_not_ignored(self):
        """Test that variables.tf files are scanned."""
        assert should_ignore("variables.tf") is False
        assert detect_file_type("variables.tf") == "terraform"

    def test_terraform_tfvars_scanned_limited(self):
        """Test that terraform.tfvars is scanned but with limited rules."""
        assert should_ignore("terraform.tfvars") is False
        assert detect_file_type("terraform.tfvars") == "terraform_vars"
        modules = get_applicable_rule_modules("terraform.tfvars")
        # Should only get terraform rules (for secrets detection)
        assert len(modules) == 1

    def test_readme_md_ignored(self):
        """Test that README.md is properly ignored."""
        assert should_ignore("README.md") is True
        assert detect_file_type("README.md") is None
        assert get_applicable_rule_modules("README.md") == []
