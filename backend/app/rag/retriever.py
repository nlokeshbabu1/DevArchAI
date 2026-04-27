"""
RAG (Retrieval-Augmented Generation) Retriever Service for DevArchAI.

Stores DevSecOps documentation and retrieves relevant docs based on rule_id
to provide context to the LLM for generating better remediation fixes.

Uses keyword-based matching with relevance scoring -- no vector DB required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Document dataclass
# ---------------------------------------------------------------------------

@dataclass
class DocEntry:
    """A single documentation entry."""

    doc_id: str
    title: str
    category: str  # e.g. "cis_benchmark", "k8s_security", "terraform", "docker"
    content: str
    tags: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)  # Direct rule associations
    url: Optional[str] = None
    priority: int = 0  # Higher = more relevant


@dataclass
class RetrievalResult:
    """Result of a document retrieval operation."""

    query: str
    documents: list[DocEntry]
    total_available: int
    relevance_scores: dict[str, float] = field(default_factory=dict)

    def to_context_string(self, max_docs: int = 5) -> str:
        """
        Format retrieved documents as a context string for the LLM.

        Args:
            max_docs: Maximum number of documents to include.

        Returns:
            A formatted string suitable for inclusion in an LLM prompt.
        """
        docs = self.documents[:max_docs]
        if not docs:
            return "No relevant documentation found for this issue."

        parts: list[str] = [
            f"Retrieved {len(docs)} relevant document(s) for context:",
            "",
        ]
        for i, doc in enumerate(docs, 1):
            score = self.relevance_scores.get(doc.doc_id, 0.0)
            parts.append(f"--- Document {i} (relevance: {score:.2f}) ---")
            parts.append(f"Title: {doc.title}")
            if doc.url:
                parts.append(f"Reference: {doc.url}")
            parts.append(f"Category: {doc.category}")
            parts.append("")
            parts.append(doc.content)
            parts.append("")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert retrieval result to dictionary."""
        return {
            "query": self.query,
            "document_count": len(self.documents),
            "total_available": self.total_available,
            "documents": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "category": d.category,
                    "content_preview": d.content[:200] + "...",
                    "relevance_score": self.relevance_scores.get(d.doc_id, 0.0),
                    "url": d.url,
                }
                for d in self.documents[:5]
            ],
        }


# ---------------------------------------------------------------------------
# Documentation knowledge base
# ---------------------------------------------------------------------------

