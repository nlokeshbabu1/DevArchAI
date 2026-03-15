"""Findings enrichment service - adds risk, impact, and fix examples."""

from typing import Any

import structlog

from app.rule_engine.base import RuleFinding

logger = structlog.get_logger(__name__)


# Fix examples library organized by rule_id pattern
FIX_EXAMPLES: dict[str, dict[str, Any]] = {
    # Terraform State Management
    "TF-STATE-001": {
        "risk": "Terraform state stored locally cannot be shared across team members or CI/CD pipelines, leading to state drift, failed applies, and potential infrastructure corruption.",
        "impact": "Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift and deployment failures.",
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
    },
    "TF-STATE-002": {
        "risk": "Without remote backend, Terraform state is stored locally, preventing team collaboration and risking state loss if the local file is deleted.",
        "impact": "Team members cannot collaborate on infrastructure changes. State loss results in inability to manage existing resources.",
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
  }
}''',
    },
    "TF-STATE-003": {
        "risk": "Without state locking, concurrent terraform apply operations can corrupt the state file, leading to infrastructure drift and failed deployments.",
        "impact": "State corruption can cause Terraform to lose track of resources, resulting in duplicate resources or orphaned infrastructure.",
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"  # Enables locking
    encrypt        = true
  }
}

# Or for Terraform 1.10+:
terraform {
  backend "s3" {
    bucket        = "tf-state-prod"
    key           = "terraform.tfstate"
    region        = "us-east-1"
    use_lockfile  = true  # Built-in file-based locking
  }
}''',
    },
    "TF-STATE-004": {
        "risk": "Unencrypted Terraform state may contain sensitive information (passwords, keys, connection strings) that could be exposed if the state storage is compromised.",
        "impact": "Exposure of state file could lead to credential theft, unauthorized access to cloud resources, and compliance violations.",
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true  # Enable server-side encryption
    dynamodb_table = "terraform-lock"
  }
}''',
    },
    # Terraform Provider Rules
    "TF-PROV-001": {
        "risk": "Unpinned provider versions can introduce breaking changes during terraform init, causing unexpected behavior or deployment failures.",
        "impact": "Provider updates may change resource behavior, causing infrastructure drift or failed deployments in production.",
        "fix_example": '''terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # Allows 5.x.x but not 6.0.0
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0, < 4.0"
    }
  }
}''',
    },
    "TF-PROV-002": {
        "risk": "Providers from untrusted sources may contain malicious code that compromises your infrastructure or exfiltrates sensitive data.",
        "impact": "Supply chain attacks through malicious providers can lead to complete infrastructure compromise.",
        "fix_example": '''terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"  # Official HashiCorp registry
      version = "~> 5.0"
    }
  }
}

