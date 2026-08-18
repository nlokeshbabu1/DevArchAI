"""Findings enrichment service - adds risk, impact, fix examples, and documentation links.

Now supports:
- Static FIX_EXAMPLES (fallback)
- AI-powered dynamic enrichment (for HIGH/CRITICAL)
- Documentation URL mapping
"""

import difflib
import hashlib
import json
from typing import Any

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
        "full_example": '''# backend.tf - Remote state configuration
terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true

    # Enable state locking
    # DynamoDB table must have a primary key named 'LockID'
  }
}

# Create S3 bucket for state (in a separate apply)
resource "aws_s3_bucket" "terraform_state" {
  bucket = "tf-state-prod"

  lifecycle {
    prevent_destroy = true
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Create DynamoDB table for locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform Lock Table"
    Environment = "production"
  }
}''',
        "best_practices": [
            "Use separate state files for different environments",
            "Enable versioning on the S3 bucket",
            "Restrict IAM access to state bucket",
            "Use DynamoDB for state locking to prevent concurrent modifications",
            "Encrypt state files at rest and in transit",
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
        "full_example": '''# backend.tf - Remote state configuration
terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

# S3 bucket for state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "my-terraform-state-bucket"
}

# Versioning for state history
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# DynamoDB for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}''',
        "best_practices": [
            "Use DynamoDB for state locking",
            "Enable encryption for state files",
            "Use separate state files per environment (dev, staging, prod)",
            "Enable S3 versioning for state history and recovery",
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
        "full_example": '''# backend.tf - Remote state with locking
terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "Terraform State Lock"
    Environment = "production"
  }
}

# Note: The DynamoDB table must have a primary key named 'LockID' (type String)
# Terraform uses this to acquire locks before state operations''',
        "best_practices": [
            "Use DynamoDB table with pay-per-request billing",
            "Enable state file versioning",
            "Enable point-in-time recovery for DynamoDB",
            "Use IAM policies to restrict lock table access",
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
        "full_example": '''# backend.tf - Encrypted remote state
terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

# S3 bucket with encryption
resource "aws_s3_bucket" "terraform_state" {
  bucket = "tf-state-prod"
}

# Server-side encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.terraform_state.arn
    }
  }
}

# KMS key for state encryption
resource "aws_kms_key" "terraform_state" {
  description             = "KMS key for Terraform state encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name        = "Terraform State KMS Key"
    Environment = "production"
  }
}

# Versioning for state history
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}''',
        "best_practices": [
            "Enable server-side encryption with KMS",
            "Use bucket policies to enforce encryption",
            "Enable key rotation for KMS keys",
            "Restrict KMS key access to authorized principals only",
        ],
        "confidence": 0.95,
    },
    # Terraform Provider Rules
    "TF-PROV-001": {
        "summary": "Terraform provider version is not pinned, allowing potentially breaking changes.",
        "risk": "Unpinned provider versions can introduce breaking changes during terraform init, causing unexpected behavior or deployment failures.",
        "impact": "Provider updates may change resource behavior, causing infrastructure drift or failed deployments in production.",
        "fix_code": '''terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}''',
        "fix_example": '''terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # Allows 5.x.x but not 6.0.0
    }
  }
}''',
        "full_example": '''terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}''',
        "best_practices": [
            "Pin provider versions using ~> constraint (e.g., ~> 5.0 allows 5.x.x but not 6.0.0)",
            "Use terraform required_version to enforce minimum Terraform version",
            "Run terraform init -upgrade periodically to test newer versions in staging",
            "Review provider changelogs before upgrading major versions",
        ],
        "confidence": 0.95,
    },
    # Terraform Secrets
    "TF-SEC-001": {
        "summary": "Hardcoded secrets in Terraform files can be exposed in version control and state files.",
        "risk": "Hardcoded secrets in Terraform files are stored in version control and state files, exposing credentials to anyone with repository or state access.",
        "impact": "Credential exposure can lead to unauthorized access, data breaches, and significant compliance violations (SOC2, HIPAA, PCI-DSS).",
        "fix_code": '''variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

resource "aws_db_instance" "db" {
  password = var.db_password
}''',
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
        "full_example": '''# variables.tf
variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 16
    error_message = "Password must be at least 16 characters."
  }
}

# main.tf
# Use AWS Secrets Manager for production secrets
data "aws_secretsmanager_secret_version" "db_creds" {
  secret_id = "prod/db/credentials"
}

resource "aws_db_instance" "db" {
  identifier = "production-db"
  
  # Reference from Secrets Manager
  username = jsondecode(data "aws_secretsmanager_secret_version" "db_creds".secret_string)["username"]
  password = jsondecode(data "aws_secretsmanager_secret_version" "db_creds".secret_string)["password"]
  
  # Mark as sensitive in outputs
}

# outputs.tf
output "db_endpoint" {
  value = aws_db_instance.db.endpoint
}

# Note: Never output passwords even with sensitive = true in production''',
        "best_practices": [
            "Use AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault for secret storage",
            "Mark sensitive variables with sensitive = true",
            "Never commit .tfvars files with secrets to version control",
            "Use terraform-docs to document required variables",
            "Rotate secrets regularly and use short-lived credentials when possible",
        ],
        "confidence": 0.95,
    },
    # Terraform Encryption Rules
    "TF-ENC-001": {
        "summary": "S3 bucket is not configured with server-side encryption.",
        "risk": "Unencrypted S3 buckets expose stored data to unauthorized access if bucket policies are misconfigured or if AWS account is compromised.",
        "impact": "Data breaches, compliance violations (GDPR, HIPAA, PCI-DSS), and potential regulatory fines.",
        "fix_code": '''resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}''',
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
        "full_example": '''resource "aws_s3_bucket" "data" {
  bucket = "my-secure-bucket"

  tags = {
    Name        = "Secure Data Bucket"
    Environment = "production"
  }
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
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}''',
        "best_practices": [
            "Enable default encryption with AWS KMS for key management",
            "Enable versioning to protect against accidental deletion",
            "Block all public access unless explicitly required",
            "Use bucket policies to enforce encryption requirements",
            "Enable CloudTrail logging for S3 data events",
        ],
        "confidence": 0.95,
    },
    "TF-ENC-002": {
        "summary": "EBS volume is not encrypted at rest.",
        "risk": "Unencrypted EBS volumes expose data at rest, allowing anyone with disk access to read sensitive information.",
        "impact": "Data breaches if instances are compromised, compliance violations, and potential data leakage from terminated instances.",
        "fix_code": '''resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-west-2a"
  size              = 40
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
}''',
        "fix_example": '''resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-west-2a"
  size              = 40
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
}''',
        "full_example": '''resource "aws_kms_key" "ebs" {
  description             = "KMS key for EBS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-west-2a"
  size              = 40
  type              = "gp3"
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn

  tags = {
    Name        = "Encrypted Data Volume"
    Environment = "production"
  }
}

# Attach to EC2 instance
resource "aws_volume_attachment" "ebs_att" {
  device_name = "/dev/sdh"
  volume_id   = aws_ebs_volume.encrypted.id
  instance_id = aws_instance.web.id
}''',
        "best_practices": [
            "Enable encryption for all EBS volumes, especially for production",
            "Use AWS KMS keys for encryption key management",
            "Enable key rotation for KMS keys",
            "Encrypt snapshots derived from encrypted volumes",
            "Use IAM policies to restrict KMS key access",
        ],
        "confidence": 0.95,
    },
    "TF-ENC-003": {
        "summary": "RDS database instance is not configured with storage encryption.",
        "risk": "Unencrypted databases expose sensitive data at rest, including PII, financial data, and application secrets.",
        "impact": "Data breaches, compliance violations (HIPAA, PCI-DSS, SOC2), regulatory fines, and reputational damage.",
        "fix_code": '''resource "aws_db_instance" "secure" {
  identifier        = "secure-db"
  engine            = "postgres"
  storage_encrypted = true
  kms_key_id        = aws_kms_key.db.arn
}''',
        "fix_example": '''resource "aws_db_instance" "secure" {
  identifier           = "secure-db"
  engine               = "postgres"
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.db.arn
  publicly_accessible  = false
}''',
        "full_example": '''resource "aws_kms_key" "db" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_db_instance" "secure" {
  identifier     = "production-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp2"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.db.arn

  db_name  = "appdb"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.private.name

  publicly_accessible = false

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  auto_minor_version_upgrade = true
  deletion_protection        = true

  tags = {
    Name        = "Production PostgreSQL"
    Environment = "production"
  }
}''',
        "best_practices": [
            "Enable storage encryption for all RDS instances",
            "Use AWS KMS with automatic key rotation",
            "Disable public accessibility for production databases",
            "Enable automated backups with appropriate retention",
            "Use security groups to restrict database access",
        ],
        "confidence": 0.95,
    },
    # Terraform Networking Rules
    "TF-NET-001": {
        "summary": "Security group allows unrestricted inbound access from 0.0.0.0/0.",
        "risk": "Security groups allowing 0.0.0.0/0 expose services directly to the internet, making them vulnerable to brute force attacks, exploits, and unauthorized access.",
        "impact": "Critical services (SSH, RDP, databases) exposed to the internet can be compromised, leading to data breaches, ransomware, or cryptomining.",
        "fix_code": '''resource "aws_security_group" "restricted" {
  name   = "restricted-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "SSH from trusted IPs only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}''',
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
        "full_example": '''resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main.id

  # Allow HTTP from anywhere
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow HTTPS from anywhere
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Restrict SSH to VPC only
  ingress {
    description = "SSH from VPC only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "Web Security Group"
    Environment = "production"
  }
}''',
        "best_practices": [
            "Never allow 0.0.0.0/0 on sensitive ports (22, 3389, database ports)",
            "Use security group references instead of CIDR blocks when possible",
            "Document the purpose of each ingress rule with descriptions",
            "Regularly audit security groups for overly permissive rules",
            "Use VPC endpoints for AWS service access instead of public internet",
        ],
        "confidence": 0.95,
    },
    "TF-NET-002": {
        "summary": "RDS database instance is publicly accessible.",
        "risk": "Publicly accessible databases can be discovered and attacked from the internet, exposing sensitive data to unauthorized access.",
        "impact": "Data breaches, SQL injection attacks, credential stuffing, and complete database compromise.",
        "fix_code": '''resource "aws_db_instance" "private" {
  publicly_accessible  = false
  db_subnet_group_name = aws_db_subnet_group.private.name
}''',
        "fix_example": '''resource "aws_db_instance" "private" {
  publicly_accessible  = false  # Must be false
  db_subnet_group_name = aws_db_subnet_group.private.name
}''',
        "full_example": '''resource "aws_db_subnet_group" "private" {
  name       = "private-db-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name        = "Private DB Subnet Group"
    Environment = "production"
  }
}

resource "aws_security_group" "db" {
  name        = "db-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL from application security group only
  ingress {
    description     = "PostgreSQL from app servers"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "private" {
  identifier     = "production-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"

  allocated_storage  = 100
  storage_encrypted  = true
  kms_key_id         = aws_kms_key.db.arn

  db_name  = "appdb"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.private.name

  # CRITICAL: Never expose database to public internet
  publicly_accessible = false

  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "final-postgres-snapshot"

  tags = {
    Name        = "Production PostgreSQL"
    Environment = "production"
  }
}''',
        "best_practices": [
            "Set publicly_accessible = false for all production databases",
            "Place databases in private subnets only",
            "Use security groups to restrict access to application tier only",
            "Use VPC peering or PrivateLink for cross-VPC database access",
            "Enable database activity streams for audit logging",
        ],
        "confidence": 0.95,
    },
    # Terraform IAM Rules
    "TF-IAM-001": {
        "summary": "IAM policy uses wildcard (*) permissions violating least privilege principle.",
        "risk": "Wildcard IAM permissions (*) violate the principle of least privilege, granting excessive access that can be exploited if credentials are compromised.",
        "impact": "Compromised credentials with wildcard permissions can lead to complete account takeover, data exfiltration, or resource destruction.",
        "fix_code": '''resource "aws_iam_policy" "specific" {
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
        "full_example": '''# ❌ BAD: Overly permissive policy
# resource "aws_iam_policy" "bad" {
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Effect   = "Allow"
#       Action   = "*"
#       Resource = "*"
#     }]
#   })
# }

# ✅ GOOD: Least privilege policy
resource "aws_iam_policy" "app_s3_access" {
  name        = "app-s3-access-policy"
  description = "Grants specific S3 access for application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListObjectsInBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.app.arn
      },
      {
        Sid    = "ReadWriteObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.app.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role" "app" {
  name = "app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "app_attach" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_s3_access.arn
}''',
        "best_practices": [
            "Follow the principle of least privilege - grant only required permissions",
            "Use specific resource ARNs instead of wildcards",
            "Use IAM Access Analyzer to identify unused permissions",
            "Regularly audit and review IAM policies",
            "Use conditions to further restrict access (e.g., by IP, time)",
        ],
        "confidence": 0.95,
    },
    # Terraform Tags
    "TF-TAG-001": {
        "summary": "Terraform resources are missing required tags for cost allocation and management.",
        "risk": "Missing tags make it difficult to track resource ownership, allocate costs, enforce policies, and manage resources at scale.",
        "impact": "Inability to identify resource owners during incidents, inaccurate cost allocation, and compliance audit failures.",
        "fix_code": '''locals {
  default_tags = {
    Environment = var.environment
    Owner       = var.owner
    Project     = var.project
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "data" {
  tags = local.default_tags
}''',
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
        "full_example": '''# variables.tf
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "owner" {
  description = "Resource owner"
  type        = string
  default     = "platform-team"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "myapp"
}

# locals.tf
locals {
  default_tags = {
    Environment = var.environment
    Owner       = var.owner
    Project     = var.project
    ManagedBy   = "terraform"
    CostCenter  = "engineering"
  }
}

# main.tf - Apply tags to all resources
resource "aws_s3_bucket" "data" {
  bucket = "my-app-data-bucket"

  tags = local.default_tags
}

resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = "t3.medium"

  tags = merge(local.default_tags, {
    Name = "web-server"
    Role = "web"
  })
}

# Use provider-level default tags (Terraform AWS Provider v4+)
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.default_tags
  }
}''',
        "best_practices": [
            "Define a standard tagging strategy (Environment, Owner, Project, CostCenter)",
            "Use terraform-local or locals to define default tags",
            "Use provider-level default_tags for automatic tagging (AWS Provider v4+)",
            "Enforce tagging policies using AWS Config or Service Control Policies",
            "Include CostCenter tag for accurate billing allocation",
        ],
        "confidence": 0.95,
    },
    # Kubernetes Rules
    "K8S-001": {
        "summary": "Kubernetes container lacks resource requests and limits configuration.",
        "risk": "Containers without resource limits can consume all node resources, causing node instability and affecting other workloads.",
        "impact": "Resource exhaustion leads to node crashes, pod evictions, and service outages affecting all applications on the node.",
        "fix_code": '''resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"''',
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
        "full_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  labels:
    app: myapp
spec:
  replicas: 3
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
        image: myapp:1.0.0
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5''',
        "best_practices": [
            "Set resource requests based on typical usage",
            "Set limits to prevent resource starvation",
            "Use Vertical Pod Autoscaler to right-size resources",
            "Monitor actual usage with Prometheus and adjust accordingly",
            "Set LimitRange defaults at namespace level",
        ],
        "confidence": 0.95,
    },
    "K8S-002": {
        "summary": "Kubernetes container is running as root user which is a security risk.",
        "risk": "Containers running as root have full access to the host system if they escape the container, increasing the blast radius of exploits.",
        "impact": "Container breakout vulnerabilities can lead to full host compromise, lateral movement, and cluster-wide attacks.",
        "fix_code": '''securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL''',
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
        "full_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-deployment
  labels:
    app: secure-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secure-app
  template:
    metadata:
      labels:
        app: secure-app
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 3000
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
              - ALL''',
        "best_practices": [
            "Always run containers as non-root users",
            "Drop all capabilities and add only what's needed",
            "Use read-only root filesystem where possible",
            "Enable seccomp and AppArmor profiles",
            "Prevent privilege escalation with allowPrivilegeEscalation: false",
        ],
        "confidence": 0.95,
    },
    "K8S-REL-001": {
        "summary": "Deployment has only a single replica which creates a single point of failure.",
        "risk": "Single replica deployments have no redundancy and will cause complete service outage during pod failures or node maintenance.",
        "impact": "Service downtime during pod failures, updates, or node maintenance. No high availability.",
        "fix_code": '''spec:
  replicas: 3  # Run multiple replicas for HA''',
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
        "full_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  labels:
    app: myapp
spec:
  replicas: 3  # Multiple replicas for high availability
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: myapp
              topologyKey: kubernetes.io/hostname
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"''',
        "best_practices": [
            "Run at least 2-3 replicas for production workloads",
            "Use pod anti-affinity to spread replicas across nodes",
            "Configure rolling update strategy with maxUnavailable: 0",
            "Use PodDisruptionBudget to protect during voluntary disruptions",
            "Consider using multiple availability zones for critical workloads",
        ],
        "confidence": 0.95,
    },
    "K8S-REL-002": {
        "summary": "No PodDisruptionBudget configured for voluntary disruptions.",
        "risk": "Without PodDisruptionBudget, voluntary disruptions (node drains, cluster upgrades) can take down all pods simultaneously, causing service outages.",
        "impact": "Service downtime during cluster maintenance, node upgrades, or scaling operations.",
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
spec:
  minAvailable: 1  # Keep at least 1 pod running
  selector:
    matchLabels:
      app: myapp

# Or use maxUnavailable:
# spec:
#   maxUnavailable: 1  # Allow only 1 pod to be unavailable''',
        "full_example": '''apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: production
  labels:
    app: myapp
spec:
  minAvailable: 1  # Ensure at least 1 pod is always available
  selector:
    matchLabels:
      app: myapp
      tier: backend

# Alternative: Use maxUnavailable for stateless workloads
# ---
# apiVersion: policy/v1
# kind: PodDisruptionBudget
# metadata:
#   name: app-pdb-max-unavailable
# spec:
#   maxUnavailable: 1  # Allow only 1 pod to be unavailable at a time
#   selector:
#     matchLabels:
#       app: myapp''',
        "best_practices": [
            "Set minAvailable based on application requirements",
            "Use maxUnavailable for stateless applications",
            "Consider PDB for all critical workloads",
            "Test PDB behavior during node drains",
            "Monitor PDB status with kubectl get pdb",
        ],
        "confidence": 0.95,
    },
    "K8S-REL-003": {
        "summary": "Container lacks liveness probe for health monitoring and automatic recovery.",
        "risk": "Without liveness probes, Kubernetes cannot detect if a container is deadlocked or stuck, leading to traffic being sent to non-functional pods.",
        "impact": "Service degradation as traffic routes to unresponsive containers. No automatic recovery.",
        "fix_code": '''livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 3
  periodSeconds: 3''',
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
        "full_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  replicas: 3
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
        image: myapp:1.0.0
        ports:
        - containerPort: 8080
        
        # Liveness probe - detects deadlocks
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        # Readiness probe - detects startup completion
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        
        # Startup probe - for slow-starting containers
        startupProbe:
          httpGet:
            path: /healthz
            port: 8080
          failureThreshold: 30
          periodSeconds: 10''',
        "best_practices": [
            "Use liveness probes to detect and recover from deadlocks",
            "Use readiness probes to prevent traffic to unready pods",
            "Use startup probes for slow-starting applications",
            "Set appropriate timeouts and failure thresholds",
            "Ensure health endpoints are lightweight and fast",
        ],
        "confidence": 0.95,
    },
    "K8S-SEC-001": {
        "summary": "No Kubernetes NetworkPolicies found, allowing unrestricted pod-to-pod communication.",
        "risk": "Without NetworkPolicies, all pods can communicate freely with each other. If an attacker compromises one pod, they can potentially access all other pods in the cluster.",
        "impact": "Lateral movement attacks, data exfiltration, unauthorized access to sensitive services, compliance violations.",
        "fix_code": '''apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-ingress
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000''',
        "fix_example": '''# Default deny all ingress traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress

# Allow specific traffic to frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
      tier: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 3000

# Allow backend to communicate with database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
      tier: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
          tier: data
    ports:
    - protocol: TCP
      port: 5432''',
        "full_example": '''# Namespace with NetworkPolicy support
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    name: production

# Default deny all ingress traffic in namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress

# Default deny all egress traffic in namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress

# Allow ingress from ingress controller to frontend pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
      tier: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    - podSelector:
        matchLabels:
          app: backend
          tier: api
    ports:
    - protocol: TCP
      port: 3000

# Allow frontend to communicate with backend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
      tier: web
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
          tier: api
    ports:
    - protocol: TCP
      port: 8080

# Allow backend to communicate with database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
      tier: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
          tier: data
    ports:
    - protocol: TCP
      port: 5432

# Allow DNS resolution for all pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53''',
        "best_practices": [
            "Implement default-deny NetworkPolicies for zero-trust networking",
            "Use namespace-level isolation for multi-tenant clusters",
            "Allow only required ingress/egress traffic with specific selectors",
            "Use label selectors to define trust boundaries between services",
            "Test NetworkPolicies in staging before production deployment",
            "Monitor and audit network traffic for policy violations",
        ],
        "confidence": 0.95,
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
        "full_example": '''apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  labels:
    app: myapp
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
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max''',
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
        "full_example": '''apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: production
  labels:
    app: myapp
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: myapp
      tier: backend

# For stateless applications, use maxUnavailable instead:
# ---
# apiVersion: policy/v1
# kind: PodDisruptionBudget
# metadata:
#   name: app-pdb-frontend
#   namespace: production
# spec:
#   maxUnavailable: 1
#   selector:
#     matchLabels:
#       app: myapp
#       tier: frontend''',
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
        "full_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  labels:
    app: myapp
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 8080
          name: metrics
        - containerPort: 3000
          name: http
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        # Liveness probe using health endpoint
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        # Readiness probe
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        # Environment for tracing
        env:
        - name: OTEL_SERVICE_NAME
          value: "myapp"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://otel-collector:4317"''',
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
        "full_example": '''name: Secure Deploy Pipeline
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
    - uses: actions/checkout@v4

    # Use OIDC for AWS authentication (preferred method)
    - name: Configure AWS credentials via OIDC
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
        role-session-name: github-actions-session
        aws-region: us-east-1

    # Use GitHub Secrets for application config
    - name: Deploy application
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        API_KEY: ${{ secrets.API_KEY }}
        REDIS_URL: ${{ secrets.REDIS_URL }}
      run: |
        echo "Deploying with secure credentials..."
        ./deploy.sh

    # Verify deployment
    - name: Health check
      run: |
        curl -f https://myapp.com/health || exit 1

# Note: Configure secrets in GitHub Settings > Secrets and variables > Actions
# Never hardcode secrets in workflow files!''',
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
        "full_example": '''name: Optimized CI Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [16, 18, 20]

    steps:
    - uses: actions/checkout@v4

    # Setup Node.js with caching
    - name: Setup Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'

    # Cache dependencies
    - name: Cache node modules
      uses: actions/cache@v4
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ matrix.node-version }}-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-${{ matrix.node-version }}-

    # Install dependencies (uses cache)
    - name: Install dependencies
      run: npm ci

    # Build
    - name: Build
      run: npm run build

    # Test
    - name: Run tests
      run: npm test

    # Cache build output
    - name: Cache dist
      uses: actions/cache@v4
      with:
        path: dist/
        key: ${{ runner.os }}-build-${{ matrix.node-version }}-${{ github.sha }}''',
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
        "full_example": '''name: Production Deploy Pipeline
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: npm test

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.myapp.com
    steps:
    - uses: actions/checkout@v4
    - name: Deploy to staging
      run: ./deploy.sh staging

  integration-tests:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
    - name: Run integration tests
      run: npm run test:integration
      env:
        BASE_URL: https://staging.myapp.com

  deploy-production:
    needs: [test, deploy-staging, integration-tests]
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    steps:
    - uses: actions/checkout@v4

    - name: Deploy to production
      run: ./deploy.sh production

    - name: Health check
      run: curl -f https://myapp.com/health || exit 1

    - name: Rollback on failure
      if: failure()
      run: ./rollback.sh production''',
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
        "full_example": '''name: Terraform CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        shell: bash
        working-directory: ./terraform

    steps:
    - uses: actions/checkout@v4

    - uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0
        terraform_wrapper: false

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/terraform-ci
        aws-region: us-east-1

    - name: Terraform Init
      run: terraform init

    - name: Terraform Format Check
      run: terraform fmt -check

    - name: Terraform Validate
      run: terraform validate

    - name: Terraform Plan
      run: terraform plan -out=tfplan -no-color

    - name: Save Plan Artifact
      if: github.event_name == 'pull_request'
      run: terraform show -json tfplan > tfplan.json

    - name: Upload Plan
      if: github.event_name == 'pull_request'
      uses: actions/upload-artifact@v3
      with:
        name: tfplan
        path: terraform/tfplan.json

    - name: Terraform Apply
      if: github.ref == 'refs/heads/main' && github.event_name == 'push'
      run: terraform apply -auto-approve tfplan''',
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
        "full_example": '''name: Terraform with Plan Review
on:
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./terraform

    steps:
    - uses: actions/checkout@v4

    - uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/terraform-ci
        aws-region: us-east-1

    - name: Terraform Init
      run: terraform init

    - name: Terraform Plan
      run: terraform plan -out=tfplan -no-color

    - name: Save Plan Output
      run: terraform show -no-color tfplan > tfplan.txt

    - name: Comment Plan on PR
      uses: actions/github-script@v7
      with:
        github-token: ${{ secrets.GITHUB_TOKEN }}
        script: |
          const fs = require('fs');
          const plan = fs.readFileSync('terraform/tfplan.txt', 'utf8');
          const truncatedPlan = plan.length > 65000 ? plan.substring(0, 65000) + '... (truncated)' : plan;
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## Terraform Plan\\n\\n\\`\\`\\`\\n${truncatedPlan}\\n\\`\\`\\``
          });

  apply:
    needs: plan
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    environment: production
    defaults:
      run:
        working-directory: ./terraform

    steps:
    - uses: actions/checkout@v4

    - uses: hashicorp/setup-terraform@v3

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/terraform-ci
        aws-region: us-east-1

    - name: Terraform Init
      run: terraform init

    - name: Terraform Apply
      run: terraform apply -auto-approve''',
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
        "full_example": '''# backend.tf
terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = "my-org-tf-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

# CI/CD workflow
name: Terraform with State Management
on:
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./terraform

    steps:
    - uses: actions/checkout@v4

    - uses: hashicorp/setup-terraform@v3

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/terraform-ci
        aws-region: us-east-1

    - name: Terraform Init
      run: terraform init

    - name: Terraform Plan
      run: terraform plan -out=tfplan

    - name: Terraform Apply
      run: terraform apply -auto-approve tfplan

# Note: State is stored in S3 with locking via DynamoDB
# This prevents concurrent modifications and state corruption''',
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
        "full_example": '''# main.tf - Using Terraform modules
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

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      min_size     = 2
      max_size     = 5
      desired_size = 3
    }
  }
}

# outputs.tf
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}''',
        "confidence": 0.90,
    },
    "CI-SEC-001": {
        "summary": "CI/CD pipeline lacks security scanning for vulnerabilities and secrets.",
        "risk": "CI/CD pipelines without security scanning allow vulnerable code and dependencies to reach production.",
        "impact": "Security vulnerabilities, supply chain attacks, and compliance violations in production.",
        "fix_code": '''# Add security scanning steps
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Run Semgrep SAST
  uses: returntocorp/semgrep-action@v1
  with:
    config: p/security-audit''',
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
        "full_example": '''name: Security Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security-scanning:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    # SAST - Static Application Security Testing
    - name: Run Semgrep SAST
      uses: returntocorp/semgrep-action@v1
      with:
        config: >-
          p/security-audit
          p/secrets
          p/owasp-top-ten

    # Dependency scanning
    - name: Run Trivy FS scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'

    # Upload SARIF to GitHub Security tab
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

    # Container scanning
    - name: Build and scan Docker image
      uses: docker/build-push-action@v5
      with:
        push: false
        tags: app:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Run Trivy image scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'image'
        image-ref: app:${{ github.sha }}
        format: 'sarif'
        output: 'trivy-image-results.sarif'

    # Secret scanning
    - name: Secret scanning with Gitleaks
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}''',
        "best_practices": [
            "Run SAST scanning on every pull request",
            "Scan dependencies for known vulnerabilities (SCA)",
            "Scan container images for vulnerabilities",
            "Implement secret scanning to prevent credential leaks",
            "Upload results to GitHub Security tab for tracking",
        ],
        "confidence": 0.95,
    },
    "CI-SCALE-001": {
        "summary": "CI/CD pipeline lacks build caching causing slow builds and wasted resources.",
        "risk": "Without build caching, every CI/CD run downloads dependencies and builds from scratch, wasting time and resources.",
        "impact": "Slow build times (5-10x slower). Increased CI/CD costs. Wasted compute resources.",
        "fix_code": '''# Add dependency caching
- name: Cache node modules
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-''',
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
        "full_example": '''name: Optimized CI/CD Pipeline
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

    # Cache dependencies - speeds up npm install
    - name: Cache node modules
      id: cache-npm
      uses: actions/cache@v4
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-

    # Cache build artifacts
    - name: Cache build output
      id: cache-build
      uses: actions/cache@v4
      with:
        path: dist/
        key: ${{ runner.os }}-build-${{ github.sha }}
        restore-keys: |
          ${{ runner.os }}-build-

    # Install dependencies (uses cache)
    - name: Install dependencies
      run: npm ci

    # Build with caching
    - name: Build
      run: npm run build

    # Cache Docker layers for faster builds
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Cache Docker layers
      uses: actions/cache@v4
      with:
        path: /tmp/.buildx-cache
        key: ${{ runner.os }}-buildx-${{ github.sha }}
        restore-keys: |
          ${{ runner.os }}-buildx-

    # Build Docker image with cache
    - name: Build Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: false
        tags: app:${{ github.sha }}
        cache-from: type=local,src=/tmp/.buildx-cache
        cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max

    # Test with matrix for parallel execution
    - name: Run tests
      strategy:
        matrix:
          node-version: [16, 18, 20]
      run: npm test''',
        "best_practices": [
            "Cache dependencies between runs using actions/cache",
            "Use matrix builds for parallel testing",
            "Split large workflows into smaller jobs",
            "Use self-hosted runners for frequent builds",
            "Cache Docker layers with Buildx for faster image builds",
        ],
        "confidence": 0.90,
    },
    "CI-REL-002": {
        "summary": "CI/CD pipeline lacks automated testing causing unreliable deployments.",
        "risk": "Without automated testing, bugs and regressions reach production, causing service outages and user impact.",
        "impact": "Production bugs, service outages, customer dissatisfaction, and increased support costs.",
        "fix_code": '''# Add automated testing steps
- name: Run unit tests
  run: npm run test:unit

- name: Run integration tests
  run: npm run test:integration

- name: Run E2E tests
  run: npm run test:e2e''',
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
        "full_example": '''name: Complete CI/CD Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    # Unit tests with coverage
    - name: Run unit tests
      run: npm run test:unit -- --coverage

    # Integration tests
    - name: Run integration tests
      run: npm run test:integration
      env:
        DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}

    # E2E tests with Playwright
    - name: Install Playwright browsers
      run: npx playwright install --with-deps

    - name: Run E2E tests
      run: npm run test:e2e

    # Upload coverage report
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage/lcov.info
        fail_ci_if_error: true

    # Security audit
    - name: Run npm audit
      run: npm audit --audit-level=high

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    environment: staging
    steps:
    - uses: actions/checkout@v4
    - run: ./deploy.sh staging

  deploy-production:
    needs: [test, deploy-staging]
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    steps:
    - uses: actions/checkout@v4
    - run: ./deploy.sh production''',
        "best_practices": [
            "Run unit tests on every commit",
            "Run integration tests with test database",
            "Run E2E tests for critical user flows",
            "Enforce code coverage thresholds",
            "Use environment protection rules for production",
        ],
        "confidence": 0.90,
    },
    # Docker Rules
    "DOCKER-001": {
        "summary": "Docker container is running as root user which is a security risk.",
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host system.",
        "impact": "Root container access increases attack surface and potential damage from container breakout exploits.",
        "fix_code": '''# Create non-root user
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nodejs -u 1001

USER nodejs''',
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
        "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user and group
RUN addgroup --gid 1000 -S appgroup && \\
    adduser --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set proper ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Always run containers as non-root users",
            "Create a dedicated user and group for the application",
            "Use distroless or Alpine images for minimal attack surface",
            "Set proper file ownership before switching users",
            "Test application functionality after removing root access",
        ],
        "confidence": 0.95,
    },
    "DOCKER-002": {
        "summary": "Dockerfile uses 'latest' tag for base image causing non-reproducible builds.",
        "risk": "Using 'latest' tag leads to non-deterministic builds, making it impossible to reproduce builds or rollback to known-good versions.",
        "impact": "Unexpected base image changes can introduce vulnerabilities, breaking changes, or compatibility issues.",
        "fix_code": '''# Pin specific version
FROM node:18.17.0-alpine3.18

# Or use digest for immutability
FROM node@sha256:abc123def456...''',
        "fix_example": '''# Pin specific version
FROM node:18.17.0-alpine3.18

# Or use digest for immutability
FROM node@sha256:abc123def456...''',
        "full_example": '''# Production-ready Dockerfile with pinned base image
FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]

# Note: Update base image version periodically and test in staging
# Use Dependabot or Renovate to automate base image updates''',
        "best_practices": [
            "Always pin base images to specific versions (e.g., node:18.17.0-alpine3.18)",
            "Consider using image digests for complete immutability (e.g., node@sha256:...)",
            "Use automated tools like Dependabot to update base image versions",
            "Document base image versions in your README or documentation",
            "Test base image updates in a staging environment before production",
        ],
        "confidence": 0.95,
    },
    "docker_no_healthcheck": {
        "summary": "Docker container lacks HEALTHCHECK instruction for health monitoring.",
        "risk": "Without HEALTHCHECK, container orchestration systems cannot detect if the application inside the container is healthy or unresponsive.",
        "impact": "Unhealthy containers may continue receiving traffic, causing service degradation and poor user experience.",
        "fix_code": '''# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1''',
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
        "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck for orchestration systems
# Adjust interval, timeout, and retries based on your application
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# For different applications:
# Python/Flask: HEALTHCHECK CMD curl -f http://localhost:5000/health || exit 1
# Go:          HEALTHCHECK CMD wget -q --spider http://localhost:8080/health || exit 1
# Java/Spring: HEALTHCHECK CMD curl -f http://localhost:8080/actuator/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Set appropriate interval and timeout for your application",
            "Use /health or /healthz endpoint for health checks",
            "Ensure health endpoint checks critical dependencies (database, cache)",
            "Set start-period to allow application startup time",
            "Monitor health check failures in your orchestration system",
        ],
        "confidence": 0.95,
    },
    "DKR-SCALE-001": {
        "summary": "Base image uses 'latest' tag which can cause inconsistent deployments and non-reproducible builds.",
        "risk": "Using 'latest' tag leads to non-deterministic builds, making it impossible to reproduce builds or rollback to known-good versions. Unexpected base image changes can break your application.",
        "impact": "Your Docker builds will pull different base images over time, potentially introducing breaking changes, security vulnerabilities, or compatibility issues without your knowledge. This makes debugging and rollbacks extremely difficult.",
        "fix_code": '''# Pin specific version instead of latest
FROM node:18.17.0-alpine3.18

# Or use digest for complete immutability
FROM node@sha256:abc123def456...''',
        "fix_example": '''# Bad: Using latest tag (non-deterministic)
# FROM node:latest

# Good: Pin specific version
FROM node:18.17.0-alpine3.18

# Better: Use digest for complete immutability
# FROM node@sha256:1234567890abcdef...''',
        "full_example": '''# Production-ready Dockerfile with pinned base image
FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Always pin base images to specific versions (e.g., node:18.17.0-alpine3.18)",
            "Consider using image digests for complete immutability (e.g., node@sha256:...)",
            "Use automated tools like Dependabot to update base image versions",
            "Document base image versions in your README or documentation",
            "Test base image updates in a staging environment before production",
        ],
        "confidence": 0.95,
    },
    "docker_no_healthcheck": {
        "summary": "Docker container lacks HEALTHCHECK instruction for health monitoring.",
        "risk": "Without HEALTHCHECK, container orchestration systems cannot detect if the application inside the container is healthy or unresponsive.",
        "impact": "Unhealthy containers may continue receiving traffic, causing service degradation and poor user experience.",
        "fix_code": '''# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1''',
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
        "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck for orchestration systems
# Adjust interval, timeout, and retries based on your application
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# For different applications:
# Python/Flask: HEALTHCHECK CMD curl -f http://localhost:5000/health || exit 1
# Go:          HEALTHCHECK CMD wget -q --spider http://localhost:8080/health || exit 1
# Java/Spring: HEALTHCHECK CMD curl -f http://localhost:8080/actuator/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Set appropriate interval and timeout for your application",
            "Use /health or /healthz endpoint for health checks",
            "Ensure health endpoint checks critical dependencies (database, cache)",
            "Set start-period to allow application startup time",
            "Monitor health check failures in your orchestration system",
        ],
        "confidence": 0.95,
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
        "summary": "Docker container is running as root user which is a security risk.",
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host system.",
        "impact": "Root container access increases attack surface and potential damage from container breakout exploits.",
        "fix_code": '''# Create non-root user and group
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Switch to non-root user
USER appuser''',
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
        "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user and group
