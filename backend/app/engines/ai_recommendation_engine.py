"""AI Recommendation Engine for generating remediation guidance."""

from dataclasses import dataclass
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AIRecommendation:
    """AI-generated recommendation."""

    finding_id: str
    rule_id: str
    explanation: str
    impact: str
    remediation_steps: list[str]
    code_example: Optional[str] = None
    verification_steps: Optional[list[str]] = None
    confidence: float = 1.0


class AIRecommendationEngine:
    """
    Generate AI-powered remediation recommendations.

    Uses LLM to generate human-readable explanations and fix guidance.
    Falls back to template-based recommendations if LLM unavailable.
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        self.llm_provider = llm_provider
        self._templates = self._load_templates()

    def _load_templates(self) -> dict[str, str]:
        """Load recommendation templates."""
        return {
            "root_user": """
**Explanation**: Running containers as root user is a security risk. If an attacker escapes the container, they gain root access to the host.

**Impact**:
- Container escape vulnerabilities become critical
- Attacker gains elevated privileges
- Violates CIS Docker Benchmark 4.1

**Remediation Steps**:
1. Create a non-root user in your Dockerfile
2. Set the USER instruction before CMD/ENTRYPOINT
3. Ensure application has permissions to run as non-root

**Example**:
```dockerfile
# Create user
RUN useradd -r -s /bin/false -u 1000 appuser

# Copy application files
COPY --chown=appuser:appuser . /app

# Switch to non-root user
USER appuser

WORKDIR /app
CMD ["./app"]
```

**Verification**: Run `docker inspect <image>` and check the User field is not empty/root.
""",
            "latest_tag": """
**Explanation**: Using 'latest' tag makes builds non-reproducible. The image content can change without your knowledge.

**Impact**:
- Builds are not reproducible
- Unexpected breaking changes may occur
- Difficult to rollback to known-good versions

**Remediation Steps**:
1. Identify the current image version
2. Pin to specific semantic version
3. Set up automated dependency updates

**Example**:
```dockerfile
# Bad
FROM node:latest

# Good
FROM node:18.17.0-alpine3.18

# Or use digest for immutability
FROM node@sha256:abc123...
```

**Verification**: Check Dockerfile for ':latest' or missing version tags.
""",
            "no_healthcheck": """
**Explanation**: HEALTHCHECK instruction helps Docker detect if container is functioning correctly.

**Impact**:
- Unhealthy containers continue receiving traffic
- Manual intervention required to detect failures
- Kubernetes liveness probes may not work correctly

**Remediation Steps**:
1. Identify application health endpoint
2. Add HEALTHCHECK instruction
3. Configure appropriate interval and timeout

**Example**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

**Verification**: Run `docker inspect <image>` and check Healthcheck section.
""",
            "no_resource_limits": """
**Explanation**: Without resource limits, containers can consume all host resources.

**Impact**:
- Noisy neighbor problems
- Node instability
- Pod evictions in Kubernetes

**Remediation Steps**:
1. Monitor current resource usage
2. Set appropriate limits based on usage + headroom
3. Configure requests for scheduling

**Example**:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

**Verification**: Run `kubectl describe pod` and check Limits/Requests.
""",
            "no_liveness_probe": """
**Explanation**: Liveness probes detect when containers are stuck or deadlocked.

**Impact**:
- Deadlocked containers never restart
- Wasted resources on unhealthy pods
- Potential service degradation

**Remediation Steps**:
1. Create health check endpoint in application
2. Configure liveness probe with appropriate settings
3. Set initial delay for application startup

**Example**:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Verification**: Run `kubectl describe pod` and check Liveness section.
""",
            "public_s3_bucket": """
**Explanation**: Public S3 buckets expose data to anyone on the internet.

**Impact**:
- Data breach risk
- Compliance violations (GDPR, HIPAA, SOC2)
- Potential data modification by attackers

**Remediation Steps**:
1. Remove public ACL from bucket
2. Add bucket policy denying public access
3. Enable S3 Block Public Access