# Always verify provider source:
# - Official: hashicorp/*
# - Verified: terraform-providers/*
# - Avoid: Unknown organization sources''',
    },
    # Terraform Secrets
    "TF-SEC-001": {
        "risk": "Hardcoded secrets in Terraform files are stored in version control and state files, exposing credentials to anyone with repository or state access.",
        "impact": "Credential exposure can lead to unauthorized access, data breaches, and significant compliance violations (SOC2, HIPAA, PCI-DSS).",
        "fix_example": '''# Use variables with sensitive flag
variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Reference from AWS Secrets Manager
data "aws_secretsmanager_secret_version" "db_creds" {
  secret_id = "prod/db/credentials"
}

resource "aws_db_instance" "main" {
  password = data "aws_secretsmanager_secret_version" "db_creds".secret_string
}

# Or use environment variables
# export TF_VAR_db_password="secure-password"''',
    },
    # Terraform Encryption Rules
    "TF-ENC-001": {
        "risk": "Unencrypted S3 buckets expose stored data to unauthorized access if bucket policies are misconfigured or if AWS account is compromised.",
        "impact": "Data breaches, compliance violations (GDPR, HIPAA, PCI-DSS), and potential regulatory fines.",
        "fix_example": '''resource "aws_s3_bucket" "data" {
  bucket = "my-secure-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}''',
    },
    "TF-ENC-002": {
        "risk": "Unencrypted EBS volumes expose data at rest, allowing anyone with disk access to read sensitive information.",
        "impact": "Data breaches if instances are compromised, compliance violations, and potential data leakage from terminated instances.",
        "fix_example": '''resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-west-2a"
  size              = 40
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
}

resource "aws_instance" "secure" {
  ami           = "ami-12345678"
  instance_type = "t3.micro"

  root_block_device {
    encrypted   = true
    kms_key_id  = aws_kms_key.ebs.arn
    volume_size = 50
  }
}''',
    },
    "TF-ENC-003": {
        "risk": "Unencrypted databases expose sensitive data at rest, including PII, financial data, and application secrets.",
        "impact": "Data breaches, compliance violations (HIPAA, PCI-DSS, SOC2), regulatory fines, and reputational damage.",
        "fix_example": '''resource "aws_db_instance" "secure" {
  identifier           = "secure-db"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.db.arn
  publicly_accessible  = false
  skip_final_snapshot  = false
}

resource "aws_rds_cluster" "secure" {
  cluster_identifier     = "secure-aurora"
  engine                 = "aurora-postgresql"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.db.arn
  master_username        = var.db_username
  master_password        = var.db_password
}''',
    },
    # Terraform Networking Rules
    "TF-NET-001": {
        "risk": "Security groups allowing 0.0.0.0/0 expose services directly to the internet, making them vulnerable to brute force attacks, exploits, and unauthorized access.",
        "impact": "Critical services (SSH, RDP, databases) exposed to the internet can be compromised, leading to data breaches, ransomware, or cryptomining.",
        "fix_example": '''# Restrict SSH to specific IP ranges
resource "aws_security_group" "restricted" {
  name        = "restricted-sg"
  description = "Security group with restricted access"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from trusted IPs only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8", "192.168.1.0/24"]  # Internal networks only
  }

  # Use VPC endpoints instead of public access
  ingress {
    description = "HTTPS from VPC only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}''',
    },
    "TF-NET-002": {
        "risk": "Publicly accessible databases can be discovered and attacked from the internet, exposing sensitive data to unauthorized access.",
        "impact": "Data breaches, SQL injection attacks, credential stuffing, and complete database compromise.",
        "fix_example": '''resource "aws_db_instance" "private" {
  identifier           = "private-db"
  engine               = "postgres"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  publicly_accessible  = false  # Must be false
  db_subnet_group_name = aws_db_subnet_group.private.name
  vpc_security_group_ids = [aws_security_group.db.id]

  # Access via bastion host or VPC endpoint
}

resource "aws_security_group" "db" {
  name        = "db-sg"
  description = "Database security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from app servers only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]  # Reference app SG
  }
}''',
    },
    # Terraform IAM Rules
    "TF-IAM-001": {
        "risk": "Wildcard IAM permissions (*) violate the principle of least privilege, granting excessive access that can be exploited if credentials are compromised.",
        "impact": "Compromised credentials with wildcard permissions can lead to complete account takeover, data exfiltration, or resource destruction.",
        "fix_example": '''# Instead of wildcard permissions:
# ❌ BAD:
resource "aws_iam_policy" "bad" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:*"  # Too permissive
      Resource = "*"
    }]
  })
}

# ✅ GOOD: Specific permissions
resource "aws_iam_policy" "good" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.app.arn,
        "${aws_s3_bucket.app.arn}/*"
      ]
    }]
  })
}''',
    },
    "TF-IAM-002": {
        "risk": "NotAction is counter-intuitive and can grant unintended permissions when new AWS services or actions are added.",
        "impact": "Policy may grant more access than intended, especially as AWS adds new service actions.",
        "fix_example": '''# Instead of NotAction:
# ❌ BAD - unclear what is actually allowed
resource "aws_iam_policy" "bad" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect      = "Allow"
      NotAction   = ["iam:*", "organizations:*"]
      Resource    = "*"
    }]
  })
}

# ✅ GOOD - Explicit actions
resource "aws_iam_policy" "good" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:Describe*",
        "s3:GetObject",
        "s3:ListBucket",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "*"
    }]
  })
}''',
    },
    # Terraform Tags
    "TF-TAG-001": {
        "risk": "Missing tags make it difficult to track resource ownership, allocate costs, enforce policies, and manage resources at scale.",
        "impact": "Inability to identify resource owners during incidents, inaccurate cost allocation, and compliance audit failures.",
        "fix_example": '''# Define default tags
locals {
  default_tags = {
    Environment = var.environment
    Owner       = var.owner
    Project     = var.project
    CostCenter  = var.cost_center
    ManagedBy   = "terraform"
  }
}

# Apply to all resources
resource "aws_s3_bucket" "data" {
  bucket = "my-bucket"

  tags = merge(local.default_tags, {
    Name        = "data-bucket"
    Description = "Primary data storage"
  })
}

# Or use provider-level default tags
provider "aws" {
  default_tags {
    tags = local.default_tags
  }
}''',
    },
    # Kubernetes Rules
    "K8S-001": {
        "risk": "Containers without resource limits can consume all node resources, causing node instability and affecting other workloads.",
        "impact": "Resource exhaustion leads to node crashes, pod evictions, and service outages affecting all applications on the node.",
        "fix_example": '''apiVersion: v1
kind: Pod
metadata:
  name: resource-limited-pod
spec:
  containers:
  - name: app
    image: myapp:1.0.0
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"''',
    },
    "K8S-002": {
        "risk": "Containers running as root have full access to the host system if they escape the container, increasing the blast radius of exploits.",
        "impact": "Container breakout vulnerabilities can lead to full host compromise, lateral movement, and cluster-wide attacks.",
        "fix_example": '''apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: app
    image: myapp:1.0.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL''',
    },
    # Docker Rules
    "DOCKER-001": {
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host system.",
        "impact": "Root container access increases attack surface and potential damage from container breakout exploits.",
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nodejs -u 1001

USER nodejs

EXPOSE 3000

CMD ["node", "server.js"]''',
    },
    "DOCKER-002": {
        "risk": "Using 'latest' tag leads to non-deterministic builds, making it impossible to reproduce builds or rollback to known-good versions.",
        "impact": "Unexpected base image changes can introduce vulnerabilities, breaking changes, or compatibility issues.",
        "fix_example": '''# Pin specific version
FROM node:18.17.0-alpine3.18

# Or use digest for immutability
FROM node@sha256:abc123def456...

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER nodejs
CMD ["node", "server.js"]''',
    },
    # CI/CD Rules
    "CICD-001": {
        "risk": "CI/CD pipelines without proper secrets management expose credentials in logs, environment variables, or configuration files.",
        "impact": "Exposed credentials can be used to compromise cloud infrastructure, deploy malicious code, or access sensitive data.",
        "fix_example": '''# GitHub Actions - Use secrets
name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/github-role
        aws-region: us-east-1

    # Never echo secrets or print them in logs
    - name: Deploy
      run: |
        echo "Deploying..."
        # AWS credentials are automatically available''',
    },
}


