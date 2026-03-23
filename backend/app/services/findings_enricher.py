"""Findings enrichment service - adds risk, impact, fix examples, and documentation links.

Now supports:
- Static FIX_EXAMPLES (fallback)
- AI-powered dynamic enrichment (for HIGH/CRITICAL)
- Documentation URL mapping
"""

import hashlib
import json
from typing import Any, Optional

import structlog

from app.ai.engine import BaseLLMProvider, get_llm_provider
from app.config import settings
from app.rule_engine.base import RuleFinding
from app.services.devops_documentation import get_documentation_url

logger = structlog.get_logger(__name__)


# Fix examples library organized by rule_id pattern (STATIC FALLBACK)
FIX_EXAMPLES: dict[str, dict[str, Any]] = {
    # Terraform State Management
    "TF-STATE-001": {
        "summary": "Terraform state is stored locally without remote backend configuration.",
        "risk": "Terraform state stored locally cannot be shared across team members or CI/CD pipelines, leading to state drift, failed applies, and potential infrastructure corruption.",
        "impact": "Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift and deployment failures.",
        "fix_code": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "best_practices": [
            "Use separate state files for different environments",
            "Enable versioning on the S3 bucket",
            "Restrict IAM access to state bucket",
        ],
        "confidence": 0.95,
    },
    "TF-STATE-002": {
        "summary": "Terraform is using local state storage instead of remote backend.",
        "risk": "Without remote backend, Terraform state is stored locally, preventing team collaboration and risking state loss if the local file is deleted.",
        "impact": "Team members cannot collaborate on infrastructure changes. State loss results in inability to manage existing resources.",
        "fix_code": '''terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
  }
}''',
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
  }
}''',
        "best_practices": [
            "Use DynamoDB for state locking",
            "Enable encryption for state files",
        ],
        "confidence": 0.95,
    },
    "TF-STATE-003": {
        "summary": "Terraform state backend is missing locking configuration.",
        "risk": "Without state locking, concurrent terraform apply operations can corrupt the state file, leading to infrastructure drift and failed deployments.",
        "impact": "State corruption can cause Terraform to lose track of resources, resulting in duplicate resources or orphaned infrastructure.",
        "fix_code": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "best_practices": [
            "Use DynamoDB table with pay-per-request billing",
            "Enable state file versioning",
        ],
        "confidence": 0.95,
    },
    "TF-STATE-004": {
        "summary": "Terraform state file is not encrypted at rest.",
        "risk": "Unencrypted Terraform state may contain sensitive information (passwords, keys, connection strings) that could be exposed if the state storage is compromised.",
        "impact": "Exposure of state file could lead to credential theft, unauthorized access to cloud resources, and compliance violations.",
        "fix_code": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}''',
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}''',
        "best_practices": [
            "Enable server-side encryption with KMS",
            "Use bucket policies to enforce encryption",
        ],
        "confidence": 0.95,
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
  }
}''',
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
}''',
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
}''',
    },
    "TF-ENC-003": {
        "risk": "Unencrypted databases expose sensitive data at rest, including PII, financial data, and application secrets.",
        "impact": "Data breaches, compliance violations (HIPAA, PCI-DSS, SOC2), regulatory fines, and reputational damage.",
        "fix_example": '''resource "aws_db_instance" "secure" {
  identifier           = "secure-db"
  engine               = "postgres"
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.db.arn
  publicly_accessible  = false
}''',
    },
    # Terraform Networking Rules
    "TF-NET-001": {
        "risk": "Security groups allowing 0.0.0.0/0 expose services directly to the internet, making them vulnerable to brute force attacks, exploits, and unauthorized access.",
        "impact": "Critical services (SSH, RDP, databases) exposed to the internet can be compromised, leading to data breaches, ransomware, or cryptomining.",
        "fix_example": '''# Restrict SSH to specific IP ranges
resource "aws_security_group" "restricted" {
  name        = "restricted-sg"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from trusted IPs only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8", "192.168.1.0/24"]
  }
}''',
    },
    "TF-NET-002": {
        "risk": "Publicly accessible databases can be discovered and attacked from the internet, exposing sensitive data to unauthorized access.",
        "impact": "Data breaches, SQL injection attacks, credential stuffing, and complete database compromise.",
        "fix_example": '''resource "aws_db_instance" "private" {
  publicly_accessible  = false  # Must be false
  db_subnet_group_name = aws_db_subnet_group.private.name
}''',
    },
    # Terraform IAM Rules
    "TF-IAM-001": {
        "risk": "Wildcard IAM permissions (*) violate the principle of least privilege, granting excessive access that can be exploited if credentials are compromised.",
        "impact": "Compromised credentials with wildcard permissions can lead to complete account takeover, data exfiltration, or resource destruction.",
        "fix_example": '''# ✅ GOOD: Specific permissions
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
    ManagedBy   = "terraform"
  }
}

# Apply to all resources
resource "aws_s3_bucket" "data" {
  tags = local.default_tags
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
  containers:
  - name: app
    image: myapp:1.0.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
          - ALL''',
    },
    "K8S-REL-001": {
        "risk": "Single replica deployments have no redundancy and will cause complete service outage during pod failures or node maintenance.",
        "impact": "Service downtime during pod failures, updates, or node maintenance. No high availability.",
        "fix_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  replicas: 3  # Run multiple replicas for HA
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0.0''',
    },
    "K8S-REL-002": {
        "risk": "Without PodDisruptionBudget, voluntary disruptions (node drains, cluster upgrades) can take down all pods simultaneously, causing service outage.",
        "impact": "Service downtime during cluster maintenance, node upgrades, or scaling operations.",
        "fix_example": '''apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 1  # Keep at least 1 pod running
  selector:
    matchLabels:
      app: myapp

# Or use maxUnavailable:
# spec:
#   maxUnavailable: 1  # Allow only 1 pod to be unavailable''',
    },
    "K8S-REL-003": {
        "risk": "Without liveness probes, Kubernetes cannot detect if a container is deadlocked or stuck, leading to traffic being sent to non-functional pods.",
        "impact": "Service degradation as traffic routes to unresponsive containers. No automatic recovery.",
        "fix_example": '''apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: myapp:1.0.0
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 3
      periodSeconds: 3''',
    },
    "K8S-SEC-001": {
        "risk": "Pods without security context run with default privileges, potentially as root, increasing attack surface.",
        "impact": "Privilege escalation, container breakout, and host compromise risks.",
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
    "K8S-SCALE-001": {
        "summary": "No HorizontalPodAutoscaler configured for automatic scaling.",
        "risk": "Without HorizontalPodAutoscaler, applications cannot scale based on demand, leading to poor performance during traffic spikes or wasted resources during low usage.",
        "impact": "Service degradation during traffic spikes. Over-provisioning during low usage.",
        "fix_code": '''apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70''',
        "fix_example": '''apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70''',
        "best_practices": [
            "Set appropriate min/max replicas based on load patterns",
            "Use multiple metrics (CPU, memory, custom) for scaling decisions",
            "Configure scale-down stabilization to prevent flapping",
        ],
        "confidence": 0.95,
    },
    "K8S-REL-002": {
        "summary": "No PodDisruptionBudget configured for voluntary disruptions.",
        "risk": "Without PodDisruptionBudget, voluntary disruptions (node drains, cluster upgrades) can take down all pods simultaneously, causing service outages.",
        "impact": "Service downtime during maintenance, cluster upgrades, or node pool changes.",
        "fix_code": '''apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: myapp''',
        "fix_example": '''apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: production
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: myapp
      tier: backend''',
        "best_practices": [
            "Set minAvailable based on application requirements",
            "Use maxUnavailable for stateless applications",
            "Consider PDB for all critical workloads",
        ],
        "confidence": 0.95,
    },
    "K8S-OBS-001": {
        "summary": "Missing observability configuration for monitoring and alerting.",
        "risk": "Without proper observability, issues go undetected until they impact users. Debugging production issues becomes difficult.",
        "impact": "Increased MTTR, poor visibility into application health, missed SLA breaches.",
        "fix_code": '''# Add Prometheus annotations for scraping
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"''',
        "fix_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 8080
          name: metrics
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"''',
        "best_practices": [
            "Expose metrics on standard /metrics endpoint",
            "Add structured logging with correlation IDs",
            "Configure distributed tracing for microservices",
        ],
        "confidence": 0.90,
    },
    "CI-SEC-003": {
        "summary": "CI/CD pipeline secrets may not be properly managed.",
        "risk": "Hardcoded or improperly managed secrets in CI/CD can be exposed in logs, build artifacts, or source control.",
        "impact": "Credential theft, unauthorized access to cloud resources, supply chain attacks.",
        "fix_code": '''# Use GitHub Secrets for sensitive values
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}

# Or use OIDC for cloud provider auth
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/github-actions
    aws-region: us-east-1''',
        "fix_example": '''name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Use OIDC for AWS (preferred)
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/github-actions
        aws-region: us-east-1
    
    # Use secrets for application config
    - name: Deploy
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        API_KEY: ${{ secrets.API_KEY }}
      run: |
        ./deploy.sh''',
        "best_practices": [
            "Use OIDC instead of long-lived credentials",
            "Never print secrets in logs",
            "Rotate secrets regularly",
            "Use environment-specific secrets",
        ],
        "confidence": 0.95,
    },
    "CI-SCALE-001": {
        "summary": "CI/CD pipeline not optimized for scale and performance.",
        "risk": "Slow builds waste developer time and increase CI/CD costs. Lack of caching leads to redundant work.",
        "impact": "Increased build times, higher CI/CD costs, slower release cycles.",
        "fix_code": '''# Add dependency caching
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-''',
        "fix_example": '''name: CI Pipeline
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Cache dependencies
    - name: Cache node modules
      uses: actions/cache@v4
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-
    
    # Use matrix for parallel testing
    - name: Test
      strategy:
        matrix:
          node-version: [16, 18, 20]
      run: npm test''',
        "best_practices": [
            "Cache dependencies between runs",
            "Use matrix builds for parallel testing",
            "Split large workflows into smaller jobs",
            "Use self-hosted runners for frequent builds",
        ],
        "confidence": 0.90,
    },
    "CI-REL-002": {
        "summary": "CI/CD pipeline lacks reliability features for production deployments.",
        "risk": "Without proper gates and rollback mechanisms, bad deployments can reach production and cause outages.",
        "impact": "Production outages, difficult rollbacks, poor deployment reliability.",
        "fix_code": '''# Add deployment approval gate
jobs:
  deploy-production:
    needs: [test, staging]
    environment:
      name: production
      url: https://myapp.com''',
        "fix_example": '''name: Deploy Pipeline
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: npm test
  
  deploy-staging:
    needs: test
    environment: staging
    steps:
    - run: ./deploy.sh staging
  
  deploy-production:
    needs: [test, deploy-staging]
    environment:
      name: production
      url: https://myapp.com
    steps:
    - run: ./deploy.sh production''',
        "best_practices": [
            "Use environment protection rules",
            "Require manual approval for production",
            "Implement automatic rollback on failure",
            "Use blue-green or canary deployments",
        ],
        "confidence": 0.90,
    },
    "TF-CICD-001": {
        "summary": "Terraform not integrated with CI/CD pipeline.",
        "risk": "Manual Terraform runs lead to inconsistent state, human errors, and lack of audit trail.",
        "impact": "Infrastructure drift, deployment failures, compliance issues.",
        "fix_code": '''# GitHub Actions for Terraform
name: Terraform CI
on:
  push:
    branches: [main]
jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: hashicorp/setup-terraform@v3
    - run: terraform init
    - run: terraform plan
    - run: terraform apply -auto-approve''',
        "fix_example": '''name: Terraform CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0
    
    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/terraform-ci
        aws-region: us-east-1
    
    - name: Terraform Init
      run: terraform init
    
    - name: Terraform Plan
      run: terraform plan -out=tfplan
    
    - name: Terraform Apply
      if: github.ref == 'refs/heads/main'
      run: terraform apply -auto-approve tfplan''',
        "best_practices": [
            "Store state in remote backend with locking",
            "Require PR review for terraform plan",
            "Use separate workflows for plan and apply",
            "Enable audit logging for all changes",
        ],
        "confidence": 0.95,
    },
    "TF-CICD-002": {
        "summary": "Terraform plan not reviewed before apply.",
        "risk": "Applying Terraform without review can cause unintended infrastructure changes or outages.",
        "impact": "Accidental resource deletion, configuration drift, production outages.",
        "fix_code": '''# Add manual approval step
jobs:
  apply:
    needs: plan
    environment: production
    steps:
    - run: terraform apply''',
        "fix_example": '''name: Terraform with Review
on:
  pull_request:
    branches: [main]
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: hashicorp/setup-terraform@v3
    - run: terraform plan -out=tfplan
    
    # Comment plan on PR
    - uses: actions/github-script@v7
      with:
        script: |
          const plan = fs.readFileSync('tfplan.txt', 'utf8')
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            body: `## Terraform Plan\\n\\n\\`\\`\\`\\n${plan}\\n\\`\\`\\``
          })
  
  apply:
    needs: plan
    if: github.event.pull_request.merged == true
    environment: production
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: terraform apply -auto-approve''',
        "best_practices": [
            "Always review terraform plan before apply",
            "Use GitHub PR comments to show plan output",
            "Require manual approval for production changes",
            "Enable terraform state locking",
        ],
        "confidence": 0.95,
    },
    "TF-CICD-003": {
        "summary": "Terraform state not properly managed in CI/CD.",
        "risk": "Concurrent Terraform runs can corrupt state, causing infrastructure drift or failed deployments.",
        "impact": "State corruption, duplicate resources, orphaned infrastructure.",
        "fix_code": '''# Use remote backend with locking
terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "fix_example": '''# backend.tf
terraform {
  backend "s3" {
    bucket         = "my-org-tf-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

# CI/CD workflow
name: Terraform
on: [push]
jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: hashicorp/setup-terraform@v3
    - run: terraform init
    - run: terraform plan
    - run: terraform apply -auto-approve''',
        "best_practices": [
            "Use DynamoDB for state locking",
            "Enable versioning on state bucket",
            "Use separate state files per environment",
            "Encrypt state at rest and in transit",
        ],
        "confidence": 0.95,
    },
    "TF-MOD-001": {
        "summary": "Terraform code not organized into reusable modules.",
        "risk": "Duplicate code across configurations leads to inconsistency and maintenance burden.",
        "impact": "Configuration drift, increased maintenance effort, inconsistent infrastructure.",
        "fix_code": '''# Use Terraform modules
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  
  name = "my-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
}''',
        "fix_example": '''# main.tf
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  
  name = "production-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = false
  
  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.0.0"
  
  cluster_name    = "production-eks"
  cluster_version = "1.28"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
}''',
        "best_practices": [
            "Use versioned modules from registry",
            "Pin module versions for reproducibility",
            "Create organization-specific module library",
            "Document module inputs and outputs",
        ],
        "confidence": 0.90,
    },
    "CI-SEC-001": {
        "risk": "CI/CD pipelines without security scanning allow vulnerable code and dependencies to reach production.",
        "impact": "Security vulnerabilities, supply chain attacks, and compliance violations in production.",
        "fix_example": '''# GitHub Actions with security scanning
name: CI/CD Pipeline
on: [push]
jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Dependency scanning
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    # Container scanning
    - name: Build and scan container
      uses: docker/build-push-action@v5
      with:
        push: false
        tags: app:${{ github.sha }}
    
    # SAST scanning
    - name: Run Semgrep
      uses: returntocorp/semgrep-action@v1
      with:
        config: >-
          p/security-audit
          p/secrets
          p/owasp-top-ten''',
    },
    "CI-SCALE-001": {
        "risk": "Without build caching, every CI/CD run downloads dependencies and builds from scratch, wasting time and resources.",
        "impact": "Slow build times (5-10x slower). Increased CI/CD costs. Wasted compute resources.",
        "fix_example": '''# GitHub Actions with caching
name: CI/CD Pipeline
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Cache dependencies
    - name: Cache node modules
      uses: actions/cache@v3
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-
    
    # Cache Docker layers
    - name: Cache Docker layers
      uses: actions/cache@v3
      with:
        path: /tmp/.buildx-cache
        key: ${{ runner.os }}-buildx-${{ github.sha }}
        restore-keys: |
          ${{ runner.os }}-buildx-
    
    # Use cached dependencies
    - name: Install dependencies
      run: npm ci
      # Uses cached node_modules''',
    },
    "CI-REL-002": {
        "risk": "Without automated testing, bugs and regressions reach production, causing service outages and user impact.",
        "impact": "Production bugs, service outages, customer dissatisfaction, and increased support costs.",
        "fix_example": '''# GitHub Actions with automated testing
name: CI/CD Pipeline
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Unit tests
    - name: Run unit tests
      run: npm run test:unit
    
    # Integration tests
    - name: Run integration tests
      run: npm run test:integration
    
    # E2E tests
    - name: Run E2E tests
      run: npm run test:e2e
    
    # Code coverage
    - name: Check code coverage
      run: npm run test:coverage
      # Fail if coverage below threshold
    
    # Security tests
    - name: Run security tests
      run: npm audit
      # Fail on high/critical vulnerabilities''',
    },
    # Docker Rules
    "DOCKER-001": {
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host system.",
        "impact": "Root container access increases attack surface and potential damage from container breakout exploits.",
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

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
FROM node@sha256:abc123def456...''',
    },
    "docker_no_healthcheck": {
        "risk": "Without HEALTHCHECK, container orchestration systems cannot detect if the application inside the container is healthy or unresponsive.",
        "impact": "Unhealthy containers may continue receiving traffic, causing service degradation and poor user experience.",
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

USER nodejs
EXPOSE 3000
CMD ["node", "server.js"]''',
    },
    "DKR-REL-001": {
        "summary": "Docker container lacks HEALTHCHECK instruction for health monitoring.",
        "risk": "Without HEALTHCHECK, container orchestration systems cannot detect if the application inside the container is healthy or unresponsive.",
        "impact": "Unhealthy containers may continue receiving traffic, causing service degradation and poor user experience.",
        "fix_code": '''HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1''',
        "fix_example": '''# Add HEALTHCHECK instruction to Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# For different applications:
# Node.js: HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1
# Python:  HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
# Go:      HEALTHCHECK CMD wget -q --spider http://localhost:8080/health || exit 1''',
        "full_example": '''FROM node:18.17.0-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Set appropriate interval and timeout for your application",
            "Use /health or /healthz endpoint for health checks",
            "Ensure health endpoint checks critical dependencies",
        ],
        "confidence": 0.95,
    },
    "DKR-SEC-001": {
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host system.",
        "impact": "Root container access increases attack surface and potential damage from container breakout exploits.",
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user and group
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set proper ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 3000
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
        aws-region: us-east-1''',
    },
}


