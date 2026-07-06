"""AI Fix Code Generation Service - Production Grade."""

import structlog

logger = structlog.get_logger(__name__)


class FixGenerationStrategy:
    """Strategy pattern for generating fixes based on file type."""

    @staticmethod
    def generate_terraform_fix(finding: dict) -> str:
        """Generate Terraform fix code."""
        rule_id = finding.get("rule_id", "")
        file_path = finding.get("file_path", "")
        description = finding.get("description", "").lower()

        # Encryption fixes
        if "encryption" in description or "encrypt" in description:
            if "s3" in file_path.lower() or "s3" in description:
                return """# Enable S3 bucket server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.this.arn
    }
    bucket_key_enabled = true
  }
}

# Enable S3 bucket key for cost optimization
resource "aws_s3_bucket_bucket_key" "this" {
  bucket = aws_s3_bucket.this.id
}"""
            elif "ebs" in file_path.lower() or "ebs" in description:
                return """# Enable EBS volume encryption
resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-east-1a"
  size              = 100
  encrypted         = true
  kms_key_id        = aws_kms_key.this.arn
  
  tags = {
    Name        = "encrypted-volume"
    Environment = "production"
  }
}"""
            elif "rds" in file_path.lower() or "rds" in description:
                return """# Enable RDS instance encryption
resource "aws_db_instance" "encrypted" {
  identifier           = "encrypted-db"
  engine               = "postgres"
  engine_version       = "14.7"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.this.arn
  publicly_accessible  = false
  skip_final_snapshot  = true
  
  tags = {
    Name        = "encrypted-rds"
    Environment = "production"
  }
}"""

        # Versioning fixes
        if "versioning" in description or "version" in description:
            return """# Enable S3 bucket versioning
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable S3 bucket logging
resource "aws_s3_bucket_logging" "this" {
  bucket = aws_s3_bucket.this.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "log/"
}"""

        # Public access fixes
        if "public" in description or "access" in description:
            return """# Block all public access to S3 bucket
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket policy to deny unencrypted requests
resource "aws_s3_bucket_policy" "deny_unencrypted" {
  bucket = aws_s3_bucket.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.this.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      }
    ]
  })
}"""

        # Logging fixes
        if "logging" in description or "log" in description:
            return """# Enable S3 bucket access logging
resource "aws_s3_bucket_logging" "this" {
  bucket = aws_s3_bucket.this.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "access-logs/"
}

# CloudTrail logging configuration
resource "aws_cloudtrail" "main" {
  name                          = "production-trail"
  s3_bucket_name                = aws_s3_bucket.logs.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  
  event_selector {
    read_write_type           = "All"
    include_management_events = true
    
    data_resource {
      type = "AWS::S3::Object"
      values = ["${aws_s3_bucket.this.arn}/"]
    }
  }
}"""

        # Resource tagging fixes
        if "tag" in description or "cost" in description:
            return """# Add required tags for cost tracking and governance
tags = {
  Name        = "production-resource"
  Environment = "production"
  Owner       = "devops-team"
  Project     = "main-infrastructure"
  CostCenter  = "engineering"
  ManagedBy   = "terraform"
  CreatedAt   = formatdate("YYYY-MM-DD", timestamp())
  Compliance  = "required"
}"""

        # Security group fixes
        if "security" in description or "sg" in rule_id.lower():
            return """# Restrictive security group configuration
resource "aws_security_group" "restricted" {
  name        = "restricted-sg"
  description = "Security group with restricted access"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from anywhere"
  }

  # Allow SSH only from bastion
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "SSH from internal network only"
  }

  # All outbound traffic allowed
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "restricted-security-group"
    Environment = "production"
  }
}"""

        # Default fix template
        return f"""# Fix for {rule_id}
# File: {file_path}
#
# Apply this configuration to resolve the identified issue.
# Review carefully before applying to production environments.
#
# Recommendations:
# 1. Review the fix in a staging environment first
# 2. Ensure all dependencies are properly configured
# 3. Test thoroughly before deploying to production
# 4. Monitor for any unexpected behavior after deployment

# Add your fixed configuration here
# Replace this with the appropriate resource configuration
resource "example_resource" "fixed" {{
  # Add your fixed configuration here
  # Ensure all security best practices are followed
}}

# Add required tags
tags = {{
  Name        = "fixed-resource"
  Environment = "production"
  ManagedBy   = "terraform"
}}"""

    @staticmethod
    def generate_dockerfile_fix(finding: dict) -> str:
        """Generate Dockerfile fix code."""
        rule_id = finding.get("rule_id", "")
        description = finding.get("description", "").lower()

        # Non-root user fix
        if "root" in description or "user" in description:
            return """# Create non-root user and group
RUN addgroup --system --gid 1001 appgroup && \\
    adduser --system --uid 1001 --ingroup appgroup appuser

# Set proper ownership of application files
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Verify user
RUN whoami"""

        # Health check fix
        if "health" in description or "check" in description:
            return """# Add health check for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# Alternative health check for different applications
# For Node.js applications:
# HEALTHCHECK --interval=30s --timeout=3s \\
#   CMD node healthcheck.js || exit 1

# For Python applications:
# HEALTHCHECK --interval=30s --timeout=3s \\
#   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1"""

        # Base image pinning fix
        if "latest" in description or "pin" in description or "version" in description:
            return """# Pin base image to specific version for reproducibility
# Replace 'latest' with specific version tag or SHA
FROM node:18.17.0-alpine3.18@sha256:abc123...

# Alternative examples:
# FROM python:3.11.4-slim-bullseye
# FROM golang:1.21.0-alpine3.18
# FROM openjdk:17.0.8-slim-bullseye

# Always use specific versions, never 'latest'
# Consider using SHA256 digest for maximum security"""

        # Multi-stage build fix
        if "stage" in description or "build" in description:
            return """# Multi-stage build for smaller production image
# Build stage
FROM node:18.17.0-alpine3.18 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:18.17.0-alpine3.18

# Install ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup

USER appuser

EXPOSE 3000

CMD ["node", "dist/main.js"]"""

        # Layer caching fix
        if "layer" in description or "cache" in description:
            return """# Optimize Docker layer caching
# Copy dependency files first (changes less frequently)
COPY package*.json ./
RUN npm ci

# Then copy source code (changes more frequently)
COPY . .

# This ensures npm install layer is cached if package.json hasn't changed"""

        # Default fix
        return f"""# Fix for {rule_id}
# Review and apply appropriate Dockerfile changes

# Security best practices:
# 1. Use specific base image versions
# 2. Run as non-root user
# 3. Add health checks
# 4. Use multi-stage builds
# 5. Minimize layers and image size
# 6. Scan for vulnerabilities regularly

# Add your specific fix here"""

    @staticmethod
    def generate_kubernetes_fix(finding: dict) -> str:
        """Generate Kubernetes YAML fix code."""
        rule_id = finding.get("rule_id", "")
        description = finding.get("description", "").lower()

        # Resource limits fix
        if "resource" in description or "limit" in description or "memory" in description:
            return """apiVersion: v1
kind: Pod
metadata:
  name: example-with-resources
  labels:
    app: example
spec:
  containers:
  - name: app
    image: myapp:1.0.0
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
    ports:
    - containerPort: 3000
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
      periodSeconds: 5"""

        # Security context fix
        if "security" in description or "context" in description:
            return """apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  labels:
    app: secure-app
spec:
  # Pod-level security context
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
    # Container-level security context
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
      capabilities:
        drop:
          - ALL
    
    # Volume mounts for writable directories
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /var/cache
    
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
  
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}"""

        # Network policy fix
        if "network" in description or "policy" in description:
            return """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: myapp
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 3000"""

        # Service account fix
        if "service" in description and "account" in description:
            return """apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: production
  labels:
    app: myapp
automountServiceAccountToken: false

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-role-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: app-service-account
  namespace: production
roleRef:
  kind: Role
  name: app-role
  apiGroup: rbac.authorization.k8s.io"""

        # Default fix
        return f"""# Fix for {rule_id}
# Apply appropriate Kubernetes configuration

# Security best practices:
# 1. Set resource requests and limits
# 2. Use security contexts
# 3. Run as non-root user
# 4. Use network policies
# 5. Use service accounts with minimal permissions
# 6. Enable pod security standards

apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
  - name: app
    image: myapp:1.0.0
    # Add your configuration here"""

    @staticmethod
    def generate_ci_cd_fix(finding: dict) -> str:
        """Generate CI/CD pipeline fix code."""
        rule_id = finding.get("rule_id", "")
        description = finding.get("description", "").lower()

        # Security scanning fix
        if "security" in description or "scan" in description:
            return """name: Security Scan
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      with:
        fetch-depth: 0
    
    - name: Initialize CodeQL
      uses: github/codeql-action/init@v2
      with:
        languages: javascript
    
    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v2
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'"""

        # Secret detection fix
        if "secret" in description or "credential" in description:
            return """name: Secret Detection
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  detect-secrets:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      with:
        fetch-depth: 0
    
    - name: Install detect-secrets
      run: pip install detect-secrets
    
    - name: Run detect-secrets
      run: |
        detect-secrets scan --baseline .secrets.baseline
        detect-secrets audit .secrets.baseline
    
    - name: Run Gitleaks
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}"""

        # Dependency scanning fix
        if "dependency" in description or "dependabot" in description:
            return """name: Dependency Review
on:
  pull_request:
    branches: [main]

jobs:
  dependency-review:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Dependency Review
      uses: actions/dependency-review-action@v3
      with:
        fail-on-severity: moderate
        deny-licenses: GPL-3.0, AGPL-3.0
    
    - name: Run npm audit
      run: npm audit --audit-level=moderate
      if: always()
    
    - name: Run Snyk to check for vulnerabilities
      uses: snyk/actions/node@master
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=moderate"""

        # Default fix
        return f"""# Fix for {rule_id}
# Add security scanning to your CI/CD pipeline

name: Security and Quality Gates
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run security scans
      run: |
        echo "Add your security scanning commands here"
        # Examples:
        # - npm audit
        # - trivy fs .
        # - gitleaks detect
    
    - name: Upload security results
      run: |
        echo "Upload results to GitHub Security tab\""""

    @classmethod
    def generate_fix(cls, finding: dict, fix_type: str) -> str:
        """Generate fix based on type."""
        generators = {
            "terraform": cls.generate_terraform_fix,
            "dockerfile": cls.generate_dockerfile_fix,
            "kubernetes": cls.generate_kubernetes_fix,
            "ci_cd": cls.generate_ci_cd_fix,
        }

        generator = generators.get(fix_type, cls.generate_terraform_fix)
        return generator(finding)