**Example**:
```terraform
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"

  # Remove or set to private
  # acl = "private"  # Deprecated in favor of ownership_controls

  # Enable block public access
  object_ownership = "BucketOwnerEnforced"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**Verification**: Run `aws s3api get-bucket-acl --bucket <name>` and verify no public grants.
""",
            "open_security_group": """
**Explanation**: Security groups allowing SSH from 0.0.0.0/0 expose instances to brute force attacks.

**Impact**:
- Brute force attack surface
- Unauthorized access attempts
- Compliance violations

**Remediation Steps**:
1. Identify instances requiring SSH access
2. Restrict to specific IP ranges or bastion host
3. Consider using AWS Systems Manager Session Manager

**Example**:
```terraform
resource "aws_security_group" "ssh" {
  name = "ssh-access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Internal network only
  }
}

# Or use Session Manager (no SSH needed)
resource "aws_ssm_document" "session_manager" {
  name          = "session-manager-policy"
  document_type = "Session"
}
```

**Verification**: Run `aws ec2 describe-security-groups` and check for 0.0.0.0/0 on port 22.
""",
            "no_ci_tests": """
**Explanation**: CI pipelines without automated tests risk deploying broken code.

**Impact**:
- Bugs reach production
- Manual testing burden increases
- Slower feedback loop

**Remediation Steps**:
1. Add unit test stage to pipeline
2. Configure test coverage thresholds
3. Block merges on test failures

**Example**:
```yaml
# GitHub Actions
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Verification**: Check CI configuration for test execution steps.
""",
        }

    async def generate_recommendations(
        self,
        findings: list[dict[str, Any]],
        include_code_examples: bool = True,
    ) -> list[AIRecommendation]:
        """
        Generate AI recommendations for findings.

        Args:
            findings: List of findings from rule engine
            include_code_examples: Whether to include code examples

        Returns:
            List of AI recommendations
        """
        recommendations = []

        for finding in findings[:20]:  # Limit to top 20 findings
            try:
                recommendation = await self._generate_recommendation(finding, include_code_examples)
                recommendations.append(recommendation)
            except Exception as e:
                logger.warning(
                    "Failed to generate recommendation",
                    rule_id=finding.get("rule_id"),
                    error=str(e),
                )
                # Fall back to template
                recommendations.append(self._fallback_recommendation(finding))

        return recommendations

    async def _generate_recommendation(
        self,
        finding: dict[str, Any],
        include_code_examples: bool,
    ) -> AIRecommendation:
        """Generate recommendation using LLM if available."""
        # Try LLM if available
        if self.llm_provider:
            try:
                prompt = self._build_prompt(finding)
                response = await self.llm_provider.generate(prompt)
                return self._parse_llm_response(finding, response)
            except Exception as e:
                logger.warning("LLM generation failed, using template", error=str(e))

        # Fall back to template
        return self._fallback_recommendation(finding)

    def _fallback_recommendation(self, finding: dict[str, Any]) -> AIRecommendation:
        """Generate recommendation from template."""
        rule_id = finding.get("rule_id", "").lower()
        description = finding.get("description", "")

        # Select template based on rule ID or keywords
        template = self._select_template(rule_id, description)

        return AIRecommendation(
            finding_id=finding.get("id", ""),
            rule_id=rule_id,
            explanation=template.get("explanation", description),
            impact=template.get("impact", "Security or reliability risk detected"),
            remediation_steps=template.get("steps", ["Review and fix the configuration"]),
            code_example=template.get("code"),
            verification_steps=template.get("verification"),
            confidence=0.8,
        )

    def _select_template(self, rule_id: str, description: str) -> dict[str, Any]:
        """Select appropriate template based on rule."""
        description_lower = description.lower()

        template_map = {
            "root": "root_user",
            "latest": "latest_tag",
            "healthcheck": "no_healthcheck",
            "resource": "no_resource_limits",
            "liveness": "no_liveness_probe",
            "public": "public_s3_bucket",
            "ssh": "open_security_group",
            "test": "no_ci_tests",
        }

        for keyword, template_name in template_map.items():
            if keyword in rule_id.lower() or keyword in description_lower:
                return self._get_template(template_name)

        # Default template
        return {
            "explanation": "This finding indicates a potential security or reliability issue.",
            "impact": "May affect production readiness and security posture.",
            "steps": ["Review the finding", "Apply recommended fix", "Verify the change"],
        }

    def _get_template(self, name: str) -> dict[str, Any]:
        """Get template by name."""
        template = self._templates.get(name, "")
        if not template:
            return {}

        # Parse template into structured format
        return {
            "explanation": self._extract_section(template, "Explanation"),
            "impact": self._extract_section(template, "Impact"),
            "steps": self._extract_list(template, "Remediation Steps"),
            "code": self._extract_code_block(template),
            "verification": self._extract_list(template, "Verification"),
        }

    def _extract_section(self, text: str, section: str) -> str:
        """Extract section from template."""
        import re
        match = re.search(rf"\*\*{section}\*\*:\s*(.*?)(?=\n\*\*|$)", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_list(self, text: str, section: str) -> list[str]:
        """Extract list from template section."""
        import re
        match = re.search(rf"\*\*{section}\*\*:\s*(.*?)(?=\n\*\*|$)", text, re.DOTALL)
        if not match:
            return []

        content = match.group(1)
        items = re.findall(r"^\d+\.\s*(.+)$", content, re.MULTILINE)
        return items

    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract code block from template."""
        import re
        match = re.search(r"```(\w+)?\n(.*?)```", text, re.DOTALL)
        return match.group(2) if match else None

    def _build_prompt(self, finding: dict[str, Any]) -> str:
        """Build LLM prompt for recommendation."""
        return f"""You are a DevOps security expert. Generate remediation guidance for this finding:

Rule ID: {finding.get('rule_id')}
Rule Name: {finding.get('rule_name')}
Severity: {finding.get('severity')}
Category: {finding.get('category')}
Description: {finding.get('description')}
File: {finding.get('file_path', 'N/A')}

Provide:
1. A brief explanation of why this matters
2. The potential impact if not fixed
3. Step-by-step remediation instructions
4. A code example showing the fix
5. How to verify the fix works

Format as markdown with clear sections."""

    def _parse_llm_response(self, finding: dict[str, Any], response: str) -> AIRecommendation:
        """Parse LLM response into recommendation."""
        return AIRecommendation(
            finding_id=finding.get("id", ""),
            rule_id=finding.get("rule_id", ""),
            explanation=self._extract_section(response, "explanation") or response[:200],
            impact=self._extract_section(response, "impact") or "See explanation",
            remediation_steps=self._extract_list(response, "steps") or ["Fix the issue"],
            code_example=self._extract_code_block(response),
            verification_steps=self._extract_list(response, "verification"),
            confidence=0.9,
        )

    async def generate_executive_summary(
        self,
        overall_score: float,
        findings: list[dict[str, Any]],
        category_scores: dict[str, float],
    ) -> str:
        """Generate executive summary of analysis results."""
        critical_count = sum(1 for f in findings if f.get("severity") == "critical")
        high_count = sum(1 for f in findings if f.get("severity") == "high")

        summary = f"""## Production Readiness Assessment

**Overall Score: {overall_score:.1f}/100**

This analysis identified {len(findings)} findings, including {critical_count} critical and {high_count} high severity issues.

### Key Findings

"""

        # Add category breakdown
        for category, score in category_scores.items():
            status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            summary += f"- {status} **{category.title()}**: {score:.1f}/100\n"

        # Add top recommendations
        summary += "\n### Priority Actions\n\n"

        critical_findings = [f for f in findings if f.get("severity") == "critical"][:3]
        for i, finding in enumerate(critical_findings, 1):
            summary += f"{i}. **{finding.get('rule_name')}**: {finding.get('description')}\n"

        return summary