class AIFixEnrichmentService:
    """AI-powered fix enrichment service with caching."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider
        
        # Determine if we should use mock based on provider and API keys
        provider = settings.LLM_PROVIDER.lower()
        if provider == "mock":
            self._use_mock = True
        elif provider == "gemini":
            self._use_mock = not settings.GEMINI_API_KEY
        elif provider == "openai":
            self._use_mock = not settings.OPENAI_API_KEY
        elif provider == "anthropic":
            self._use_mock = not settings.ANTHROPIC_API_KEY
        else:
            self._use_mock = True  # Default to mock for unknown providers
        
        self._cache: dict[str, dict[str, Any]] = {}  # In-memory cache

    def _get_cache_key(self, rule_id: str, file_content_hash: str) -> str:
        """Generate cache key from rule_id and file content hash."""
        return f"{rule_id}:{file_content_hash}"

    def _hash_content(self, content: str) -> str:
        """Hash file content for cache key."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def generate_fix(self, finding: dict[str, Any], file_content: str = "") -> dict[str, Any]:
        """
        Generate AI fix suggestion for a finding.

        Args:
            finding: Finding dict with rule_id, title, severity, file_type
            file_content: Optional actual file content for context

        Returns:
            dict with summary, risk, fix_code, full_example, impact, confidence
        """
        rule_id = finding.get("rule_id", "")
        logger.info("Generating fix", rule_id=rule_id, use_mock=self._use_mock, provider=settings.LLM_PROVIDER)
        
        # Check cache first
        cache_key = self._get_cache_key(
            rule_id,
            self._hash_content(file_content) if file_content else "no_content"
        )

        if cache_key in self._cache:
            logger.debug("Cache hit for fix", rule_id=rule_id)
            return self._cache[cache_key]

        # Use mock if AI not configured
        if self._use_mock:
            logger.info("Using mock fix generator", rule_id=rule_id)
            result = self._generate_mock_fix(finding)
        else:
            try:
                logger.info("Calling AI fix generator", rule_id=rule_id, provider=settings.LLM_PROVIDER)
                result = await self._generate_ai_fix(finding, file_content)
                logger.info("AI fix generated successfully", rule_id=rule_id, confidence=result.get("confidence"))
            except Exception as e:
                logger.warning("AI fix generation failed, using mock", rule_id=rule_id, error=str(e))
                result = self._generate_mock_fix(finding)

        # Cache result
        self._cache[cache_key] = result
        return result

    async def _generate_ai_fix(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate fix using LLM."""
        if not self.llm_provider:
            self.llm_provider = get_llm_provider()

        prompt = self._build_fix_prompt(finding, file_content)
        response = await self.llm_provider.generate(prompt)

        return self._parse_ai_response(response, finding)

    def _build_fix_prompt(self, finding: dict[str, Any], file_content: str) -> str:
        """Build prompt for AI fix generation."""
        rule_id = finding.get("rule_id", "UNKNOWN")
        title = finding.get("rule_name", "Unknown Issue")
        severity = finding.get("severity", "MEDIUM")
        file_type = finding.get("file_type", "unknown")
        description = finding.get("description", "")

        return f"""You are an expert DevOps engineer. Generate a production-ready fix for this issue.

ISSUE DETAILS:
- Rule ID: {rule_id}
- Title: {title}
- Severity: {severity}
- File Type: {file_type}
- Description: {description}

{'FILE CONTENT:' if file_content else ''}
{file_content if file_content else 'N/A'}

Generate a response in this EXACT JSON format:
{{
  "summary": "Simple 1-2 sentence explanation of the issue",
  "risk": "Why this is dangerous (security, reliability, or performance impact)",
  "fix_code": "Production-ready fix code (use proper escaping for newlines)",
  "full_example": "Complete corrected file snippet showing the fix in context",
  "impact": "Security/reliability improvement from applying this fix",
  "confidence": 0.85
}}

REQUIREMENTS:
1. Fix code must be production-ready (not pseudocode)
2. Include proper error handling where applicable
3. Follow security best practices
4. Use specific versions (not 'latest')
5. Include comments explaining key changes

For Docker root user issues, MUST include:
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

USER appuser

For Docker HEALTHCHECK issues, MUST include:
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${{PORT:-3000}}/health || exit 1

Respond ONLY with the JSON, no other text."""

    def _parse_ai_response(self, response: str, finding: dict[str, Any]) -> dict[str, Any]:
        """Parse AI response into structured format."""
        import json
        import re

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)

            return {
                "summary": result.get("summary", finding.get("description", "")),
                "risk": result.get("risk", ""),
                "fix_code": result.get("fix_code", ""),
                "full_example": result.get("full_example", ""),
                "impact": result.get("impact", ""),
                "confidence": float(result.get("confidence", 0.8)),
            }
        except Exception as e:
            logger.warning("Failed to parse AI response", error=str(e))
            return self._generate_mock_fix(finding)

    def _generate_mock_fix(self, finding: dict[str, Any]) -> dict[str, Any]:
        """Generate mock fix (fallback when AI unavailable)."""
        rule_id = finding.get("rule_id", "")

        # Check static FIX_EXAMPLES first
        if rule_id in FIX_EXAMPLES:
            return {
                "summary": finding.get("description", ""),
                **FIX_EXAMPLES[rule_id],
                "confidence": 0.95,
            }

        # Default mock fix
        return {
            "summary": finding.get("description", "Issue detected in configuration."),
            "risk": "This issue may impact security, reliability, or performance.",
            "fix_code": "# Apply recommended fix based on best practices\n# See documentation for specific guidance",
            "full_example": "# Example configuration with fix applied\n# Replace with your specific configuration",
            "impact": "Improves security posture and follows industry best practices.",
            "confidence": 0.75,
        }


class FindingsEnricher:
    """Enrich findings with risk, impact, and fix examples.

    Now supports:
    - Static FIX_EXAMPLES (fallback for all)
    - AI-powered enrichment (for HIGH/CRITICAL severity)
    - Caching for performance
    """

    def __init__(self):
        self._fix_examples = FIX_EXAMPLES
        self._ai_service: Optional[AIFixEnrichmentService] = None

    def _get_ai_service(self) -> AIFixEnrichmentService:
        """Get or create AI enrichment service."""
        if self._ai_service is None:
            self._ai_service = AIFixEnrichmentService()
        return self._ai_service

    async def enrich_finding_async(self, finding: RuleFinding, file_content: str = "") -> RuleFinding:
        """
        Enrich a finding with AI-powered or static enrichment.

        Logic:
        - If severity is HIGH or CRITICAL → use AI
        - Otherwise → use static FIX_EXAMPLES
        - If AI fails → fallback to static

        Args:
            finding: The finding to enrich
            file_content: Optional file content for AI context

        Returns:
            Finding with enrichment fields populated
        """
        severity = str(finding.severity).lower() if hasattr(finding.severity, 'value') else str(finding.severity).lower()

        # Use AI for HIGH/CRITICAL severity
        if severity in ["high", "critical"]:
            try:
                ai_service = self._get_ai_service()
                ai_fix = await ai_service.generate_fix({
                    "rule_id": finding.rule_id,
                    "rule_name": finding.rule_name,
                    "severity": severity,
                    "file_type": finding.file_path.split('.')[-1] if '.' in finding.file_path else "unknown",
                    "description": finding.description,
                }, file_content)

                # Apply AI enrichment
                if not finding.risk:
                    finding.risk = ai_fix.get("risk", "")
                if not finding.fix_example:
                    # Try both "fix_code" (AI) and "fix_example" (static) keys
                    finding.fix_example = ai_fix.get("fix_code") or ai_fix.get("fix_example") or ai_fix.get("full_example") or ""
                if not finding.impact_analysis:
                    finding.impact_analysis = ai_fix.get("impact", "")
                if not finding.impact:
                    finding.impact = ai_fix.get("impact", "")
                if ai_fix.get("full_example"):
                    # Store full example in fix_example if available
                    finding.fix_example = ai_fix.get("full_example", finding.fix_example)
                finding.confidence = ai_fix.get("confidence", 0.8)
                finding.ai_generated = True  # Mark as AI-generated

                logger.info(
                    "AI enrichment applied",
                    rule_id=finding.rule_id,
                    severity=severity,
                    confidence=finding.confidence,
                    ai_generated=finding.ai_generated,
                )

                return finding

            except Exception as e:
                logger.warning(
                    "AI enrichment failed, falling back to static",
                    rule_id=finding.rule_id,
                    error=str(e),
                )
                # Fall through to static enrichment

        # Static enrichment (fallback or for LOW/MEDIUM severity)
        return self.enrich_finding(finding)

    def enrich_finding(self, finding: RuleFinding) -> RuleFinding:
        """
        Enrich a single finding with static risk, impact, fix example, and documentation URL.

        Args:
            finding: The finding to enrich

        Returns:
            Finding with enrichment fields populated
        """
        # Look up fix example by rule_id
        fix_data = self._fix_examples.get(finding.rule_id, {})

        # Apply enrichment (only if not already set)
        if not finding.summary and "summary" in fix_data:
            finding.summary = fix_data["summary"]
            logger.debug(f"Enriched {finding.rule_id} with summary")
        if not finding.risk and "risk" in fix_data:
            finding.risk = fix_data["risk"]
            logger.debug(f"Enriched {finding.rule_id} with risk")
        if not finding.impact and "impact" in fix_data:
            finding.impact = fix_data["impact"]
            logger.debug(f"Enriched {finding.rule_id} with impact")
        if not finding.impact_analysis and "impact" in fix_data:
            finding.impact_analysis = fix_data["impact"]
            logger.debug(f"Enriched {finding.rule_id} with impact_analysis")
        if not finding.fix_code and "fix_code" in fix_data:
            finding.fix_code = fix_data["fix_code"]
            logger.debug(f"Enriched {finding.rule_id} with fix_code")
        if not finding.fix_example and "fix_example" in fix_data:
            finding.fix_example = fix_data["fix_example"]
            logger.debug(f"Enriched {finding.rule_id} with fix_example")
        if not finding.full_example and "full_example" in fix_data:
            finding.full_example = fix_data["full_example"]
            logger.debug(f"Enriched {finding.rule_id} with full_example")
        if not finding.best_practices and "best_practices" in fix_data:
            finding.best_practices = fix_data["best_practices"]
            logger.debug(f"Enriched {finding.rule_id} with best_practices")
        if not finding.confidence and "confidence" in fix_data:
            finding.confidence = fix_data["confidence"]
            logger.debug(f"Enriched {finding.rule_id} with confidence")

        # Add documentation URL
        if not finding.documentation_url:
            finding.documentation_url = get_documentation_url(finding.rule_id)
            if finding.documentation_url:
                logger.debug(f"Enriched {finding.rule_id} with documentation_url")

        # Mark as static (not AI-generated)
        if not hasattr(finding, 'ai_generated'):
            finding.ai_generated = False

        return finding

    async def enrich_findings_async(
        self,
        findings: list[RuleFinding],
        file_contents: dict[str, str] = None,
    ) -> list[RuleFinding]:
        """
        Enrich multiple findings with AI-powered or static enrichment.

        Args:
            findings: List of findings to enrich
            file_contents: Optional dict mapping file_path to content

        Returns:
            List of enriched findings
        """
        enriched = []
        for finding in findings:
            file_content = file_contents.get(finding.file_path, "") if file_contents else ""
            enriched_finding = await self.enrich_finding_async(finding, file_content)
            enriched.append(enriched_finding)

        logger.info(
            "Findings enriched",
            total_count=len(findings),
            ai_enriched_count=sum(1 for f in enriched if f.confidence and f.confidence > 0.8),
        )

        return enriched

    def enrich_findings(self, findings: list[RuleFinding]) -> list[RuleFinding]:
        """
        Enrich multiple findings with static risk, impact, and fix examples.

        Args:
            findings: List of findings to enrich

        Returns:
            List of enriched findings
        """
        enriched = []
        for finding in findings:
            enriched.append(self.enrich_finding(finding))

        logger.info(
            "Findings enriched (static)",
            total_count=len(findings),
            enriched_count=sum(1 for f in enriched if f.risk or f.impact or f.fix_example),
        )

        return enriched


def enrich_findings(findings: list[RuleFinding]) -> list[RuleFinding]:
    """Convenience function to enrich findings (static)."""
    enricher = FindingsEnricher()
    return enricher.enrich_findings(findings)


async def enrich_findings_with_ai(
    findings: list[RuleFinding],
    file_contents: dict[str, str] = None,
) -> list[RuleFinding]:
    """Convenience function to enrich findings with AI."""
    enricher = FindingsEnricher()
    return await enricher.enrich_findings_async(findings, file_contents)