# Pre-loaded DevSecOps documentation entries
_KNOWLEDGE_BASE: list[DocEntry] = [
    # ===================================================================
    # CIS Benchmarks
    # ===================================================================
    DocEntry(
        doc_id="cis-aws-001",
        title="CIS AWS Foundations Benchmark - S3 Bucket Security",
        category="cis_benchmark",
        content=(
            "CIS AWS Foundations Benchmark v1.5.0, Section 2.1.1:\n\n"
            "Ensure S3 buckets are not publicly accessible. "
            "S3 buckets should have Block Public Access settings enabled at both "
            "the bucket and account level. Public access to S3 buckets can lead "
            "to data exposure and unauthorized access.\n\n"
            "Remediation:\n"
            "1. Enable S3 Block Public Access at the account level\n"
            "2. Enable S3 Block Public Access at the bucket level\n"
            "3. Review and remove any bucket policies granting public access\n"
            "4. Enable S3 bucket encryption (SSE-S3 or SSE-KMS)\n"
            "5. Enable S3 access logging for audit trail\n\n"
            "Terraform example:\n"
            'resource "aws_s3_bucket_public_access_block" "example" {\n'
            "  bucket = aws_s3_bucket.example.id\n"
            "  block_public_acls       = true\n"
            "  block_public_policy     = true\n"
            "  ignore_public_acls      = true\n"
            "  restrict_public_buckets = true\n"
            "}"
        ),
        tags=["s3", "public_access", "aws", "storage", "data_protection"],
        rule_ids=["AWS-S3-001", "AWS-S3-002", "AWS-S3-003"],
        url="https://www.cisecurity.org/benchmark/amazon_web_services",
        priority=10,
    ),
    DocEntry(
        doc_id="cis-aws-002",
        title="CIS AWS Foundations Benchmark - IAM Security",
        category="cis_benchmark",
        content=(
            "CIS AWS Foundations Benchmark v1.5.0, Section 1.1-1.22:\n\n"
            "IAM best practices for AWS accounts:\n\n"
            "1. Maintain current contact information for the AWS account\n"
            "2. Ensure security contact information is registered\n"
            "3. Delete the root user's access keys\n"
            "4. Ensure no root account access key exists\n"
            "5. Ensure MFA is enabled for the root account\n"
            "6. Ensure hardware MFA is enabled for the root account\n"
            "7. Eliminate use of the root user for administrative tasks\n"
            "8. Ensure multi-factor authentication is enabled for all IAM users\n"
            "9. Do not create access keys for the root user\n"
            "10. Ensure IAM policies are attached only to groups or roles\n\n"
            "Key principle: Follow least privilege. Grant only the permissions "
            "required to perform specific actions."
        ),
        tags=["iam", "mfa", "root_user", "aws", "access_control", "least_privilege"],
        rule_ids=["AWS-IAM-001", "AWS-IAM-002", "AWS-IAM-003"],
        url="https://www.cisecurity.org/benchmark/amazon_web_services",
        priority=10,
    ),
    DocEntry(
        doc_id="cis-k8s-001",
        title="CIS Kubernetes Benchmark - Pod Security",
        category="cis_benchmark",
        content=(
            "CIS Kubernetes Benchmark v1.8.0, Section 5.2:\n\n"
            "Pod Security Standards and Security Context:\n\n"
            "1. Minimize the admission of privileged containers\n"
            "   - Set securityContext.privileged to false\n"
            "2. Minimize the admission of containers with allowPrivilegeEscalation\n"
            "   - Set securityContext.allowPrivilegeEscalation to false\n"
            "3. Minimize the admission of containers running as root\n"
            "   - Set securityContext.runAsNonRoot to true\n"
            "   - Set securityContext.runAsUser to a non-zero UID\n"
            "4. Minimize the admission of containers with added capabilities\n"
            "   - Set securityContext.capabilities.drop to [\"ALL\"]\n"
            "5. Minimize the admission of containers with the NET_RAW capability\n"
            "   - Drop NET_RAW capability explicitly\n\n"
            "Use Pod Security Admission (PSA) or OPA/Gatekeeper to enforce "
            "these standards cluster-wide."
        ),
        tags=["kubernetes", "pod_security", "privileged", "root", "capabilities"],
        rule_ids=["K8S-SEC-001", "K8S-SEC-002", "K8S-SEC-003", "K8S-SEC-004"],
        url="https://www.cisecurity.org/benchmark/kubernetes",
        priority=10,
    ),

    # ===================================================================
    # Kubernetes Security
    # ===================================================================
    DocEntry(
        doc_id="k8s-sec-001",
        title="Kubernetes Security Best Practices - RBAC",
        category="k8s_security",
        content=(
            "Kubernetes RBAC (Role-Based Access Control) Best Practices:\n\n"
            "1. Use Roles and ClusterRoles instead of direct bindings\n"
            "2. Use RoleBindings and ClusterRoleBindings to assign roles\n"
            "3. Follow the principle of least privilege\n"
            "4. Avoid using wildcard (*) permissions\n"
            "5. Use namespaces to isolate resources and permissions\n"
            "6. Regularly audit RBAC policies\n"
            "7. Use ServiceAccounts for pod-to-API-server communication\n"
            "8. Disable anonymous access to the API server\n\n"
            "Example - Minimal ServiceAccount role:\n"
            "apiVersion: rbac.authorization.k8s.io/v1\n"
            "kind: Role\n"
            "metadata:\n"
            "  namespace: default\n"
            "  name: pod-reader\n"
            "rules:\n"
            "- apiGroups: [\"\"]\n"
            '  resources: ["pods"]\n'
            '  verbs: ["get", "watch", "list"]'
        ),
        tags=["kubernetes", "rbac", "service_account", "least_privilege", "access_control"],
        rule_ids=["K8S-RBAC-001", "K8S-RBAC-002"],
        url="https://kubernetes.io/docs/reference/access-authn-authz/rbac/",
        priority=8,
    ),
    DocEntry(
        doc_id="k8s-sec-002",
        title="Kubernetes Network Policies",
        category="k8s_security",
        content=(
            "Kubernetes Network Policies for Micro-segmentation:\n\n"
            "Network policies control traffic flow between pods. By default, "
            "all pods can communicate with all other pods. Network policies "
            "allow you to restrict this communication.\n\n"
            "Best practices:\n"
            "1. Default deny all ingress and egress traffic\n"
            "2. Explicitly allow only required communication paths\n"
            "3. Use namespace selectors for cross-namespace policies\n"
            "4. Use a CNI plugin that supports NetworkPolicy (Calico, Cilium)\n"
            "5. Test network policies in a non-production environment first\n\n"
            "Example - Default deny all ingress:\n"
            "apiVersion: networking.k8s.io/v1\n"
            "kind: NetworkPolicy\n"
            "metadata:\n"
            "  name: default-deny-ingress\n"
            "  namespace: default\n"
            "spec:\n"
            "  podSelector: {}\n"
            "  policyTypes:\n"
            "  - Ingress"
        ),
        tags=["kubernetes", "network_policy", "micro_segmentation", "cni"],
        rule_ids=["K8S-NET-001", "K8S-NET-002"],
        url="https://kubernetes.io/docs/concepts/services-networking/network-policies/",
        priority=7,
    ),
    DocEntry(
        doc_id="k8s-sec-003",
        title="Kubernetes Secrets Management",
        category="k8s_security",
        content=(
            "Kubernetes Secrets Management Best Practices:\n\n"
            "1. Never store secrets in ConfigMaps or environment variables in plain text\n"
            "2. Enable encryption at rest for etcd (where secrets are stored)\n"
            "3. Use external secret management (HashiCorp Vault, AWS Secrets Manager)\n"
            "4. Rotate secrets regularly\n"
            "5. Use RBAC to restrict access to secrets\n"
            "6. Enable audit logging for secret access\n"
            "7. Consider using Sealed Secrets or External Secrets Operator\n\n"
            "Enable etcd encryption:\n"
            "apiVersion: apiserver.config.k8s.io/v1\n"
            "kind: EncryptionConfiguration\n"
            "resources:\n"
            "  - resources:\n"
            "      - secrets\n"
            "    providers:\n"
            "      - aescbc:\n"
            "          keys:\n"
            "            - name: key1\n"
            "              secret: <base64-encoded-secret>"
        ),
        tags=["kubernetes", "secrets", "encryption", "etcd", "vault"],
        rule_ids=["K8S-SEC-005", "K8S-SEC-006"],
        url="https://kubernetes.io/docs/concepts/configuration/secret/",
        priority=8,
    ),

    # ===================================================================
    # Terraform Best Practices
    # ===================================================================
    DocEntry(
        doc_id="tf-best-001",
        title="Terraform State Management Best Practices",
        category="terraform",
        content=(
            "Terraform State Management Best Practices:\n\n"
            "1. Always use remote state storage (S3, GCS, Azure Blob)\n"
            "2. Enable state locking (DynamoDB for S3)\n"
            "3. Enable encryption at rest for state files\n"
            "4. Enable versioning on the state storage bucket\n"
            "5. Use separate state files per environment (dev, staging, prod)\n"
            "6. Restrict IAM access to the state bucket\n"
            "7. Never commit state files to version control\n"
            "8. Use workspaces for environment separation when appropriate\n\n"
            "Remote state configuration:\n"
            "terraform {\n"
            '  backend "s3" {\n'
            '    bucket         = "tf-state-prod"\n'
            '    key            = "terraform.tfstate"\n'
            '    region         = "us-east-1"\n'
            '    dynamodb_table = "terraform-lock"\n'
            "    encrypt        = true\n"
            "  }\n"
            "}"
        ),
        tags=["terraform", "state", "remote_backend", "s3", "dynamodb", "locking"],
        rule_ids=["TF-STATE-001", "TF-STATE-002", "TF-STATE-003", "TF-STATE-004"],
        url="https://developer.hashicorp.com/terraform/language/settings/backends",
        priority=10,
    ),
    DocEntry(
        doc_id="tf-best-002",
        title="Terraform Security Best Practices",
        category="terraform",
        content=(
            "Terraform Security Best Practices:\n\n"
            "1. Never hardcode secrets in .tf files -- use variables or secret managers\n"
            "2. Use .gitignore to exclude *.tfvars with sensitive data\n"
            "3. Use terraform validate and tflint in CI/CD pipelines\n"
            "4. Pin provider versions to avoid unexpected changes\n"
            "5. Use modules for reusable, tested infrastructure patterns\n"
            "6. Review plan output before applying in production\n"
            "7. Use sentinel policies (Terraform Cloud) or OPA for policy-as-code\n"
            "8. Enable detailed logging (TF_LOG=DEBUG) for troubleshooting\n\n"
            "Secure variable usage:\n"
            'variable "db_password" {\n'
            '  type      = string\n'
            '  sensitive = true\n'
            '}\n\n'
            "resource \"aws_db_instance\" \"example\" {\n"
            "  password = var.db_password  # Never hardcode\n"
            "}"
        ),
        tags=["terraform", "secrets", "security", "variables", "ci_cd", "modules"],
        rule_ids=["TF-SEC-001", "TF-SEC-002", "TF-SEC-003"],
        url="https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables",
        priority=9,
    ),
    DocEntry(
        doc_id="tf-best-003",
        title="Terraform Resource Security Configuration",
        category="terraform",
        content=(
            "Terraform Resource Security Configuration:\n\n"
            "Ensure all cloud resources are configured securely:\n\n"
            "S3 Buckets:\n"
            "- Enable encryption (SSE-S3 or SSE-KMS)\n"
            "- Block public access\n"
            "- Enable versioning and logging\n"
            "- Use bucket policies to restrict access\n\n"
            "EC2 Instances:\n"
            "- Use security groups (not NACLs) for fine-grained control\n"
            "- Disable public IPs for private subnets\n"
            "- Use IAM roles instead of access keys\n"
            "- Enable detailed monitoring\n\n"
            "RDS Instances:\n"
            "- Enable encryption at rest\n"
            "- Disable public accessibility\n"
            "- Use IAM database authentication\n"
            "- Enable automated backups\n\n"
            "Security Groups:\n"
            "- Follow least privilege for ingress/egress rules\n"
            "- Avoid 0.0.0.0/0 CIDR blocks\n"
            "- Use specific port ranges instead of all traffic"
        ),
        tags=["terraform", "aws", "s3", "ec2", "rds", "security_groups"],
        rule_ids=["AWS-S3-001", "AWS-EC2-001", "AWS-RDS-001", "AWS-SG-001"],
        url="https://developer.hashicorp.com/terraform/tutorials/aws-get-started",
        priority=8,
    ),

    # ===================================================================
    # Docker Security
    # ===================================================================
    DocEntry(
        doc_id="docker-sec-001",
        title="Docker Security Best Practices",
        category="docker_security",
        content=(
            "Docker Container Security Best Practices:\n\n"
            "1. Run containers as non-root user (USER directive)\n"
            "2. Use minimal base images (alpine, distroless, scratch)\n"
            "3. Scan images for vulnerabilities (Trivy, Snyk, Grype)\n"
            "4. Pin image versions with SHA digests\n"
            "5. Remove unnecessary packages and files from images\n"
            "6. Use multi-stage builds to reduce attack surface\n"
            "7. Set resource limits (memory, CPU)\n"
            "8. Use read-only root filesystem where possible\n"
            "9. Do not run with --privileged flag\n"
            "10. Use Docker Content Trust for image signing\n\n"
            "Example secure Dockerfile:\n"
            "FROM node:20-alpine AS builder\n"
            "WORKDIR /app\n"
            "COPY package*.json ./\n"
            "RUN npm ci --only=production\n"
            "COPY . .\n"
            "RUN npm run build\n\n"
            "FROM node:20-alpine\n"
            "RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser\n"
            "WORKDIR /app\n"
            "COPY --from=builder /app/dist ./dist\n"
            "COPY --from=builder /app/node_modules ./node_modules\n"
            "USER appuser\n"
            'EXPOSE 3000\n'
            'CMD ["node", "dist/main.js"]'
        ),
        tags=["docker", "container", "non_root", "minimal_image", "multi_stage"],
        rule_ids=["DOCKER-SEC-001", "DOCKER-SEC-002", "DOCKER-SEC-003", "DOCKER-SEC-004"],
        url="https://docs.docker.com/develop/develop-images/dockerfile_best-practices/",
        priority=10,
    ),
    DocEntry(
        doc_id="docker-sec-002",
        title="Docker Runtime Security",
        category="docker_security",
        content=(
            "Docker Runtime Security Configuration:\n\n"
            "When running containers, apply these security flags:\n\n"
            "1. --read-only: Mount root filesystem as read-only\n"
            "2. --no-new-privileges: Prevent privilege escalation\n"
            "3. --cap-drop=ALL: Drop all Linux capabilities\n"
            "4. --cap-add=<specific>: Add only required capabilities\n"
            "5. --memory and --cpus: Set resource limits\n"
            "6. --security-opt=no-new-privileges:true\n"
            "7. --userns-remap: Enable user namespace remapping\n\n"
            "Example secure docker run:\n"
            "docker run \\\n"
            "  --read-only \\\n"
            "  --no-new-privileges \\\n"
            "  --cap-drop=ALL \\\n"
            "  --cap-add=NET_BIND_SERVICE \\\n"
            "  --memory=512m \\\n"
            "  --cpus=1.0 \\\n"
            "  --user 1000:1000 \\\n"
            "  --tmpfs /tmp \\\n"
            "  myapp:latest"
        ),
        tags=["docker", "runtime", "capabilities", "read_only", "resource_limits"],
        rule_ids=["DOCKER-SEC-005", "DOCKER-SEC-006"],
        url="https://docs.docker.com/engine/security/",
        priority=8,
    ),

    # ===================================================================
    # CI/CD Security
    # ===================================================================
    DocEntry(
        doc_id="cicd-sec-001",
        title="CI/CD Pipeline Security Best Practices",
        category="cicd_security",
        content=(
            "CI/CD Pipeline Security Best Practices:\n\n"
            "1. Store secrets in CI/CD platform secret stores (not in code)\n"
            "2. Use OIDC for cloud provider authentication (no long-lived keys)\n"
            "3. Pin action versions in GitHub Actions (use SHA, not tags)\n"
            "4. Run security scanning (SAST, SCA, container scanning) in pipeline\n"
            "5. Require code review for pipeline configuration changes\n"
            "6. Use branch protection rules\n"
            "7. Limit permissions with GITHUB_TOKEN and OIDC\n"
            "8. Audit and rotate CI/CD secrets regularly\n"
            "9. Use ephemeral build environments\n"
            "10. Sign build artifacts (Sigstore/cosign)\n\n"
            "GitHub Actions OIDC for AWS:\n"
            "permissions:\n"
            "  id-token: write\n"
            "  contents: read\n\n"
            "jobs:\n"
            "  deploy:\n"
            "    steps:\n"
            "      - uses: aws-actions/configure-aws-credentials @v4\n"
            "        with:\n"
            "          role-to-assume: arn:aws:iam::123456789:role/deploy-role\n"
            "          aws-region: us-east-1"
        ),
        tags=["cicd", "github_actions", "oidc", "secrets", "pipeline_security"],
        rule_ids=["CI-SEC-001", "CI-SEC-002", "CI-SEC-003"],
        url="https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions",
        priority=7,
    ),
]