class FixGenerationService:
    """Service for generating AI fix code."""

    def __init__(self):
        self.strategy = FixGenerationStrategy()

    def generate_fix(self, finding: dict, fix_type: str) -> dict:
        """
        Generate fix code for a finding.

        Args:
            finding: Finding data with rule_id, description, file_path, etc.
            fix_type: Type of fix (terraform, dockerfile, kubernetes, ci_cd)

        Returns:
            Dict with fix_code and metadata
        """
        try:
            fix_code = self.strategy.generate_fix(finding, fix_type)

            return {
                "success": True,
                "fix_code": fix_code,
                "fix_type": fix_type,
                "confidence": 0.9,
                "message": "Fix code generated successfully",
                "metadata": {
                    "file_path": finding.get("file_path", ""),
                    "rule_id": finding.get("rule_id", ""),
                },
            }
        except Exception as e:
            logger.error(f"Fix generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate fix code",
            }

    def validate_fix(self, fix_code: str, file_path: str) -> dict:
        """
        Validate generated fix code.

        Args:
            fix_code: The generated fix code
            file_path: Original file path

        Returns:
            Validation result
        """
        # Basic validation - can be enhanced with actual syntax checking
        if not fix_code or len(fix_code.strip()) == 0:
            return {
                "valid": False,
                "errors": ["Fix code is empty"],
            }

        # Check for common issues
        errors = []
        warnings = []

        if "TODO" in fix_code or "FIXME" in fix_code:
            warnings.append("Fix contains TODO/FIXME comments")

        if "# Replace" in fix_code or "# Add your" in fix_code:
            warnings.append("Fix contains placeholder comments - review required")

        # Check for syntax issues based on file type
        if ".tf" in file_path:
            # Basic Terraform validation
            if fix_code.count("{") != fix_code.count("}"):
                errors.append("Unbalanced braces in Terraform code")
            if "resource" not in fix_code and "data" not in fix_code:
                warnings.append("No resource or data block found")
        elif "Dockerfile" in file_path:
            # Basic Dockerfile validation
            if "FROM" not in fix_code:
                errors.append("No FROM instruction found")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def enhance_fix_with_context(
        self,
        fix_code: str,
        file_path: str,
        original_code: str = None,
    ) -> dict:
        """
        Enhance fix code with context and instructions.

        Args:
            fix_code: The generated fix code
            file_path: Path to the file
            original_code: Original code for comparison

        Returns:
            Enhanced fix with instructions
        """
        instructions = []

        # Generate file-specific instructions
        if ".tf" in file_path:
            instructions.extend([
                "1. Review the Terraform configuration carefully",
                "2. Run `terraform fmt` to format the code",
                "3. Run `terraform validate` to check syntax",
                "4. Run `terraform plan` to preview changes",
                "5. Apply changes with `terraform apply`",
            ])
        elif "Dockerfile" in file_path:
            instructions.extend([
                "1. Review the Dockerfile changes",
                "2. Build the image: `docker build -t myapp:latest .`",
                "3. Test the container locally",
                "4. Push to registry: `docker push myapp:latest`",
            ])
        elif ".yaml" in file_path or ".yml" in file_path:
            if "k8s" in file_path.lower() or "kubernetes" in file_path.lower():
                instructions.extend([
                    "1. Review the Kubernetes manifest",
                    "2. Validate: `kubectl apply --dry-run=client -f file.yaml`",
                    "3. Apply: `kubectl apply -f file.yaml`",
                    "4. Verify: `kubectl get pods`",
                ])

        return {
            "fix_code": fix_code,
            "instructions": instructions,
            "file_path": file_path,
            "requires_review": True,
        }


# Global instance
fix_generation_service = FixGenerationService()


def get_fix_generation_service() -> FixGenerationService:
    """Get the fix generation service."""
    return fix_generation_service