RUN addgroup --gid 1000 -S appgroup && \\
    adduser --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set proper ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Always run containers as non-root users",
            "Create a dedicated user and group for the application",
            "Use distroless or Alpine images for minimal attack surface",
            "Set proper file ownership before switching users",
            "Test application functionality after removing root access",
        ],
        "confidence": 0.95,
    },
    "DKR-SEC-002": {
        "summary": "Potential secrets exposed in Dockerfile ENV variables which can be accessed by anyone with access to the image.",
        "risk": "Secrets in Dockerfile ENV variables are stored in image layers and can be extracted by anyone with access to the image. This includes API keys, database passwords, and other sensitive credentials.",
        "impact": "Exposed credentials can lead to unauthorized access to databases, APIs, cloud resources, and sensitive data. This can result in data breaches, financial loss, and compliance violations.",
        "fix_code": '''# Use build arguments for build-time secrets (not stored in final image)
ARG API_KEY
RUN echo "Building with API key" # Don't echo the actual value

# Or use runtime environment variables (passed at container start)
# docker run -e API_KEY=secret my-image

# Or use Docker secrets (for Swarm)
# docker secret create my_secret secret.txt
# docker service create --secret my_secret my-service''',
        "fix_example": '''# Bad: Secret in ENV (stored in image layer)
# ENV API_KEY=sk-1234567890
# ENV DATABASE_PASSWORD=supersecret

# Good: Use ARG for build-time (not in final image)
ARG API_KEY
RUN echo "Building application..."

# Better: Pass secrets at runtime
# docker run -e API_KEY=$API_KEY my-image

# Best: Use secret management tools (AWS Secrets Manager, HashiCorp Vault)''',
        "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

# Use ARG for build-time variables (not stored in final image)
ARG NPM_TOKEN
RUN if [ -n "$NPM_TOKEN" ]; then \\
      echo "//registry.npmjs.org/:_authToken=$NPM_TOKEN" > ~/.npmrc; \\
    fi

# Copy and install dependencies
COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Don't include secrets in the image!
# Pass them at runtime: docker run -e API_KEY=secret my-image

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Never hardcode secrets in Dockerfile ENV instructions",
            "Use build arguments (ARG) for build-time secrets - they're not in final image",
            "Pass secrets at runtime using environment variables or Docker secrets",
            "Use secret management tools like AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault",
            "Scan Dockerfiles with tools like Hadolint or Trivy to detect exposed secrets",
        ],
        "confidence": 0.95,
    },
    "DKR-COST-001": {
        "summary": "Using a large base image increases build time, storage costs, and attack surface.",
        "risk": "Large base images like Ubuntu or Debian take longer to build, pull, and deploy. They also contain more packages that could have security vulnerabilities, increasing your attack surface.",
        "impact": "Slower CI/CD pipelines, increased storage costs, longer deployment times, and higher security risk from unnecessary packages. Can also increase cloud egress costs for multi-region deployments.",
        "fix_code": '''# Use Alpine or distroless images for smaller size
FROM node:18.17.0-alpine3.18

# Or use distroless for minimal attack surface
FROM gcr.io/distroless/nodejs18-debian11''',
        "fix_example": '''# Bad: Large base image (~150MB)
# FROM ubuntu:22.04
# FROM debian:bullseye

# Good: Alpine image (~50MB)
FROM node:18.17.0-alpine3.18

# Better: Distroless image (~30MB)
# FROM gcr.io/distroless/nodejs18-debian11

# Best: Multi-stage build for minimal final image
FROM node:18.17.0 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18.17.0-alpine3.18
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/index.js"]''',
        "full_example": '''# Multi-stage build for minimal production image
FROM node:18.17.0 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production image - minimal size
FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy only production dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy built application
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "dist/index.js"]''',
        "best_practices": [
            "Use Alpine-based images for smaller size (e.g., node:18-alpine)",
            "Consider distroless images for minimal attack surface",
            "Use multi-stage builds to keep production images small",
            "Regularly scan images for vulnerabilities with Trivy or Snyk",
            "Remove unnecessary packages and files to reduce image size",
        ],
        "confidence": 0.95,
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

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
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
        elif provider == "mistral":
            self._use_mock = not settings.MISTRAL_API_KEY
        else:
            # Auto-detect: use mock only if NO API keys are available
            self._use_mock = not any([
                settings.GEMINI_API_KEY,
                settings.OPENAI_API_KEY,
                settings.ANTHROPIC_API_KEY,
                settings.MISTRAL_API_KEY,
            ])

        logger.info(f"AIFixEnrichmentService initialized: provider={provider}, use_mock={self._use_mock}, has_mistral_key={bool(settings.MISTRAL_API_KEY)}")

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

        # Generate code diff if we have file content
        if file_content and result.get("fix_code"):
            result["before_code"] = file_content
            result["after_code"] = result.get("fix_code", "")
            result["unified_diff"] = self._generate_unified_diff(
                file_content,
                result.get("fix_code", ""),
                finding.get("file_path", "file")
            )

        return result

    def _generate_unified_diff(self, before: str, after: str, filename: str = "file") -> str:
        """Generate unified diff between before and after code."""
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)

        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            n=3
        )

        return ''.join(diff)

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
        self._ai_service: AIFixEnrichmentService | None = None

    def _get_ai_service(self) -> AIFixEnrichmentService:
        """Get or create AI enrichment service."""
        if self._ai_service is None:
            self._ai_service = AIFixEnrichmentService()
        return self._ai_service

    async def enrich_finding_async(self, finding: RuleFinding, file_content: str = "") -> RuleFinding:
        """
        Enrich a finding with AI-powered or static enrichment.

        Logic:
        - Try AI for ALL severities (not just HIGH/CRITICAL)
        - If AI fails → fallback to static FIX_EXAMPLES
        - Ensures ALL findings get complete data

        Args:
            finding: The finding to enrich
            file_content: Optional file content for AI context

        Returns:
            Finding with enrichment fields populated
        """
        severity = str(finding.severity).lower() if hasattr(finding.severity, 'value') else str(finding.severity).lower()

        # Try AI enrichment for ALL severities
        try:
            # PHASE 2D: RAG - Retrieve documentation before AI generation (NEW - Production Grade)
            rag_context = ""
            try:
                from app.rag import retrieve_docs
                rag_docs = retrieve_docs(finding.rule_id)
                if rag_docs and rag_docs.documents:
                    rag_context = rag_docs.to_context_string(max_docs=3)
                    logger.info(
                        "RAG documentation retrieved",
                        rule_id=finding.rule_id,
                        docs_count=len(rag_docs.documents),
                    )
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
                rag_context = ""

            ai_service = self._get_ai_service()
            logger.info(f"AI enrichment attempt: rule={finding.rule_id}, use_mock={ai_service._use_mock}")

            ai_fix = await ai_service.generate_fix({
                "rule_id": finding.rule_id,
                "rule_name": finding.rule_name,
                "severity": severity,
                "file_type": finding.file_path.split('.')[-1] if '.' in finding.file_path else "unknown",
                "description": finding.description,
                "rag_context": rag_context,  # Add RAG context to AI prompt
            }, file_content)

            # Apply AI enrichment
            if not finding.summary:
                finding.summary = ai_fix.get("summary", "")
            if not finding.risk:
                finding.risk = ai_fix.get("risk", "")
            if not finding.fix_example:
                # Try both "fix_code" (AI) and "fix_example" (static) keys
                finding.fix_example = ai_fix.get("fix_code") or ai_fix.get("fix_example") or ai_fix.get("full_example") or ""
            if not finding.fix_code:
                finding.fix_code = ai_fix.get("fix_code", "")
            if not finding.full_example:
                finding.full_example = ai_fix.get("full_example", "")
            if not finding.impact_analysis:
                finding.impact_analysis = ai_fix.get("impact", "")
            if not finding.impact:
                finding.impact = ai_fix.get("impact", "")
            if not finding.best_practices:
                finding.best_practices = ai_fix.get("best_practices", [])
            finding.confidence = ai_fix.get("confidence", 0.8)
            finding.ai_generated = True  # Mark as AI-generated

            # Add code diff fields for Code Diff Viewer
            if ai_fix.get("before_code"):
                finding.metadata['before_code'] = ai_fix.get("before_code")
            if ai_fix.get("after_code"):
                finding.metadata['after_code'] = ai_fix.get("after_code")
            if ai_fix.get("unified_diff"):
                finding.metadata['unified_diff'] = ai_fix.get("unified_diff")

            # Backwards compatibility: populate ai_explanation from summary
            if not finding.ai_explanation and finding.summary:
                finding.ai_explanation = finding.summary

            logger.info(f"✅ AI enrichment applied: rule={finding.rule_id}, ai_generated={finding.ai_generated}")

            logger.info(
                "AI enrichment applied",
                rule_id=finding.rule_id,
                severity=severity,
                confidence=finding.confidence,
                ai_generated=finding.ai_generated,
            )

            return finding

        except Exception as e:
            logger.warning(f"❌ AI enrichment failed, falling back to static: rule={finding.rule_id}, error={str(e)}")
            # Fall through to static enrichment

        # Static enrichment (fallback)
        return self.enrich_finding(finding)

    def enrich_finding(self, finding: RuleFinding) -> RuleFinding:
        """
        Enrich a single finding with static risk, impact, fix example, and documentation URL.

        Args:
            finding: The finding to enrich

        Returns:
            Finding with enrichment fields populated
        """
        logger.debug(f"Static enrichment: rule={finding.rule_id}")

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

        # Backwards compatibility: populate ai_explanation from summary
        if not finding.ai_explanation and finding.summary:
            finding.ai_explanation = finding.summary
            logger.debug(f"Enriched {finding.rule_id} with ai_explanation (from summary)")

        # Add documentation URL
        if not finding.documentation_url:
            finding.documentation_url = get_documentation_url(finding.rule_id)
            if finding.documentation_url:
                logger.debug(f"Enriched {finding.rule_id} with documentation_url")

        # Mark as static (not AI-generated)
        if not hasattr(finding, 'ai_generated'):
            finding.ai_generated = False

        logger.info(f"📝 Static enrichment complete: rule={finding.rule_id}, ai_generated={finding.ai_generated}")

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
