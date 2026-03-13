#!/usr/bin/env python3
"""
Rule Engine Accuracy Test Script

Tests the rule engine against multiple repositories and generates accuracy reports.

Usage:
    python scripts/test_rule_engine_accuracy.py
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.parsers.terraform import TerraformParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.cicd import CICDParser
from app.parsers.base import ParserRegistry
from app.rule_engine.base import RuleRegistry, RuleFinding
from app.services.findings_deduplicator import FindingsDeduplicator


@dataclass
class ExpectedFinding:
    """Expected finding for comparison."""
    rule_id: str
    file: str
    severity: str = ""
    category: str = ""


@dataclass
class TestResult:
    """Test result for a single repository."""
    repository: str
    files_scanned: int = 0
    findings_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    scan_duration: float = 0.0
    findings: List[Dict] = field(default_factory=list)
    expected_findings: List[ExpectedFinding] = field(default_factory=list)


@dataclass
class AccuracyMetrics:
    """Overall accuracy metrics."""
    repositories_tested: int = 0
    total_files_scanned: int = 0
    total_findings: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    accuracy: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    total_duration: float = 0.0


class RuleEngineAccuracyTester:
    """Test rule engine accuracy against repositories."""

    def __init__(self, repos_dir: Path):
        self.repos_dir = repos_dir
        self.parser_registry = self._setup_parsers()
        self.rule_registry = RuleRegistry()
        self.deduplicator = FindingsDeduplicator()
        self.results: List[TestResult] = []
        self.metrics = AccuracyMetrics()

    def _setup_parsers(self) -> ParserRegistry:
        """Initialize parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        return registry

    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type from path."""
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()
        path_str = str(file_path).lower()

        if suffix in ['.tf', '.tf.json', '.tfvars']:
            return 'terraform'
        elif name in ['dockerfile', 'containerfile'] or 'dockerfile' in name:
            return 'dockerfile'
        elif '.github/workflows/' in path_str or name in ['.gitlab-ci.yml', 'jenkinsfile']:
            return 'cicd'
        elif suffix in ['.yaml', '.yml']:
            # Check if kubernetes
            k8s_indicators = ['kubernetes', 'k8s', 'manifests', 'deployment', 'service', 'pod']
            if any(ind in path_str for ind in k8s_indicators):
                return 'kubernetes'

        return 'unknown'

    def _scan_repository(self, repo_path: Path) -> List[RuleFinding]:
        """Scan a single repository."""
        all_findings = []

        # Collect all files
        files = []
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if '.git' in str(file_path) and '.github' not in str(file_path):
                continue
            if 'node_modules' in str(file_path):
                continue
            files.append(file_path)

        # Parse and scan each file
        for file_path in files:
            file_type = self._get_file_type(file_path)
            if file_type == 'unknown':
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                parsed = self.parser_registry.parse_file(file_path, content)

                if not parsed:
                    continue

                # Extract resources
                resources = []
                parsed_data = parsed.parsed_data

                if isinstance(parsed_data, dict):
                    if file_type == 'terraform':
                        for resource in parsed_data.get('resources', []):
                            resource['file_path'] = str(file_path)
                            resource['file_type'] = 'terraform'
                            resources.append(resource)

                        for backend in parsed_data.get('backends', []):
                            resources.append({
                                'file_type': 'terraform',
                                'resource_type': 'backend',
                                'properties': backend,
                                'file_path': str(file_path),
                            })

                    elif file_type == 'kubernetes':
                        for deployment in parsed_data.get('deployments', []):
                            deployment['file_path'] = str(file_path)
                            deployment['file_type'] = 'kubernetes'
                            resources.append(deployment)

                    elif file_type == 'dockerfile':
                        parsed_data['file_path'] = str(file_path)
                        parsed_data['file_type'] = 'dockerfile'
                        resources.append(parsed_data)

                    elif file_type == 'cicd':
                        parsed_data['file_path'] = str(file_path)
                        parsed_data['file_type'] = 'cicd'
                        parsed_data['raw_content'] = content
                        resources.append(parsed_data)

                # Run rules
                file_findings = self.rule_registry.evaluate_all(
                    resources,
                    str(file_path),
                    file_type=file_type
                )
                all_findings.extend(file_findings)

            except Exception as e:
                print(f"Error scanning {file_path}: {e}")

        # Deduplicate findings
        deduplicated = self.deduplicator.deduplicate(all_findings)
        return deduplicated

    def _load_expected_findings(self, repo_path: Path) -> List[ExpectedFinding]:
        """Load expected findings for a repository."""
        expected_file = repo_path / 'expected_findings.json'

        if not expected_file.exists():
            return []

        try:
            data = json.loads(expected_file.read_text())
            findings = data.get('expected_findings', [])
            return [ExpectedFinding(**f) for f in findings]
        except Exception as e:
            print(f"Error loading expected findings for {repo_path}: {e}")
            return []

    def _calculate_metrics(self, actual: List[RuleFinding], expected: List[ExpectedFinding]) -> Dict[str, int]:
        """Calculate TP, FP, FN."""
        # Create sets for comparison
        actual_set = {(f.rule_id, Path(f.file_path).name) for f in actual}
        expected_set = {(e.rule_id, Path(e.file).name) for e in expected}

        true_positives = len(actual_set & expected_set)
        false_positives = len(actual_set - expected_set)
        false_negatives = len(expected_set - actual_set)

        return {
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
        }

    def run_tests(self) -> AccuracyMetrics:
        """Run accuracy tests on all repositories."""
        print("=" * 70)
        print("Rule Engine Accuracy Test")
        print("=" * 70)
        print()

        start_time = time.time()

        # Find all repositories
        repos = sorted([d for d in self.repos_dir.iterdir() if d.is_dir()])

        if not repos:
            print("No repositories found in tests/repositories/")
            print("Creating synthetic test repositories...")
            repos = self._create_synthetic_repos()

        print(f"Testing {len(repos)} repositories...")
        print()

        for repo_path in repos:
            print(f"Scanning: {repo_path.name}...", end=" ")

            repo_start = time.time()

            # Scan repository
            findings = self._scan_repository(repo_path)

            # Load expected findings
            expected = self._load_expected_findings(repo_path)

            # Calculate metrics
            metrics = self._calculate_metrics(findings, expected)

            repo_duration = time.time() - repo_start

            # Create test result
            result = TestResult(
                repository=repo_path.name,
                files_scanned=len(list(repo_path.rglob("*"))),
                findings_count=len(findings),
                true_positives=metrics['true_positives'],
                false_positives=metrics['false_positives'],
                false_negatives=metrics['false_negatives'],
                scan_duration=repo_duration,
                findings=[f.to_dict() for f in findings],
                expected_findings=expected,
            )
            self.results.append(result)

            status = "✓" if metrics['false_positives'] == 0 and metrics['false_negatives'] == 0 else "⚠"
            print(f"{status} {len(findings)} findings, {metrics['true_positives']} TP, {metrics['false_positives']} FP, {metrics['false_negatives']} FN")

        # Calculate overall metrics
        total_duration = time.time() - start_time

        self.metrics.repositories_tested = len(self.results)
        self.metrics.total_files_scanned = sum(r.files_scanned for r in self.results)
        self.metrics.total_findings = sum(r.findings_count for r in self.results)
        self.metrics.true_positives = sum(r.true_positives for r in self.results)
        self.metrics.false_positives = sum(r.false_positives for r in self.results)
        self.metrics.false_negatives = sum(r.false_negatives for r in self.results)
        self.metrics.total_duration = total_duration

        # Calculate rates
        total = self.metrics.true_positives + self.metrics.false_positives + self.metrics.false_negatives
        if total > 0:
            self.metrics.accuracy = (self.metrics.true_positives / total) * 100
            self.metrics.false_positive_rate = (self.metrics.false_positives / (self.metrics.true_positives + self.metrics.false_positives + 0.001)) * 100
            self.metrics.false_negative_rate = (self.metrics.false_negatives / (self.metrics.true_positives + self.metrics.false_negatives + 0.001)) * 100

            # Precision and Recall
            precision_denom = self.metrics.true_positives + self.metrics.false_positives
            recall_denom = self.metrics.true_positives + self.metrics.false_negatives

            self.metrics.precision = (self.metrics.true_positives / (precision_denom + 0.001)) * 100
            self.metrics.recall = (self.metrics.true_positives / (recall_denom + 0.001)) * 100

            # F1 Score
            if self.metrics.precision + self.metrics.recall > 0:
                self.metrics.f1_score = 2 * (self.metrics.precision * self.metrics.recall) / (self.metrics.precision + self.metrics.recall)

        print()
        print("=" * 70)
        print(f"Test Complete: {self.metrics.repositories_tested} repositories, "
              f"{self.metrics.total_findings} findings, "
              f"Accuracy: {self.metrics.accuracy:.1f}%")
        print("=" * 70)

        return self.metrics

    def _create_synthetic_repos(self) -> List[Path]:
        """Create synthetic test repositories for testing."""
        print("Creating synthetic test repositories...")

        # Create 50 synthetic repositories with different configurations
        synthetic_configs = [
            # Terraform repos
            {'name': 'tf-s3-public', 'type': 'terraform', 'issues': ['S3_PUBLIC_ACL', 'S3_NO_ENCRYPTION']},
            {'name': 'tf-s3-secure', 'type': 'terraform', 'issues': []},
            {'name': 'tf-ec2-unencrypted', 'type': 'terraform', 'issues': ['EBS_NO_ENCRYPTION']},
            {'name': 'tf-rds-public', 'type': 'terraform', 'issues': ['RDS_PUBLIC_ACCESS', 'RDS_NO_ENCRYPTION']},
            {'name': 'tf-security-group-open', 'type': 'terraform', 'issues': ['SG_OPEN_INGRESS']},
            {'name': 'tf-no-backend', 'type': 'terraform', 'issues': ['NO_REMOTE_BACKEND']},
            {'name': 'tf-local-backend', 'type': 'terraform', 'issues': ['LOCAL_BACKEND']},
            {'name': 'tf-no-locking', 'type': 'terraform', 'issues': ['NO_STATE_LOCKING']},
            {'name': 'tf-hardcoded-secrets', 'type': 'terraform', 'issues': ['HARDCODED_SECRETS']},
            {'name': 'tf-no-tags', 'type': 'terraform', 'issues': ['MISSING_TAGS']},
            {'name': 'tf-unpinned-providers', 'type': 'terraform', 'issues': ['UNPINNED_PROVIDERS']},
            {'name': 'tf-iam-wildcard', 'type': 'terraform', 'issues': ['IAM_WILDCARD_PERMISSIONS']},
            {'name': 'tf-mixed-good', 'type': 'terraform', 'issues': ['MISSING_TAGS', 'NO_STATE_LOCKING']},
            {'name': 'tf-mixed-bad', 'type': 'terraform', 'issues': ['S3_PUBLIC_ACL', 'NO_REMOTE_BACKEND', 'HARDCODED_SECRETS']},
            {'name': 'tf-complete-secure', 'type': 'terraform', 'issues': []},

            # Kubernetes repos
            {'name': 'k8s-no-limits', 'type': 'kubernetes', 'issues': ['NO_RESOURCE_LIMITS']},
            {'name': 'k8s-root-container', 'type': 'kubernetes', 'issues': ['RUN_AS_ROOT']},
            {'name': 'k8s-no-probes', 'type': 'kubernetes', 'issues': ['NO_LIVENESS_PROBE', 'NO_READINESS_PROBE']},
            {'name': 'k8s-latest-tag', 'type': 'kubernetes', 'issues': ['LATEST_IMAGE_TAG']},
            {'name': 'k8s-no-security-context', 'type': 'kubernetes', 'issues': ['NO_SECURITY_CONTEXT']},
            {'name': 'k8s-secure', 'type': 'kubernetes', 'issues': []},
            {'name': 'k8s-mixed-issues', 'type': 'kubernetes', 'issues': ['NO_RESOURCE_LIMITS', 'LATEST_IMAGE_TAG']},
            {'name': 'k8s-no-hpa', 'type': 'kubernetes', 'issues': ['NO_HPA']},
            {'name': 'k8s-privileged', 'type': 'kubernetes', 'issues': ['PRIVILEGED_CONTAINER']},
            {'name': 'k8s-host-network', 'type': 'kubernetes', 'issues': ['HOST_NETWORK']},
            {'name': 'k8s-no-network-policy', 'type': 'kubernetes', 'issues': ['NO_NETWORK_POLICY']},
            {'name': 'k8s-default-ns', 'type': 'kubernetes', 'issues': ['DEFAULT_NAMESPACE']},
            {'name': 'k8s-no-pdb', 'type': 'kubernetes', 'issues': ['NO_PDB']},
            {'name': 'k8s-complete-secure', 'type': 'kubernetes', 'issues': []},
            {'name': 'k8s-multiple-issues', 'type': 'kubernetes', 'issues': ['NO_RESOURCE_LIMITS', 'RUN_AS_ROOT', 'LATEST_IMAGE_TAG']},

            # Docker repos
            {'name': 'docker-root-user', 'type': 'dockerfile', 'issues': ['RUN_AS_ROOT']},
            {'name': 'docker-no-healthcheck', 'type': 'dockerfile', 'issues': ['NO_HEALTHCHECK']},
            {'name': 'docker-latest-base', 'type': 'dockerfile', 'issues': ['LATEST_BASE_IMAGE']},
            {'name': 'docker-add-root', 'type': 'dockerfile', 'issues': ['ADD_INSTRUCTION', 'RUN_AS_ROOT']},
            {'name': 'docker-no-user', 'type': 'dockerfile', 'issues': ['NO_USER_INSTRUCTION']},
            {'name': 'docker-secure', 'type': 'dockerfile', 'issues': []},
            {'name': 'docker-curl-pipe', 'type': 'dockerfile', 'issues': ['CURL_PIPE_BASH']},
            {'name': 'docker-apt-no-clean', 'type': 'dockerfile', 'issues': ['APT_NO_CLEANUP']},
            {'name': 'docker-expose-all', 'type': 'dockerfile', 'issues': ['EXPOSE_ALL_PORTS']},
            {'name': 'docker-mixed-issues', 'type': 'dockerfile', 'issues': ['RUN_AS_ROOT', 'LATEST_BASE_IMAGE', 'NO_HEALTHCHECK']},
            {'name': 'docker-multi-stage', 'type': 'dockerfile', 'issues': []},
            {'name': 'docker-alpine', 'type': 'dockerfile', 'issues': []},
            {'name': 'docker-node-root', 'type': 'dockerfile', 'issues': ['RUN_AS_ROOT', 'NO_HEALTHCHECK']},
            {'name': 'docker-python-insecure', 'type': 'dockerfile', 'issues': ['RUN_AS_ROOT', 'LATEST_BASE_IMAGE']},
            {'name': 'docker-complete-secure', 'type': 'dockerfile', 'issues': []},

            # CI/CD repos
            {'name': 'cicd-no-security-scan', 'type': 'cicd', 'issues': ['NO_SECURITY_SCAN']},
            {'name': 'cicd-no-tests', 'type': 'cicd', 'issues': ['NO_TESTS']},
            {'name': 'cicd-hardcoded-secrets', 'type': 'cicd', 'issues': ['HARDCODED_SECRETS']},
            {'name': 'cicd-no-oidc', 'type': 'cicd', 'issues': ['NO_OIDC_AUTH']},
            {'name': 'cicd-no-cache', 'type': 'cicd', 'issues': ['NO_CACHING']},
            {'name': 'cicd-secure', 'type': 'cicd', 'issues': []},
            {'name': 'cicd-no-approval', 'type': 'cicd', 'issues': ['NO_APPROVAL_GATE']},
            {'name': 'cicd-no-container-scan', 'type': 'cicd', 'issues': ['NO_CONTAINER_SCAN']},
            {'name': 'cicd-no-terraform-validate', 'type': 'cicd', 'issues': ['NO_TERRAFORM_VALIDATE']},
            {'name': 'cicd-multiple-issues', 'type': 'cicd', 'issues': ['NO_SECURITY_SCAN', 'NO_TESTS', 'HARDCODED_SECRETS']},
            {'name': 'cicd-complete-secure', 'type': 'cicd', 'issues': []},
            {'name': 'cicd-github-actions', 'type': 'cicd', 'issues': ['NO_SECURITY_SCAN']},
            {'name': 'cicd-gitlab-ci', 'type': 'cicd', 'issues': ['NO_TESTS']},
            {'name': 'cicd-jenkins', 'type': 'cicd', 'issues': ['NO_SECURITY_SCAN', 'NO_TESTS']},
            {'name': 'cicd-mixed-good', 'type': 'cicd', 'issues': ['NO_CACHING']},
        ]

        repos = []
        for config in synthetic_configs:
            repo_path = self.repos_dir / config['name']
            repo_path.mkdir(parents=True, exist_ok=True)

            # Create expected findings file
            expected_file = repo_path / 'expected_findings.json'
            expected_data = {
                'expected_findings': [
                    {'rule_id': issue, 'file': self._get_sample_file(config['type'])}
                    for issue in config['issues']
                ]
            }
            expected_file.write_text(json.dumps(expected_data, indent=2))

            # Create sample infrastructure file
            sample_file_name = self._get_sample_file(config['type'])
            sample_file = repo_path / sample_file_name
            
            # Create parent directories if needed (e.g., .github/workflows/)
            sample_file.parent.mkdir(parents=True, exist_ok=True)
            sample_file.write_text(self._get_sample_content(config['type'], config['issues']))

            repos.append(repo_path)

        print(f"Created {len(repos)} synthetic repositories")
        return repos

    def _get_sample_file(self, repo_type: str) -> str:
        """Get sample file name for repo type."""
        if repo_type == 'terraform':
            return 'main.tf'
        elif repo_type == 'kubernetes':
            return 'deployment.yaml'
        elif repo_type == 'dockerfile':
            return 'Dockerfile'
        elif repo_type == 'cicd':
            return '.github/workflows/ci.yml'
        return 'main.tf'

    def _get_sample_content(self, repo_type: str, issues: List[str]) -> str:
        """Generate sample content with specific issues."""
        if repo_type == 'terraform':
            return self._generate_terraform_content(issues)
        elif repo_type == 'kubernetes':
            return self._generate_kubernetes_content(issues)
        elif repo_type == 'dockerfile':
            return self._generate_dockerfile_content(issues)
        elif repo_type == 'cicd':
            return self._generate_cicd_content(issues)
        return ""

    def _generate_terraform_content(self, issues: List[str]) -> str:
        """Generate Terraform content with specific issues."""
        content = []

        if 'S3_PUBLIC_ACL' in issues:
            content.append('''
resource "aws_s3_bucket" "public" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}
''')

        if 'S3_NO_ENCRYPTION' in issues:
            content.append('''
resource "aws_s3_bucket" "unencrypted" {
  bucket = "my-unencrypted-bucket"
}
''')

        if 'EBS_NO_ENCRYPTION' in issues:
            content.append('''
resource "aws_ebs_volume" "unencrypted" {
  availability_zone = "us-west-2a"
  size              = 100
}
''')

        if 'RDS_PUBLIC_ACCESS' in issues:
            content.append('''
resource "aws_db_instance" "public" {
  identifier           = "public-db"
  engine               = "postgres"
  publicly_accessible  = true
}
''')

        if 'SG_OPEN_INGRESS' in issues:
            content.append('''
resource "aws_security_group" "open" {
  name = "open-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
''')

        if 'NO_REMOTE_BACKEND' in issues or 'LOCAL_BACKEND' in issues:
            content.append('''
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
''')

        if 'NO_STATE_LOCKING' in issues:
            content.append('''
terraform {
  backend "s3" {
    bucket = "tf-state"
    key    = "state.tfstate"
    region = "us-east-1"
  }
}
''')

        if 'HARDCODED_SECRETS' in issues:
            content.append('''
resource "aws_db_instance" "secrets" {
  password = "supersecret123"
}
''')

        if 'MISSING_TAGS' in issues:
            content.append('''
resource "aws_s3_bucket" "untagged" {
  bucket = "untagged-bucket"
}
''')

        if 'UNPINNED_PROVIDERS' in issues:
            content.append('''
provider "aws" {
  region = "us-east-1"
}
''')

        if 'IAM_WILDCARD_PERMISSIONS' in issues:
            content.append('''
resource "aws_iam_policy" "wildcard" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:*"
      Resource = "*"
    }]
  })
}
''')

        # Add some secure resources if no issues
        if not issues:
            content.append('''
resource "aws_s3_bucket" "secure" {
  bucket = "secure-bucket"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Environment = "production"
    Owner       = "security-team"
  }
}
''')

        return "\n".join(content)

    def _generate_kubernetes_content(self, issues: List[str]) -> str:
        """Generate Kubernetes content with specific issues."""
        content = []

        if 'NO_RESOURCE_LIMITS' in issues or 'RUN_AS_ROOT' in issues or 'LATEST_IMAGE_TAG' in issues:
            deployment = '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: insecure-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: insecure
  template:
    metadata:
      labels:
        app: insecure
    spec:
      containers:
      - name: app
        image: myapp:latest
'''
            if 'NO_RESOURCE_LIMITS' in issues:
                # No resources section
                pass
            else:
                deployment += '''
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
'''

            if 'RUN_AS_ROOT' in issues:
                # No securityContext
                pass
            else:
                deployment += '''
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
'''

            if 'NO_LIVENESS_PROBE' not in issues:
                deployment += '''
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
'''

            content.append(deployment)

        if 'NO_HPA' in issues:
            content.append('''
# No HorizontalPodAutoscaler defined
''')

        if 'PRIVILEGED_CONTAINER' in issues:
            content.append('''
apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
spec:
  containers:
  - name: privileged
    image: ubuntu
    securityContext:
      privileged: true
''')

        if 'HOST_NETWORK' in issues:
            content.append('''
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true
  containers:
  - name: app
    image: nginx
''')

        # Secure deployment if no issues
        if not issues:
            content.append('''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secure
  template:
    metadata:
      labels:
        app: secure
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: app
        image: myapp:1.0.0
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
''')

        return "\n".join(content)

    def _generate_dockerfile_content(self, issues: List[str]) -> str:
        """Generate Dockerfile content with specific issues."""
        content = []

        if 'RUN_AS_ROOT' in issues or 'LATEST_BASE_IMAGE' in issues or 'NO_HEALTHCHECK' in issues:
            dockerfile = ''

            if 'LATEST_BASE_IMAGE' in issues:
                dockerfile += 'FROM node:latest\n\n'
            else:
                dockerfile += 'FROM node:18.17.0-alpine\n\n'

            dockerfile += '''
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
'''

            if 'RUN_AS_ROOT' in issues:
                # No USER instruction
                pass
            else:
                dockerfile += '''
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001
USER nodejs
'''

            if 'NO_HEALTHCHECK' in issues:
                # No HEALTHCHECK
                pass
            else:
                dockerfile += '''
HEALTHCHECK --interval=30s --timeout=3s \\
  CMD wget -q --spider http://localhost:3000/health || exit 1
'''

            content.append(dockerfile)

        if 'ADD_INSTRUCTION' in issues:
            content.append('''
FROM ubuntu:20.04
ADD https://example.com/file.tar.gz /app/
''')

        if 'CURL_PIPE_BASH' in issues:
            content.append('''
FROM ubuntu:20.04
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
''')

        if 'APT_NO_CLEANUP' in issues:
            content.append('''
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y python3
''')

        if 'EXPOSE_ALL_PORTS' in issues:
            content.append('''
FROM ubuntu:20.04
EXPOSE 1-65535
''')

        # Secure Dockerfile if no issues
        if not issues:
            content.append('''
FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

COPY . .

RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nodejs -u 1001

USER nodejs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s \\
  CMD wget -q --spider http://localhost:3000/health || exit 1

CMD ["node", "server.js"]
''')

        return "\n".join(content)

    def _generate_cicd_content(self, issues: List[str]) -> str:
        """Generate CI/CD content with specific issues."""
        content = []

        if 'NO_SECURITY_SCAN' in issues or 'NO_TESTS' in issues or 'HARDCODED_SECRETS' in issues:
            workflow = '''
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm install

      - name: Build
        run: npm run build
'''

            if 'NO_TESTS' not in issues:
                workflow += '''
      - name: Run tests
        run: npm test
'''

            if 'NO_SECURITY_SCAN' not in issues:
                workflow += '''
      - name: Security scan
        run: npm audit && npx snyk test
'''

            if 'HARDCODED_SECRETS' in issues:
                workflow += '''
      - name: Deploy
        run: |
          aws configure set aws_access_key_id AKIAIOSFODNN7EXAMPLE
          aws configure set aws_secret_access_key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
          aws s3 sync ./dist s3://my-bucket
'''
            else:
                workflow += '''
      - name: Deploy
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-role
          aws-region: us-east-1
'''

            content.append(workflow)

        if 'NO_OIDC_AUTH' in issues:
            content.append('''
      - name: Deploy without OIDC
        run: |
          echo "${{ secrets.AWS_SECRET_ACCESS_KEY }}" | aws configure set aws_secret_access_key
''')

        if 'NO_CACHING' in issues:
            # No cache steps
            pass
        else:
            content.append('''
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
''')

        if 'NO_APPROVAL_GATE' in issues:
            content.append('''
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: ./deploy.sh
''')
        else:
            content.append('''
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Deploy to production
        run: ./deploy.sh
''')

        # Secure workflow if no issues
        if not issues:
            content.append('''
name: Secure CI/CD

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4

      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Security scan
        run: npm audit && npx snyk test

      - name: Build
        run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-role
          aws-region: us-east-1

      - name: Deploy
        run: ./deploy.sh
''')

        return "\n".join(content)

    def generate_report(self, output_path: Path) -> str:
        """Generate markdown accuracy report."""
        report = []

        # Header
        report.append("# Rule Engine Accuracy Report")
        report.append("")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        report.append("## Summary")
        report.append("")
        report.append(f"- **Repositories tested:** {self.metrics.repositories_tested}")
        report.append(f"- **Total files scanned:** {self.metrics.total_files_scanned}")
        report.append(f"- **Total findings:** {self.metrics.total_findings}")
        report.append(f"- **Scan duration:** {self.metrics.total_duration:.2f}s")
        report.append("")

        # Accuracy Metrics
        report.append("## Accuracy Metrics")
        report.append("")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| True Positives | {self.metrics.true_positives} |")
        report.append(f"| False Positives | {self.metrics.false_positives} |")
        report.append(f"| False Negatives | {self.metrics.false_negatives} |")
        report.append(f"| **Accuracy** | **{self.metrics.accuracy:.1f}%** |")
        report.append(f"| Precision | {self.metrics.precision:.1f}% |")
        report.append(f"| Recall | {self.metrics.recall:.1f}% |")
        report.append(f"| F1 Score | {self.metrics.f1_score:.1f}% |")
        report.append(f"| False Positive Rate | {self.metrics.false_positive_rate:.1f}% |")
        report.append(f"| False Negative Rate | {self.metrics.false_negative_rate:.1f}% |")
        report.append("")

        # Per Repository Results
        report.append("## Per Repository Results")
        report.append("")
        report.append("| Repository | Files | Findings | TP | FP | FN | Duration |")
        report.append("|------------|-------|----------|----|----|----|---------|")

        for result in sorted(self.results, key=lambda r: r.repository):
            report.append(
                f"| {result.repository} | {result.files_scanned} | {result.findings_count} | "
                f"{result.true_positives} | {result.false_positives} | {result.false_negatives} | "
                f"{result.scan_duration:.2f}s |"
            )

        report.append("")

        # Rule Performance
        report.append("## Rule Performance")
        report.append("")

        # Aggregate rule statistics
        rule_stats: Dict[str, Dict[str, int]] = {}
        for result in self.results:
            for finding in result.findings:
                rule_id = finding['rule_id']
                if rule_id not in rule_stats:
                    rule_stats[rule_id] = {'triggered': 0, 'correct': 0, 'incorrect': 0}
                rule_stats[rule_id]['triggered'] += 1

                # Check if this finding was expected
                expected_rules = {e.rule_id for e in result.expected_findings}
                if rule_id in expected_rules:
                    rule_stats[rule_id]['correct'] += 1
                else:
                    rule_stats[rule_id]['incorrect'] += 1

        report.append("| Rule ID | Triggered | Correct | Incorrect |")
        report.append("|---------|-----------|---------|-----------|")

        for rule_id in sorted(rule_stats.keys()):
            stats = rule_stats[rule_id]
            report.append(
                f"| {rule_id} | {stats['triggered']} | {stats['correct']} | {stats['incorrect']} |"
            )

        report.append("")

        # Observations
        report.append("## Observations")
        report.append("")

        # Identify problematic rules
        high_fp_rules = [
            (rule_id, stats)
            for rule_id, stats in rule_stats.items()
            if stats['incorrect'] > stats['correct']
        ]

        if high_fp_rules:
            report.append("### Rules with High False Positive Rate")
            report.append("")
            for rule_id, stats in high_fp_rules:
                report.append(f"- **{rule_id}**: {stats['incorrect']} false positives out of {stats['triggered']} triggers")
            report.append("")

        # Identify missed detections
        high_fn_repos = [
            r for r in self.results
            if r.false_negatives > 0
        ]

        if high_fn_repos:
            report.append("### Repositories with Missed Detections")
            report.append("")
            for repo in high_fn_repos[:10]:  # Top 10
                report.append(f"- **{repo.repository}**: {repo.false_negatives} findings missed")
            report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        if high_fp_rules:
            report.append("1. **Review high false-positive rules:**")
            for rule_id, _ in high_fp_rules[:5]:
                report.append(f"   - Refine detection logic for `{rule_id}`")
            report.append("")

        if high_fn_repos:
            report.append("2. **Improve detection coverage:**")
            report.append("   - Add more test cases for edge cases")
            report.append("   - Review parser extraction logic")
            report.append("")

        report.append("3. **General improvements:**")
        report.append("   - Add semantic analysis for context-aware detection")
        report.append("   - Implement rule confidence scoring")
        report.append("   - Add automated rule testing in CI/CD")
        report.append("")

        # Performance
        report.append("## Performance Metrics")
        report.append("")
        avg_files = self.metrics.total_files_scanned / max(1, self.metrics.repositories_tested)
        avg_findings = self.metrics.total_findings / max(1, self.metrics.repositories_tested)
        avg_duration = self.metrics.total_duration / max(1, self.metrics.repositories_tested)

        report.append(f"- **Average files per repo:** {avg_files:.1f}")
        report.append(f"- **Average findings per repo:** {avg_findings:.1f}")
        report.append(f"- **Average scan time per repo:** {avg_duration:.2f}s")
        report.append(f"- **Files scanned per second:** {self.metrics.total_files_scanned / max(0.001, self.metrics.total_duration):.1f}")
        report.append("")

        report_text = "\n".join(report)

        # Write report
        output_path.write_text(report_text)

        return report_text

    def save_results(self, output_dir: Path) -> None:
        """Save test results to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save scan results
        scan_results = {
            'timestamp': datetime.now().isoformat(),
            'metrics': asdict(self.metrics),
            'repositories': [
                {
                    'name': r.repository,
                    'files_scanned': r.files_scanned,
                    'findings_count': r.findings_count,
                    'true_positives': r.true_positives,
                    'false_positives': r.false_positives,
                    'false_negatives': r.false_negatives,
                    'duration': r.scan_duration,
                    'findings': r.findings,
                }
                for r in self.results
            ],
        }

        (output_dir / 'scan_results.json').write_text(
            json.dumps(scan_results, indent=2)
        )

        # Save accuracy metrics
        (output_dir / 'accuracy_metrics.json').write_text(
            json.dumps(asdict(self.metrics), indent=2)
        )


def main():
    """Main entry point."""
    # Setup paths
    backend_dir = Path(__file__).parent.parent / "backend"
    repos_dir = backend_dir / "tests" / "repositories"
    output_dir = backend_dir / "tests" / "results"

    print("=" * 70)
    print("DevArchAI Rule Engine Accuracy Test")
    print("=" * 70)
    print()

    # Create tester
    tester = RuleEngineAccuracyTester(repos_dir)

    # Run tests
    metrics = tester.run_tests()

    # Generate report
    report_path = output_dir / 'test_report_repo.md'
    report = tester.generate_report(report_path)

    # Save results
    tester.save_results(output_dir)

    print()
    print(f"Report saved to: {report_path}")
    print(f"Scan results saved to: {output_dir / 'scan_results.json'}")
    print(f"Accuracy metrics saved to: {output_dir / 'accuracy_metrics.json'}")
    print()
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)

    return 0 if metrics.accuracy >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