# ---------------------------------------------------------------------------
# Rule-to-category mapping for quick lookups
# ---------------------------------------------------------------------------

_RULE_TO_CATEGORIES: dict[str, list[str]] = {
    "TF-STATE": ["terraform"],
    "TF-SEC": ["terraform"],
    "AWS-S3": ["cis_benchmark", "terraform"],
    "AWS-IAM": ["cis_benchmark"],
    "AWS-EC2": ["cis_benchmark", "terraform"],
    "AWS-RDS": ["cis_benchmark", "terraform"],
    "AWS-SG": ["cis_benchmark", "terraform"],
    "K8S-SEC": ["cis_benchmark", "k8s_security"],
    "K8S-RBAC": ["k8s_security"],
    "K8S-NET": ["k8s_security"],
    "DOCKER-SEC": ["docker_security"],
    "CI-SEC": ["cicd_security"],
}


# ---------------------------------------------------------------------------
# Retriever service
# ---------------------------------------------------------------------------

class RAGRetriever:
    """
    Retrieves relevant DevSecOps documentation based on rule_id or keywords.

    Uses a combination of:
    1. Direct rule_id matching (highest priority)
    2. Category-based matching (from rule prefix)
    3. Keyword/tag matching (semantic relevance)

    Returns ranked results suitable for providing context to an LLM.
    """

    def __init__(self, documents: Optional[list[DocEntry]] = None) -> None:
        """
        Initialise the retriever with a knowledge base.

        Args:
            documents: Custom document list.  Defaults to the built-in
                       DevSecOps knowledge base.
        """
        self._documents = documents or list(_KNOWLEDGE_BASE)
        self._doc_by_id: dict[str, DocEntry] = {
            d.doc_id: d for d in self._documents
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        rule_id: str,
        max_results: int = 5,
        min_score: float = 0.1,
    ) -> RetrievalResult:
        """
        Retrieve relevant documentation for a given rule_id.

        Args:
            rule_id: The rule identifier (e.g. "K8S-SEC-001").
            max_results: Maximum number of documents to return.
            min_score: Minimum relevance score threshold.

        Returns:
            A RetrievalResult containing ranked documents.
        """
        scores: dict[str, float] = {}

        for doc in self._documents:
            score = self._compute_relevance(doc, rule_id)
            if score >= min_score:
                scores[doc.doc_id] = score

        # Sort by score descending
        sorted_ids = sorted(scores, key=lambda did: scores[did], reverse=True)
        top_ids = sorted_ids[:max_results]

        documents = [self._doc_by_id[did] for did in top_ids]

        result = RetrievalResult(
            query=rule_id,
            documents=documents,
            total_available=len(self._documents),
            relevance_scores={did: scores[did] for did in top_ids},
        )

        logger.info(
            "RAG retrieval complete",
            rule_id=rule_id,
            results_found=len(documents),
            top_score=scores.get(top_ids[0], 0.0) if top_ids else 0.0,
        )

        return result

    def retrieve_by_keywords(
        self,
        keywords: list[str],
        max_results: int = 5,
        min_score: float = 0.1,
    ) -> RetrievalResult:
        """
        Retrieve documentation by keyword matching.

        Useful when the rule_id is unknown or for general queries.

        Args:
            keywords: List of search keywords.
            max_results: Maximum number of documents to return.
            min_score: Minimum relevance score threshold.

        Returns:
            A RetrievalResult containing ranked documents.
        """
        scores: dict[str, float] = {}

        for doc in self._documents:
            score = self._keyword_score(doc, keywords)
            if score >= min_score:
                scores[doc.doc_id] = score

        sorted_ids = sorted(scores, key=lambda did: scores[did], reverse=True)
        top_ids = sorted_ids[:max_results]

        documents = [self._doc_by_id[did] for did in top_ids]

        return RetrievalResult(
            query=" ".join(keywords),
            documents=documents,
            total_available=len(self._documents),
            relevance_scores={did: scores[did] for did in top_ids},
        )

    def get_document(self, doc_id: str) -> Optional[DocEntry]:
        """Retrieve a specific document by its ID."""
        return self._doc_by_id.get(doc_id)

    def get_all_categories(self) -> list[str]:
        """Return all available document categories."""
        return sorted(set(d.category for d in self._documents))

    def get_documents_by_category(
        self,
        category: str,
        max_results: int = 10,
    ) -> list[DocEntry]:
        """Return all documents in a given category."""
        docs = [d for d in self._documents if d.category == category]
        return sorted(docs, key=lambda d: d.priority, reverse=True)[:max_results]

    def add_document(self, doc: DocEntry) -> None:
        """Add a new document to the knowledge base."""
        self._documents.append(doc)
        self._doc_by_id[doc.doc_id] = doc
        logger.info("Document added to knowledge base", doc_id=doc.doc_id)

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the knowledge base."""
        if doc_id in self._doc_by_id:
            doc = self._doc_by_id.pop(doc_id)
            self._documents.remove(doc)
            logger.info("Document removed from knowledge base", doc_id=doc_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _compute_relevance(self, doc: DocEntry, rule_id: str) -> float:
        """
        Compute relevance score between a document and a rule_id.

        Scoring:
        - Direct rule_id match: 1.0
        - Rule prefix match (e.g. K8S-SEC matches K8S-SEC-001): 0.7
        - Category match from rule prefix: 0.5
        - Tag keyword match: 0.3 per matching tag
        - Content keyword match: 0.1 per match

        Args:
            doc: The document to score.
            rule_id: The rule identifier.

        Returns:
            A relevance score between 0.0 and 1.0+.
        """
        score = 0.0

        # 1. Direct rule_id match (highest priority)
        if rule_id in doc.rule_ids:
            score += 1.0

        # 2. Rule prefix match
        rule_prefix = self._extract_rule_prefix(rule_id)
        if rule_prefix:
            for doc_rule_id in doc.rule_ids:
                if doc_rule_id.startswith(rule_prefix):
                    score += 0.7
                    break

        # 3. Category match from rule prefix
        matching_categories = _RULE_TO_CATEGORIES.get(rule_prefix, [])
        if doc.category in matching_categories:
            score += 0.5

        # 4. Tag matching against rule_id components
        rule_parts = rule_id.lower().replace("-", " ").split()
        for tag in doc.tags:
            tag_lower = tag.lower()
            for part in rule_parts:
                if part in tag_lower or tag_lower in part:
                    score += 0.3
                    break

        # 5. Content keyword matching
        content_lower = doc.content.lower()
        for part in rule_parts:
            if len(part) > 2 and part in content_lower:
                score += 0.1

        # Apply document priority multiplier
        if doc.priority > 0:
            score *= (1.0 + doc.priority * 0.05)

        return score

    def _keyword_score(
        self,
        doc: DocEntry,
        keywords: list[str],
    ) -> float:
        """
        Score a document based on keyword matching.

        Args:
            doc: The document to score.
            keywords: List of keywords to match against.

        Returns:
            A relevance score.
        """
        score = 0.0
        keywords_lower = [k.lower() for k in keywords]

        # Title match (highest weight)
        title_lower = doc.title.lower()
        for kw in keywords_lower:
            if kw in title_lower:
                score += 0.5

        # Tag match
        for tag in doc.tags:
            tag_lower = tag.lower()
            for kw in keywords_lower:
                if kw in tag_lower or tag_lower in kw:
                    score += 0.3

        # Content match
        content_lower = doc.content.lower()
        for kw in keywords_lower:
            if len(kw) > 2:
                count = len(re.findall(re.escape(kw), content_lower))
                score += min(count * 0.05, 0.5)  # Cap per keyword

        # Category match
        for kw in keywords_lower:
            if kw in doc.category.lower():
                score += 0.2

        # Priority multiplier
        if doc.priority > 0:
            score *= (1.0 + doc.priority * 0.05)

        return score

    @staticmethod
    def _extract_rule_prefix(rule_id: str) -> str:
        """
        Extract the rule prefix from a rule_id.

        Examples:
            "K8S-SEC-001" -> "K8S-SEC"
            "TF-STATE-001" -> "TF-STATE"
            "AWS-S3-001" -> "AWS-S3"
        """
        parts = rule_id.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:-1])
        return rule_id


# ---------------------------------------------------------------------------
# Module-level convenience function and singleton
# ---------------------------------------------------------------------------

_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """Get the global RAG retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def retrieve_docs(
    rule_id: str,
    max_results: int = 5,
) -> RetrievalResult:
    """
    Convenience function to retrieve documentation for a rule.

    Args:
        rule_id: The rule identifier.
        max_results: Maximum number of documents to return.

    Returns:
        A RetrievalResult with ranked documents.
    """
    return get_retriever().retrieve(rule_id, max_results=max_results)
