"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_dockerfile_content():
    """Sample Dockerfile content for testing."""
    return """FROM node:latest

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
"""


@pytest.fixture
def sample_dockerfile_with_user():
    """Sample Dockerfile with non-root user."""
    return """FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 3000

CMD ["node", "server.js"]
"""


@pytest.fixture
def sample_kubernetes_deployment():
    """Sample Kubernetes deployment without best practices."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "my-app",
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "my-app"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "my-app"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "myapp:latest",
                            "ports": [
                                {"containerPort": 8080}
                            ]
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_kubernetes_deployment_secure():
    """Sample Kubernetes deployment with security best practices."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "my-app",
        },
        "spec": {
            "replicas": 3,
            "selector": {
                "matchLabels": {
                    "app": "my-app"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "my-app"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "myapp:1.0.0",
                            "ports": [
                                {"containerPort": 8080}
                            ],
                            "resources": {
                                "requests": {
                                    "memory": "256Mi",
                                    "cpu": "250m"
                                },
                                "limits": {
                                    "memory": "512Mi",
                                    "cpu": "500m"
                                }
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/healthz",
                                    "port": 8080
                                },
                                "initialDelaySeconds": 30
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/ready",
                                    "port": 8080
                                },
                                "initialDelaySeconds": 5
                            },
                            "securityContext": {
                                "runAsNonRoot": True,
                                "runAsUser": 1000
                            }
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_terraform_s3_public():
    """Sample Terraform with public S3 bucket."""
    return {
        "resources": [
            {
                "type": "aws_s3_bucket",
                "name": "data_bucket",
                "values": {
                    "bucket": "my-data-bucket",
                    "acl": "public-read"
                }
            }
        ]
    }


@pytest.fixture
def sample_terraform_s3_private():
    """Sample Terraform with private S3 bucket."""
    return {
        "resources": [
            {
                "type": "aws_s3_bucket",
                "name": "data_bucket",
                "values": {
                    "bucket": "my-data-bucket",
                    "acl": "private",
                    "server_side_encryption_configuration": {
                        "rule": {
                            "apply_server_side_encryption_by_default": {
                                "sse_algorithm": "AES256"
                            }
                        }
                    },
                    "versioning": {
                        "enabled": True
                    }
                }
            }
        ]
    }


@pytest.fixture
def sample_rule_findings():
    """Sample rule findings for testing."""
    from app.rule_engine.base import Category, RuleFinding, Severity

    return [
        RuleFinding(
            rule_id="DOCKER-001",
            rule_name="Container Runs as Root",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Container runs as root user",
            recommendation="Add USER instruction",
            file_path="Dockerfile",
        ),
        RuleFinding(
            rule_id="K8S-001",
            rule_name="Missing Resource Limits",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="Container has no resource limits",
            recommendation="Set CPU and memory limits",
            file_path="k8s/deployment.yaml",
        ),
        RuleFinding(
            rule_id="TF-001",
            rule_name="Public S3 Bucket",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            description="S3 bucket has public ACL",
            recommendation="Set ACL to private",
            file_path="terraform/s3.tf",
        ),
    ]