class FindingsEnricher:
    """Enrich findings with risk, impact, and fix examples."""

    def __init__(self):
        self._fix_examples = FIX_EXAMPLES

    def enrich_finding(self, finding: RuleFinding) -> RuleFinding:
        """
        Enrich a single finding with risk, impact, and fix example.

        Args:
            finding: The finding to enrich

        Returns:
            Finding with enrichment fields populated
        """
        # Look up fix example by rule_id
        fix_data = self._fix_examples.get(finding.rule_id, {})

        # Apply enrichment (only if not already set)
        if not finding.risk and "risk" in fix_data:
            finding.risk = fix_data["risk"]
        if not finding.impact and "impact" in fix_data:
            finding.impact = fix_data["impact"]
        if not finding.fix_example and "fix_example" in fix_data:
            finding.fix_example = fix_data["fix_example"]

        return finding

    def enrich_findings(self, findings: list[RuleFinding]) -> list[RuleFinding]:
        """
        Enrich multiple findings with risk, impact, and fix examples.

        Args:
            findings: List of findings to enrich

        Returns:
            List of enriched findings
        """
        enriched = []
        for finding in findings:
            enriched.append(self.enrich_finding(finding))

        logger.info(
            "Findings enriched",
            total_count=len(findings),
            enriched_count=sum(1 for f in enriched if f.risk or f.impact or f.fix_example),
        )

        return enriched


def enrich_findings(findings: list[RuleFinding]) -> list[RuleFinding]:
    """Convenience function to enrich findings."""
    enricher = FindingsEnricher()
    return enricher.enrich_findings(findings)
