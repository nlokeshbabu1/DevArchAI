"""AI Fix Generation Service - Generates production-ready fix code using LLM.

This service generates REAL, production-ready, context-aware fixes for DevOps security issues.
Output format is strictly JSON for direct integration with production SaaS UI.
"""

from typing import Any

import structlog

from app.ai.engine import BaseLLMProvider, get_llm_provider
from app.config import settings

logger = structlog.get_logger(__name__)


# Expected fix types for each rule pattern (STRICT MAPPING)
EXPECTED_FIX_TYPES: dict[str, dict[str, Any]] = {
    # Kubernetes Security Rules
    "K8S-SEC-001": {"type": "NetworkPolicy", "keywords": ["NetworkPolicy", "networking.k8s.io", "podSelector", "ingress", "egress"]},
    "K8S-SEC-002": {"type": "securityContext", "keywords": ["securityContext", "runAsNonRoot", "runAsUser", "allowPrivilegeEscalation"]},
    "K8S-005": {"type": "securityContext", "keywords": ["securityContext", "privileged", "false"]},
    "K8S-006": {"type": "securityContext", "keywords": ["securityContext", "runAsNonRoot", "runAsUser"]},

    # Kubernetes Reliability Rules
    "K8S-001": {"type": "resources.limits", "keywords": ["resources", "limits", "cpu", "memory"]},
    "K8S-002": {"type": "resources.requests", "keywords": ["resources", "requests", "cpu", "memory"]},
    "K8S-003": {"type": "livenessProbe", "keywords": ["livenessProbe", "httpGet", "tcpSocket", "exec"]},
    "K8S-004": {"type": "readinessProbe", "keywords": ["readinessProbe", "httpGet", "tcpSocket", "exec"]},
    "K8S-REL-002": {"type": "PodDisruptionBudget", "keywords": ["PodDisruptionBudget", "policy/v1", "minAvailable", "maxUnavailable"]},
    "K8S-SCALE-001": {"type": "HorizontalPodAutoscaler", "keywords": ["HorizontalPodAutoscaler", "autoscaling", "minReplicas", "maxReplicas"]},

    # Docker Rules
    "DKR-SEC-001": {"type": "USER instruction", "keywords": ["USER", "adduser", "addgroup", "non-root"]},
    "DKR-REL-001": {"type": "HEALTHCHECK", "keywords": ["HEALTHCHECK", "CMD", "interval", "timeout", "retries"]},
    "DKR-001": {"type": "USER instruction", "keywords": ["USER", "adduser", "addgroup", "non-root"]},
    "DKR-004": {"type": "HEALTHCHECK", "keywords": ["HEALTHCHECK", "CMD", "interval", "timeout", "retries"]},

    # Terraform Rules
    "TF-STATE-001": {"type": "terraform backend", "keywords": ["terraform", "backend", "s3", "dynamodb_table"]},
    "TF-STATE-002": {"type": "terraform backend", "keywords": ["terraform", "backend", "s3", "remote"]},
    "TF-ENC-001": {"type": "S3 encryption", "keywords": ["aws_s3_bucket_server_side_encryption_configuration", "sse_algorithm", "AES256", "aws:kms"]},
    "TF-ENC-002": {"type": "EBS encryption", "keywords": ["encrypted", "true", "kms_key_id"]},
    "TF-ENC-003": {"type": "RDS encryption", "keywords": ["storage_encrypted", "true", "kms_key_id"]},
    "TF-NET-001": {"type": "security group", "keywords": ["aws_security_group", "ingress", "cidr_blocks", "0.0.0.0/0"]},
    "TF-IAM-001": {"type": "IAM policy", "keywords": ["aws_iam_policy", "Effect", "Action", "Resource", "Allow"]},
}


class AIFixGenerator:
    """Generate AI-powered fix suggestions for DevOps findings.
    
    Produces production-grade, copy-paste ready fixes with:
    - Context-aware code generation
    - Tech-specific best practices
    - Strict JSON output for UI integration
    """

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider
        self._provider_name = "auto"  # Use auto-detection based on API keys

    async def generate_fix(self, finding: dict[str, Any], file_content: str = "") -> dict[str, Any]:
        """
        Generate AI fix suggestion for a finding with automatic provider fallback.
        
        Fallback chain:
        1. Try Gemini (if GEMINI_API_KEY is set)
        2. Try OpenAI (if OPENAI_API_KEY is set)
        3. Try Anthropic (if ANTHROPIC_API_KEY is set)
        4. Fallback to Mock (static examples) - sets ai_generated=false, source="Static"
        
        Args:
            finding: Finding dict with rule_id, title, severity, file_type
            file_content: Optional actual file content for context

        Returns:
            dict with summary, risk, impact, fix_code, full_example, best_practices, confidence,
            ai_generated (bool), source (str)
        """
        # Get provider with automatic fallback based on API keys
        if not self.llm_provider:
            self.llm_provider = get_llm_provider()
            self._provider_name = type(self.llm_provider).__name__

        # Check if we're using mock provider (static fallback)
        from app.ai.engine import MockLLMProvider
        if isinstance(self.llm_provider, MockLLMProvider):
            logger.info("Using static fallback for AI fix generation", rule_id=finding.get("rule_id"))
            return self._generate_mock_fix(finding, file_content)

        # Try AI generation with fallback chain
        try:
            # Try with current provider first
            return await self._generate_ai_fix_with_fallback(finding, file_content)
        except Exception as e:
            logger.warning("AI fix generation failed, using static fallback",
                          provider=self._provider_name, error=str(e))
            # Return static fallback with proper flags
            return self._generate_mock_fix(finding, file_content)

    async def _generate_ai_fix_with_fallback(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate AI fix with automatic fallback to next provider on failure."""
        from app.ai.engine import (
            AnthropicProvider,
            GeminiProvider,
            MistralProvider,
            OpenAIProvider,
        )

        # Try Gemini first if available
        if settings.GEMINI_API_KEY and isinstance(self.llm_provider, GeminiProvider):
            try:
                result = await self._generate_fix_with_gemini(finding, file_content)
                result["ai_generated"] = True
                result["source"] = "Gemini"
                return result
            except Exception as e:
                logger.warning("Gemini failed, trying next provider", error=str(e))
                if settings.OPENAI_API_KEY:
                    self.llm_provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
                    self._provider_name = "OpenAI"
                    return await self._generate_fix_with_openai(finding, file_content)
                elif settings.ANTHROPIC_API_KEY:
                    self.llm_provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
                    self._provider_name = "Anthropic"
                    return await self._generate_fix_with_anthropic(finding, file_content)
                elif settings.MISTRAL_API_KEY:
                    self.llm_provider = get_llm_provider()  # Will return MistralProvider
                    self._provider_name = "Mistral"
                    return await self._generate_fix_with_mistral(finding, file_content)

        # Try OpenAI
        if settings.OPENAI_API_KEY and isinstance(self.llm_provider, OpenAIProvider):
            try:
                result = await self._generate_fix_with_openai(finding, file_content)
                result["ai_generated"] = True
                result["source"] = "OpenAI"
                return result
            except Exception as e:
                logger.warning("OpenAI failed, trying next provider", error=str(e))
                if settings.ANTHROPIC_API_KEY:
                    self.llm_provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
                    self._provider_name = "Anthropic"
                    return await self._generate_fix_with_anthropic(finding, file_content)
                elif settings.MISTRAL_API_KEY:
                    self.llm_provider = get_llm_provider()
                    self._provider_name = "Mistral"
                    return await self._generate_fix_with_mistral(finding, file_content)

        # Try Anthropic
        if settings.ANTHROPIC_API_KEY and isinstance(self.llm_provider, AnthropicProvider):
            try:
                result = await self._generate_fix_with_anthropic(finding, file_content)
                result["ai_generated"] = True
                result["source"] = "Anthropic"
                return result
            except Exception as e:
                logger.warning("Anthropic failed, trying next provider", error=str(e))
                if settings.MISTRAL_API_KEY:
                    self.llm_provider = get_llm_provider()
                    self._provider_name = "Mistral"
                    return await self._generate_fix_with_mistral(finding, file_content)

        # Try Mistral
        if settings.MISTRAL_API_KEY and isinstance(self.llm_provider, MistralProvider):
            try:
                result = await self._generate_fix_with_mistral(finding, file_content)
                result["ai_generated"] = True
                result["source"] = "Mistral"
                return result
            except Exception as e:
                logger.warning("Mistral failed, using static fallback", error=str(e))

        # Ultimate fallback to Mock
        logger.info("All AI providers failed, using static fallback")
        return self._generate_mock_fix(finding, file_content)

    async def _generate_fix_with_openai(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate fix using OpenAI."""
        if not self.llm_provider or not isinstance(self.llm_provider, OpenAIProvider):
            self.llm_provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)

        prompt = self._build_fix_prompt(finding, file_content)
        response = await self.llm_provider.generate(prompt)
        result = self._parse_ai_response(response, finding)
        result["ai_generated"] = True
        result["source"] = "OpenAI"
        return result

    async def _generate_fix_with_anthropic(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate fix using Anthropic."""
        if not self.llm_provider or not isinstance(self.llm_provider, AnthropicProvider):
            self.llm_provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)

        prompt = self._build_fix_prompt(finding, file_content)
        response = await self.llm_provider.generate(prompt)
        result = self._parse_ai_response(response, finding)
        result["ai_generated"] = True
        result["source"] = "Anthropic"
        return result

    async def _generate_fix_with_mistral(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate fix using Mistral AI."""
        if not self.llm_provider or not isinstance(self.llm_provider, MistralProvider):
            self.llm_provider = get_llm_provider()

        prompt = self._build_fix_prompt(finding, file_content)
        response = await self.llm_provider.generate(prompt)
        result = self._parse_ai_response(response, finding)
        result["ai_generated"] = True
        result["source"] = "Mistral"
        return result

    async def _generate_fix_with_gemini(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """
        Generate fix using Google Gemini specifically.
        
        This function handles Gemini API calls with proper error handling and JSON parsing.
        """
        if not self.llm_provider:
            self.llm_provider = get_llm_provider()

        # Verify it's actually a Gemini provider
        from app.ai.engine import GeminiProvider
        if not isinstance(self.llm_provider, GeminiProvider):
            # If provider isn't Gemini, use generic method
            return await self._generate_ai_fix(finding, file_content)

        prompt = self._build_fix_prompt(finding, file_content)

        try:
            # Call Gemini API
            response = await self.llm_provider.generate(prompt)

            # Parse response with robust JSON extraction
            result = self._parse_gemini_response(response, finding)

            # Validate confidence - fallback if too low
            if result.get("confidence", 0) < 0.6:
                logger.warning("Gemini confidence too low, using fallback", confidence=result.get("confidence"))
                return self._generate_mock_fix(finding, file_content)

            logger.info("Gemini fix generated", rule_id=finding.get("rule_id"), confidence=result.get("confidence"))
            return result

        except Exception as e:
            logger.error("Gemini fix generation failed", error=str(e))
            # Fallback to mock on any error
            return self._generate_mock_fix(finding, file_content)

    def _parse_gemini_response(self, response: str, finding: dict[str, Any]) -> dict[str, Any]:
        """
        Parse Gemini API response into structured format.
        Handles markdown code blocks and invalid JSON gracefully.
        VALIDATES fix matches rule_id.
        """
        import json
        import re

        try:
            # Clean response - remove markdown code blocks
            content = response.strip()
            if content.startswith("```"):
                # Extract JSON from markdown code block
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                if json_match:
                    content = json_match.group(1).strip()
                else:
                    content = content.strip("```").strip()

            # Try to parse JSON
            result = json.loads(content)

            # VALIDATE: Ensure fix matches rule_id
            rule_id = finding.get("rule_id", "")
            is_valid, error_msg = self._validate_ai_fix(result, rule_id)

            if not is_valid:
                logger.warning("AI fix validation failed - using fallback", rule_id=rule_id, error=error_msg)
                return self._generate_mock_fix(finding)

            logger.info("AI fix validated successfully", rule_id=rule_id)

            return {
                "summary": result.get("summary", finding.get("description", "")),
                "risk": result.get("risk", ""),
                "impact": result.get("impact", ""),
                "fix_code": result.get("fix_code", ""),
                "full_example": result.get("full_example", ""),
                "best_practices": result.get("best_practices", []),
                "confidence": float(result.get("confidence", 0.8)),
                "ai_generated": True,
                "source": "Gemini",
            }
        except json.JSONDecodeError as e:
            logger.warning("Gemini returned invalid JSON", error=str(e), response_preview=response[:200])
            # Try to extract any JSON-like structure from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    # Validate
                    rule_id = finding.get("rule_id", "")
                    is_valid, error_msg = self._validate_ai_fix(result, rule_id)
                    if not is_valid:
                        logger.warning("AI fix validation failed - using fallback", rule_id=rule_id, error=error_msg)
                        return self._generate_mock_fix(finding)

                    return {
                        "summary": result.get("summary", finding.get("description", "")),
                        "risk": result.get("risk", ""),
                        "impact": result.get("impact", ""),
                        "fix_code": result.get("fix_code", ""),
                        "full_example": result.get("full_example", ""),
                        "best_practices": result.get("best_practices", []),
                        "confidence": float(result.get("confidence", 0.7)),
                        "ai_generated": True,
                        "source": "Gemini",
                    }
                except:
                    pass
            # Ultimate fallback
            return self._generate_mock_fix(finding)
        except Exception as e:
            logger.warning("Failed to parse Gemini response", error=str(e))
            return self._generate_mock_fix(finding)

    async def _generate_ai_fix(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate fix using LLM (generic method for OpenAI/Anthropic)."""
        if not self.llm_provider:
            self.llm_provider = get_llm_provider()

        prompt = self._build_fix_prompt(finding, file_content)

        response = await self.llm_provider.generate(prompt)

        return self._parse_ai_response(response, finding)

    def _get_expected_fix_type(self, rule_id: str, category: str, file_type: str) -> str:
        """Get expected fix type based on rule_id for strict validation."""
        rule_id_upper = rule_id.upper()
        rule_id_lower = rule_id.lower()

        # Check exact match first
        if rule_id_upper in EXPECTED_FIX_TYPES:
            fix_info = EXPECTED_FIX_TYPES[rule_id_upper]
            return f"{fix_info['type']} (must contain: {', '.join(fix_info['keywords'][:3])})"

        # Check partial matches
        for pattern, fix_info in EXPECTED_FIX_TYPES.items():
            if pattern.split('-')[0] == rule_id_upper.split('-')[0]:  # Same prefix
                if pattern.endswith(rule_id_upper.split('-')[-1]):  # Same number
                    fix_info = EXPECTED_FIX_TYPES[pattern]
                    return f"{fix_info['type']} (must contain: {', '.join(fix_info['keywords'][:3])})"

        # Specific handling for known rule patterns
        if rule_id_upper == "K8S-SEC-001":
            return "NetworkPolicy (must contain: NetworkPolicy, networking.k8s.io, podSelector)"
        if rule_id_upper == "K8S-SCALE-001":
            return "HorizontalPodAutoscaler (must contain: HorizontalPodAutoscaler, autoscaling, minReplicas)"

        # Fallback based on category and file_type
        if 'kubernetes' in file_type.lower() or 'k8s' in rule_id_lower:
            if category.lower() == 'security':
                if 'network' in category.lower() or 'policy' in category.lower():
                    return "NetworkPolicy (must contain: NetworkPolicy, networking.k8s.io)"
                return "securityContext (must contain: securityContext, runAsNonRoot)"
            elif category.lower() == 'reliability':
                return "resources, probes, or PDB (based on issue type)"
            elif category.lower() == 'scalability':
                return "HorizontalPodAutoscaler (must contain: HorizontalPodAutoscaler, autoscaling)"
        elif 'docker' in file_type.lower():
            if 'user' in category.lower() or 'root' in category.lower():
                return "USER instruction"
            elif 'health' in category.lower():
                return "HEALTHCHECK instruction"
        elif 'terraform' in file_type.lower():
            if 'state' in category.lower():
                return "terraform backend block"
            elif 'encryption' in category.lower():
                return "encryption configuration"

        return "Appropriate fix for the detected issue"

    def _validate_ai_fix(self, fix_result: dict[str, Any], rule_id: str) -> tuple[bool, str]:
        """
        Validate AI-generated fix matches the rule_id.

        Returns:
            (is_valid, error_message)
        """
        rule_id_upper = rule_id.upper()
        fix_code = fix_result.get("fix_code", "")

        # Get expected fix type
        expected = EXPECTED_FIX_TYPES.get(rule_id_upper)
        if not expected:
            # No strict validation for unknown rules
            return True, ""

        # Check if fix_code contains expected keywords
        keywords = expected["keywords"]
        found_keywords = [kw for kw in keywords if kw.lower() in fix_code.lower()]

        # STRICT: At least 70% of keywords must match (was 50%)
        if len(found_keywords) < len(keywords) * 0.7:
            error_msg = f"AI fix mismatch for {rule_id}: expected {expected['type']}, got fix with keywords {found_keywords}"
            return False, error_msg

        # Specific validations for critical rules - MUST match exactly
        if rule_id_upper == "K8S-SEC-001":
            if "NetworkPolicy" not in fix_code and "networking.k8s.io" not in fix_code:
                return False, f"K8S-SEC-001 requires NetworkPolicy, got: {fix_code[:100]}..."

        if rule_id_upper == "K8S-SCALE-001":
            if "HorizontalPodAutoscaler" not in fix_code and "autoscaling" not in fix_code:
                return False, f"K8S-SCALE-001 requires HorizontalPodAutoscaler, got: {fix_code[:100]}..."

        if rule_id_upper in ["K8S-005", "K8S-006", "K8S-SEC-002"]:
            if "securityContext" not in fix_code and "runAsNonRoot" not in fix_code:
                return False, f"{rule_id} requires securityContext, got: {fix_code[:100]}..."

        if rule_id_upper in ["DKR-SEC-001", "DKR-001"]:
            if "USER" not in fix_code:
                return False, f"{rule_id} requires USER instruction, got: {fix_code[:100]}..."

        if rule_id_upper in ["DKR-REL-001", "DKR-004"]:
            if "HEALTHCHECK" not in fix_code:
                return False, f"{rule_id} requires HEALTHCHECK, got: {fix_code[:100]}..."

        if rule_id_upper == "K8S-001":
            if "resources" not in fix_code.lower() or "limits" not in fix_code.lower():
                return False, f"{rule_id} requires resources.limits, got: {fix_code[:100]}..."

        if rule_id_upper == "K8S-003":
            if "livenessProbe" not in fix_code:
                return False, f"{rule_id} requires livenessProbe, got: {fix_code[:100]}..."

        if rule_id_upper == "K8S-004":
            if "readinessProbe" not in fix_code:
                return False, f"{rule_id} requires readinessProbe, got: {fix_code[:100]}..."

        return True, ""

    def _build_fix_prompt(self, finding: dict[str, Any], file_content: str) -> str:
        """Build prompt for AI fix generation with STRICT rule-to-fix mapping."""
        rule_id = finding.get("rule_id", "UNKNOWN")
        title = finding.get("rule_name", "Unknown Issue")
        severity = finding.get("severity", "MEDIUM")
        category = finding.get("category", "security")
        file_type = finding.get("file_type", "unknown") or finding.get("category", "unknown")
        description = finding.get("description", "")
        recommendation = finding.get("recommendation", "")
        file_path = finding.get("file_path", "")

        # Get expected fix type based on rule_id pattern
        expected_fix_type = self._get_expected_fix_type(rule_id, category, file_type)

        return f"""You are a senior DevSecOps engineer and cloud security expert working in a production-grade SaaS platform (similar to Snyk/Wiz).

Your job is to analyze a security issue in a DevOps repository and generate a REAL, production-ready, context-aware fix.

You must behave like a senior engineer reviewing a real production system.

---

⚠️ CRITICAL RULES - READ CAREFULLY:

1. FIX MUST MATCH THE SPECIFIC ISSUE TYPE
   - Your fix_code MUST address the exact problem described
   - DO NOT generate generic Kubernetes/Terraform/Docker fixes
   - The fix MUST contain the specific resource/configuration mentioned in "Expected Fix Type"

2. USE RULE_ID AS PRIMARY CONTEXT
   - Each rule_id corresponds to a SPECIFIC issue
   - Your fix MUST be tailored to that specific rule_id
   - Example: K8S-SEC-001 = NetworkPolicy, NOT securityContext

3. VALIDATE YOUR OUTPUT
   - Before responding, verify your fix_code contains the expected resource type
   - If unsure, return confidence < 0.6 to trigger fallback

4. NO GENERIC FIXES
   - Do NOT generate random Kubernetes manifests
   - Do NOT copy-paste generic templates
   - Your fix MUST solve the specific issue described

---

INPUT:

Rule ID: {rule_id}
Issue Title: {title}
Severity: {severity}
Category: {category}
Technology: {file_type}
File Path: {file_path}
Description: {description}
Recommendation: {recommendation}

Expected Fix Type: {expected_fix_type}

{'File Content:' if file_content else ''}
{file_content if file_content else 'N/A - Generate fix based on rule knowledge'}

---

OUTPUT FORMAT (STRICT JSON ONLY):

{{
  "summary": "1-2 sentence explanation of the specific issue",
  "risk": "Why THIS specific issue is dangerous",
  "impact": "Real-world impact if THIS issue is not fixed",
  "fix_code": "Production-ready fix that addresses THIS specific issue",
  "full_example": "Complete corrected file showing the fix in context",
  "best_practices": ["Specific best practice 1", "Specific best practice 2"],
  "confidence": 0.0-1.0
}}

---

EXAMPLE MAPPINGS (DO NOT DEVIATE):

K8S-SEC-001 (Missing NetworkPolicy) -> MUST generate NetworkPolicy YAML
K8S-005/K8S-006 (Running as root) -> MUST generate securityContext with runAsNonRoot
K8S-001 (No resource limits) -> MUST generate resources.limits
K8S-003/K8S-004 (Missing probes) -> MUST generate livenessProbe/readinessProbe
DKR-SEC-001 (Running as root) -> MUST generate USER instruction
DKR-REL-001 (Missing HEALTHCHECK) -> MUST generate HEALTHCHECK instruction
TF-STATE-001 (No remote state) -> MUST generate terraform backend block
TF-ENC-001 (S3 unencrypted) -> MUST generate aws_s3_bucket_server_side_encryption_configuration

---

RESPONSE VALIDATION:

Before sending your response, verify:
1. fix_code contains the expected resource type from "Expected Fix Type"
2. fix_code directly addresses the issue in "Description"
3. confidence reflects your certainty (use < 0.6 if unsure)

Respond ONLY with valid JSON, no other text."""

    def _parse_ai_response(self, response: str, finding: dict[str, Any]) -> dict[str, Any]:
        """Parse AI response into structured format. VALIDATES fix matches rule_id."""
        import json
        import re

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)

            # VALIDATE: Ensure fix matches rule_id
            rule_id = finding.get("rule_id", "")
            is_valid, error_msg = self._validate_ai_fix(result, rule_id)

            if not is_valid:
                logger.warning("AI fix validation failed - using fallback", rule_id=rule_id, error=error_msg)
                return self._generate_mock_fix(finding)

            logger.info("AI fix validated successfully", rule_id=rule_id)

            # Determine source from provider
            source = "AI"
            if self.llm_provider:
                provider_name = type(self.llm_provider).__name__
                if "OpenAI" in provider_name:
                    source = "OpenAI"
                elif "Anthropic" in provider_name:
                    source = "Anthropic"
                elif "Gemini" in provider_name:
                    source = "Gemini"

            return {
                "summary": result.get("summary", finding.get("description", "")),
                "risk": result.get("risk", ""),
                "impact": result.get("impact", ""),
                "fix_code": result.get("fix_code", ""),
                "full_example": result.get("full_example", ""),
                "best_practices": result.get("best_practices", []),
                "confidence": float(result.get("confidence", 0.8)),
                "ai_generated": True,
                "source": source,
            }
        except Exception as e:
            logger.warning("Failed to parse AI response", error=str(e))
            return self._generate_mock_fix(finding)

    def _generate_mock_fix(self, finding: dict[str, Any], file_content: str = "") -> dict[str, Any]:
        """Generate mock fix (fallback when AI unavailable) - Production quality.
        
        Sets ai_generated=false and source="Static" to indicate static fallback.
        """
        rule_id = finding.get("rule_id", "")
        title = finding.get("rule_name", "")
        severity = finding.get("severity", "MEDIUM")
        category = finding.get("category", "security")
        file_type = finding.get("file_type", "unknown") or finding.get("category", "unknown")
        description = finding.get("description", "")
        file_path = finding.get("file_path", "")

        # Determine technology from file path or rule_id
        tech = self._detect_technology(file_path, rule_id, file_type)

        # Generate context-aware mock fix based on technology and issue type
        result = self._generate_tech_specific_fix(tech, rule_id, title, description, file_content, file_path)

        # Set static fallback flags
        result["ai_generated"] = False
        result["source"] = "Static"

        return result

    def _detect_technology(self, file_path: str, rule_id: str, file_type: str) -> str:
        """Detect technology from file path and rule ID."""
        if file_path:
            if file_path.endswith(".tf") or "terraform" in file_path.lower():
                return "terraform"
            if "Dockerfile" in file_path or file_path.endswith(".dockerfile"):
                return "dockerfile"
            if file_path.endswith((".yaml", ".yml")) and ("k8s" in file_path.lower() or "kubernetes" in file_path.lower()):
                return "kubernetes"
            if file_path.endswith((".yaml", ".yml")) and ("ci" in file_path.lower() or "workflow" in file_path.lower() or ".github" in file_path):
                return "ci_cd"

        # Check rule_id prefix
        if rule_id.startswith("TF-"):
            return "terraform"
        if rule_id.startswith(("DKR-", "DOCKER-")):
            return "dockerfile"
        if rule_id.startswith("K8S-"):
            return "kubernetes"
        if rule_id.startswith("CI-"):
            return "ci_cd"

        # Fallback to file_type
        file_type_lower = file_type.lower() if file_type else ""
        if "terraform" in file_type_lower:
            return "terraform"
        if "docker" in file_type_lower:
            return "dockerfile"
        if "kubernetes" in file_type_lower or "k8s" in file_type_lower:
            return "kubernetes"
        if "cicd" in file_type_lower or "ci_cd" in file_type_lower or "github" in file_type_lower:
            return "ci_cd"

        return "terraform"  # Default fallback

    def _generate_tech_specific_fix(
        self,
        tech: str,
        rule_id: str,
        title: str,
        description: str,
        file_content: str,
        file_path: str = ""
    ) -> dict[str, Any]:
        """Generate technology-specific fix based on context."""
        desc_lower = description.lower()
        title_lower = title.lower()

        # Terraform fixes
        if tech == "terraform":
            return self._generate_terraform_fix(rule_id, title, description, file_content)

        # Dockerfile fixes
        if tech == "dockerfile":
            return self._generate_dockerfile_fix(rule_id, title, description, file_content)

        # Kubernetes fixes
        if tech == "kubernetes":
            return self._generate_kubernetes_fix(rule_id, title, description, file_content, file_path)

        # CI/CD fixes
        if tech == "ci_cd":
            return self._generate_cicd_fix(rule_id, title, description, file_content)

        # Default fallback
        return self._get_default_fix(rule_id, title, description)

    def _generate_terraform_fix(
        self,
        rule_id: str,
        title: str,
        description: str,
        file_content: str
    ) -> dict[str, Any]:
        """Generate Terraform-specific fix."""
        desc_lower = description.lower()

        # State management issues
        if "state" in desc_lower or "backend" in desc_lower or "TF-STATE" in rule_id:
            return {
                "summary": "Terraform state is not configured with remote backend and locking, risking state corruption and team collaboration issues.",
                "risk": "Local state cannot be shared across team members or CI/CD pipelines. Concurrent terraform apply operations can corrupt state, causing infrastructure drift and deployment failures.",
                "impact": "Multiple engineers running terraform apply simultaneously can corrupt state, leading to infrastructure drift, failed deployments, and potential resource duplication or orphaning.",
                "fix_code": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
                "full_example": '''terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      ManagedBy   = "terraform"
      Environment = "production"
    }
  }
}''',
                "best_practices": [
                    "Use separate state files for different environments (dev/staging/prod)",
                    "Enable versioning on the S3 bucket storing state",
                    "Restrict IAM access to state bucket to authorized principals only",
                    "Use DynamoDB table with pay-per-request billing for state locking",
                ],
                "confidence": 0.95,
            }

        # Encryption issues
        if "encrypt" in desc_lower or "TF-ENC" in rule_id:
            if "s3" in desc_lower:
                return {
                    "summary": "S3 bucket lacks server-side encryption, exposing stored data at rest to unauthorized access.",
                    "risk": "Unencrypted S3 buckets expose stored data to unauthorized access if bucket policies are misconfigured or AWS account is compromised. Violates compliance requirements (GDPR, HIPAA, PCI-DSS).",
                    "impact": "Data breaches, compliance violations, regulatory fines, and reputational damage from exposed sensitive data.",
                    "fix_code": '''resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.this.arn
    }
    bucket_key_enabled = true
  }
}''',
                    "full_example": '''resource "aws_s3_bucket" "this" {
  bucket = "my-secure-bucket"

  tags = {
    Name        = "secure-bucket"
    Environment = "production"
  }
}

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

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}''',
                    "best_practices": [
                        "Use KMS keys instead of S3-managed keys for audit trail",
                        "Enable bucket key to reduce KMS API costs",
                        "Block all public access at bucket level",
                        "Enable versioning for data recovery",
                    ],
                    "confidence": 0.95,
                }
            elif "rds" in desc_lower or "database" in desc_lower:
                return {
                    "summary": "RDS instance lacks storage encryption, exposing database data at rest.",
                    "risk": "Unencrypted databases expose sensitive data at rest including PII, financial data, and application secrets. Violates HIPAA, PCI-DSS, SOC2 compliance.",
                    "impact": "Data breaches from disk access, compliance violations, regulatory fines up to 4% of annual revenue (GDPR), and reputational damage.",
                    "fix_code": '''resource "aws_db_instance" "this" {
  identifier           = "secure-db"
  engine               = "postgres"
  engine_version       = "14.7"
  instance_class       = "db.t3.medium"
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.db.arn
  publicly_accessible  = false
  skip_final_snapshot  = false
  final_snapshot_identifier = "final-snapshot"
}''',
                    "full_example": '''resource "aws_kms_key" "db" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "rds-encryption-key"
    Environment = "production"
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name        = "db-subnet-group"
    Environment = "production"
  }
}

resource "aws_db_instance" "this" {
  identifier           = "secure-db"
  engine               = "postgres"
  engine_version       = "14.7"
  instance_class       = "db.t3.medium"
  allocated_storage    = 100
  max_allocated_storage = 500
  
  db_name              = "appdb"
  username             = var.db_username
  password             = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.db.arn
  publicly_accessible  = false
  
  multi_az               = true
  auto_minor_version_upgrade = true
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  skip_final_snapshot  = false
  final_snapshot_identifier = "final-snapshot-${aws_db_instance.this.identifier}"
  
  tags = {
    Name        = "secure-rds"
    Environment = "production"
  }
}''',
                    "best_practices": [
                        "Enable Multi-AZ for high availability",
                        "Use AWS Secrets Manager for database credentials",
                        "Configure automated backups with appropriate retention",
                        "Restrict security group access to application only",
                    ],
                    "confidence": 0.95,
                }
            else:
                # Generic encryption fix
                return {
                    "summary": "Resource lacks encryption at rest, exposing sensitive data.",
                    "risk": "Unencrypted storage exposes data at rest to unauthorized access if physical media or snapshots are compromised.",
                    "impact": "Data breaches, compliance violations (GDPR, HIPAA, PCI-DSS), and regulatory fines.",
                    "fix_code": '''# Enable encryption for the resource
# For EBS volumes:
encrypted = true
kms_key_id = aws_kms_key.this.arn

# For S3 buckets:
server_side_encryption_configuration {
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}''',
                    "full_example": '''# KMS key for encryption
resource "aws_kms_key" "this" {
  description             = "KMS key for resource encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "encryption-key"
    Environment = "production"
  }
}

# Example: Encrypted EBS volume
resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-east-1a"
  size              = 100
  encrypted         = true
  kms_key_id        = aws_kms_key.this.arn

  tags = {
    Name        = "encrypted-volume"
    Environment = "production"
  }
}''',
                    "best_practices": [
                        "Use KMS keys with automatic rotation enabled",
                        "Enable encryption for all snapshots derived from encrypted volumes",
                        "Use separate KMS keys per environment for isolation",
                    ],
                    "confidence": 0.90,
                }

        # Security group / networking issues
        if "security group" in desc_lower or "ingress" in desc_lower or "TF-NET" in rule_id:
            return {
                "summary": "Security group allows unrestricted ingress from 0.0.0.0/0, exposing services to the internet.",
                "risk": "Security groups allowing 0.0.0.0/0 expose services directly to the internet, making them vulnerable to brute force attacks, exploits, and unauthorized access. Critical services (SSH, RDP, databases) can be compromised.",
                "impact": "Compromised instances, data breaches, ransomware, cryptomining, and complete account takeover if management ports are exposed.",
                "fix_code": '''# Restrict SSH to specific IP ranges only
ingress {
  description = "SSH from trusted IPs only"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["10.0.0.0/8"]
}''',
                "full_example": '''resource "aws_security_group" "restricted" {
  name        = "restricted-sg"
  description = "Security group with restricted access"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from anywhere (if needed)
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from anywhere"
  }

  # Allow SSH only from trusted network
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "SSH from internal network only"
  }

  # Allow all outbound traffic
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
}''',
                "best_practices": [
                    "Use VPC endpoints for AWS service access instead of NAT",
                    "Implement network ACLs as additional layer of defense",
                    "Use AWS Systems Manager Session Manager instead of SSH",
                    "Regularly audit security groups with AWS Config rules",
                ],
                "confidence": 0.95,
            }

        # IAM / permissions issues
        if "iam" in desc_lower or "permission" in desc_lower or "TF-IAM" in rule_id or "wildcard" in desc_lower:
            return {
                "summary": "IAM policy uses wildcard (*) permissions violating least privilege principle.",
                "risk": "Wildcard IAM permissions grant excessive access that can be exploited if credentials are compromised. Violates least privilege principle and compliance requirements.",
                "impact": "Compromised credentials with wildcard permissions can lead to complete account takeover, data exfiltration, resource destruction, and compliance audit failures.",
                "fix_code": '''# Use specific permissions instead of wildcards
resource "aws_iam_policy" "this" {
  name        = "app-policy"
  description = "Least privilege policy for application"

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
                "full_example": '''resource "aws_iam_role" "app" {
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

  tags = {
    Name        = "app-role"
    Environment = "production"
  }
}

resource "aws_iam_policy" "app" {
  name        = "app-policy"
  description = "Least privilege policy for application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Access"
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
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app.arn
}''',
                "best_practices": [
                    "Use AWS IAM Access Analyzer to identify unused permissions",
                    "Implement permission boundaries for developer roles",
                    "Use service control policies (SCPs) for guardrails",
                    "Regular access reviews with IAM Access Advisor",
                ],
                "confidence": 0.95,
            }

        # Default Terraform fix
        return {
            "summary": f"Terraform configuration issue detected: {title}",
            "risk": "This Terraform configuration may impact security, reliability, or compliance posture of your infrastructure.",
            "impact": "Potential security vulnerabilities, compliance violations, or operational issues in production environment.",
            "fix_code": f'''# Fix for {rule_id}
# Review and apply appropriate Terraform configuration changes

# Ensure all resources follow these best practices:
# 1. Use remote state backend with locking
# 2. Enable encryption for all storage resources
# 3. Apply least privilege IAM policies
# 4. Restrict security group rules
# 5. Add required tags for governance''',
            "full_example": f'''# Fixed Terraform configuration for {rule_id}
# File: {file_path if file_path else "example.tf"}

terraform {{
  required_version = ">= 1.5.0"
  
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}

  backend "s3" {{
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }}
}}

provider "aws" {{
  region = "us-east-1"
  
  default_tags {{
    tags = {{
      ManagedBy   = "terraform"
      Environment = "production"
      Owner       = "devops-team"
    }}
  }}
}}

# Add your fixed resource configuration here
# Ensure all security best practices are followed''',
            "best_practices": [
                "Run terraform validate before applying changes",
                "Review terraform plan output carefully",
                "Use workspaces for environment separation",
                "Enable AWS Config rules for continuous compliance",
            ],
            "confidence": 0.75,
        }

    def _generate_dockerfile_fix(
        self,
        rule_id: str,
        title: str,
        description: str,
        file_content: str
    ) -> dict[str, Any]:
        """Generate Dockerfile-specific fix."""
        desc_lower = description.lower()

        # Non-root user issues
        if "root" in desc_lower or ("user" in desc_lower and "non" in desc_lower) or "DKR-SEC-001" in rule_id or "DOCKER-001" in rule_id:
            return {
                "summary": "Docker container runs as root user, increasing security risk and potential for container escape attacks.",
                "risk": "Running containers as root user increases security risk. If vulnerabilities are exploited, attackers can potentially escape container isolation and compromise the host system.",
                "impact": "Container breakout exploits, host system compromise, privilege escalation attacks, and compliance violations (CIS Docker Benchmark).",
                "fix_code": '''# Create non-root user and group
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set proper ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Verify user
RUN whoami''',
                "full_example": '''FROM node:18.17.0-alpine3.18

# Install dependencies
RUN apk --no-cache add curl

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user and group
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set proper ownership of application files
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000

CMD ["node", "server.js"]''',
                "best_practices": [
                    "Use distroless or scratch base images for maximum security",
                    "Set readOnlyRootFilesystem in Kubernetes securityContext",
                    "Use Pod Security Standards to enforce non-root at cluster level",
                    "Regularly scan images for vulnerabilities with Trivy or Snyk",
                ],
                "confidence": 0.95,
            }

        # Health check issues
        if "health" in desc_lower or "healthcheck" in desc_lower or "DKR-REL-001" in rule_id or "DOCKER-004" in rule_id:
            return {
                "summary": "Docker container lacks HEALTHCHECK instruction, making it difficult for orchestrators to detect and restart unhealthy containers.",
                "risk": "Without health checks, container orchestrators (Kubernetes, ECS, Docker Swarm) cannot detect unhealthy containers, leading to service degradation and poor user experience.",
                "impact": "Undetected container failures, service outages, poor reliability, and increased mean time to recovery (MTTR).",
                "fix_code": '''# Add healthcheck for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1''',
                "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000

CMD ["node", "server.js"]''',
                "best_practices": [
                    "Use appropriate intervals based on application startup time",
                    "Implement meaningful health endpoints that check dependencies",
                    "Use separate readiness and liveness probes in Kubernetes",
                    "Consider using exec-based health checks for simpler applications",
                ],
                "confidence": 0.95,
            }

        # Latest tag issues
        if "latest" in desc_lower or "pin" in desc_lower or "version" in desc_lower or "DOCKER-002" in rule_id or "DOCKER-003" in rule_id:
            return {
                "summary": "Dockerfile uses 'latest' tag or unpinned base image version, making builds non-reproducible.",
                "risk": "Using 'latest' tag makes builds non-reproducible and may introduce unexpected breaking changes or security vulnerabilities when base image is updated.",
                "impact": "Build inconsistency across environments, potential production outages from unexpected base image changes, and difficulty debugging issues.",
                "fix_code": '''# Pin base image to specific version
FROM node:18.17.0-alpine3.18@sha256:abc123def456...

# Or at minimum use specific version tag
FROM node:18.17.0-alpine3.18''',
                "full_example": '''# Use specific base image version for reproducibility
FROM node:18.17.0-alpine3.18@sha256:abc123def456789...

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000

CMD ["node", "server.js"]''',
                "best_practices": [
                    "Use SHA256 digest for maximum reproducibility",
                    "Set up Dependabot or Renovate for base image updates",
                    "Pin all dependencies in package.json/requirements.txt",
                    "Use multi-stage builds to minimize attack surface",
                ],
                "confidence": 0.95,
            }

        # Multi-stage build issues
        if "multi" in desc_lower or "stage" in desc_lower or "DOCKER-005" in rule_id:
            return {
                "summary": "Dockerfile does not use multi-stage builds, resulting in larger image size and increased attack surface.",
                "risk": "Single-stage builds include build tools and dependencies in final image, increasing attack surface, image size, and deployment time.",
                "impact": "Larger images increase storage costs, deployment time, and security vulnerabilities from unnecessary packages.",
                "fix_code": '''# Use multi-stage build
FROM node:18.17.0-alpine3.18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18.17.0-alpine3.18
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/main.js"]''',
                "full_example": '''# Build stage
FROM node:18.17.0-alpine3.18 AS builder

WORKDIR /app

# Copy dependency files first for better caching
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM node:18.17.0-alpine3.18

# Install ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy built artifacts from builder stage
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000

CMD ["node", "dist/main.js"]''',
                "best_practices": [
                    "Use alpine or distroless base images for production stage",
                    "Copy only necessary artifacts from build stage",
                    "Minimize layers in production image",
                    "Scan final image with Trivy or Snyk before deployment",
                ],
                "confidence": 0.90,
            }

        # Default Dockerfile fix
        return {
            "summary": f"Dockerfile issue detected: {title}",
            "risk": "This Dockerfile configuration may impact security, reliability, or performance of containerized applications.",
            "impact": "Potential security vulnerabilities, container escape risks, or operational issues in production.",
            "fix_code": f'''# Fix for {rule_id}
# Apply Docker best practices:
# 1. Use specific base image versions
# 2. Run as non-root user
# 3. Add HEALTHCHECK instruction
# 4. Use multi-stage builds
# 5. Minimize layers and image size''',
            "full_example": f'''# Fixed Dockerfile for {rule_id}
# File: {file_path if file_path else "Dockerfile"}

FROM node:18.17.0-alpine3.18

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${{PORT:-3000}}/health || exit 1

EXPOSE 3000

CMD ["node", "server.js"]''',
            "best_practices": [
                "Regularly scan images for vulnerabilities",
                "Use .dockerignore to exclude unnecessary files",
                "Order instructions from least to most frequently changing",
                "Use multi-stage builds for compiled languages",
            ],
            "confidence": 0.75,
        }

    def _generate_kubernetes_fix(
        self,
        rule_id: str,
        title: str,
        description: str,
        file_content: str,
        file_path: str = ""
    ) -> dict[str, Any]:
        """Generate Kubernetes-specific fix."""
        desc_lower = description.lower()

        # Resource limits issues
        if "resource" in desc_lower or "limit" in desc_lower or "memory" in desc_lower or "cpu" in desc_lower or "K8S-001" in rule_id:
            return {
                "summary": "Kubernetes container lacks resource requests and limits, risking node stability and fair resource allocation.",
                "risk": "Containers without resource limits can consume all node resources, causing instability, affecting other workloads, and preventing proper scheduling by the Kubernetes scheduler.",
                "impact": "Node exhaustion, pod evictions, service outages, and inability to scale due to unknown resource requirements.",
                "fix_code": '''resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
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
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
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
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL''',
                "best_practices": [
                    "Use Vertical Pod Autoscaler to right-size resources",
                    "Set LimitRange defaults at namespace level",
                    "Monitor actual usage with Prometheus and adjust accordingly",
                    "Use ResourceQuota to prevent namespace resource exhaustion",
                ],
                "confidence": 0.95,
            }

        # Security context issues
        if "security" in desc_lower and ("context" in desc_lower or "root" in desc_lower) or "K8S-005" in rule_id or "K8S-006" in rule_id:
            return {
                "summary": "Kubernetes pod lacks securityContext configuration, running with default (potentially privileged) settings.",
                "risk": "Pods without securityContext may run as root, allow privilege escalation, and have unrestricted capabilities, increasing container escape risk.",
                "impact": "Container breakout exploits, host system compromise, privilege escalation attacks, and CIS benchmark violations.",
                "fix_code": '''securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
containers:
- name: app
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    runAsNonRoot: true
    runAsUser: 1000
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
        ports:
        - containerPort: 3000
        
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
        
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
      
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}''',
                "best_practices": [
                    "Use Pod Security Standards (restricted profile) at namespace level",
                    "Implement OPA Gatekeeper or Kyverno for policy enforcement",
                    "Use read-only root filesystem with emptyDir for temp files",
                    "Drop all capabilities and add only what's needed",
                ],
                "confidence": 0.95,
            }

        # Probe issues
        if "probe" in desc_lower or "liveness" in desc_lower or "readiness" in desc_lower or "K8S-003" in rule_id or "K8S-004" in rule_id:
            return {
                "summary": "Kubernetes container lacks liveness/readiness probes, preventing automatic health monitoring and traffic management.",
                "risk": "Without probes, Kubernetes cannot detect unhealthy containers or manage traffic routing properly, leading to service degradation and poor reliability.",
                "impact": "Undetected container failures, traffic sent to unhealthy pods, increased error rates, and poor user experience.",
                "fix_code": '''livenessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
readinessProbe:
  httpGet:
    path: /ready
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3''',
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
        - containerPort: 3000
        
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        
        # Liveness probe - detects deadlocks
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        # Readiness probe - controls traffic routing
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        
        # Startup probe for slow-starting containers
        startupProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 30''',
                "best_practices": [
                    "Use startupProbe for applications with variable startup time",
                    "Implement meaningful health endpoints that check dependencies",
                    "Set appropriate timeouts based on application response time",
                    "Use different endpoints for liveness and readiness checks",
                ],
                "confidence": 0.95,
            }

        # Default Kubernetes fix
        return {
            "summary": f"Kubernetes configuration issue detected: {title}",
            "risk": "This Kubernetes configuration may impact security, reliability, or scalability of workloads.",
            "impact": "Potential security vulnerabilities, service outages, or resource contention in production cluster.",
            "fix_code": f'''# Fix for {rule_id}
# Apply Kubernetes best practices:
# 1. Set resource requests and limits
# 2. Configure securityContext
# 3. Add liveness/readiness probes
# 4. Use network policies
# 5. Implement PodDisruptionBudget''',
            "full_example": f'''# Fixed Kubernetes manifest for {rule_id}
# File: {file_path if file_path else "deployment.yaml"}

apiVersion: apps/v1
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
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
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
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL''',
            "best_practices": [
                "Use PodDisruptionBudget for high availability",
                "Implement HorizontalPodAutoscaler for scaling",
                "Use NetworkPolicy for traffic isolation",
                "Apply ResourceQuota at namespace level",
            ],
            "confidence": 0.75,
        }

    def _generate_cicd_fix(
        self,
        rule_id: str,
        title: str,
        description: str,
        file_content: str
    ) -> dict[str, Any]:
        """Generate CI/CD-specific fix."""
        desc_lower = description.lower()

        # Security scanning issues
        if "security" in desc_lower or "scan" in desc_lower or "CI-002" in rule_id or "CI-SEC" in rule_id:
            return {
                "summary": "CI/CD pipeline lacks security scanning, risking deployment of vulnerable code to production.",
                "risk": "Pipeline without security scanning may deploy vulnerable code, exposed secrets, or malicious dependencies to production environments.",
                "impact": "Security breaches from vulnerable dependencies, exposed secrets in logs, supply chain attacks, and compliance violations.",
                "fix_code": '''- name: Run security scanning
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
  if: always()''',
                "full_example": '''name: Security and Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  security:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Initialize CodeQL
      uses: github/codeql-action/init@v3
      with:
        languages: javascript

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v3

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'

    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'
      if: always()

    - name: Check for secrets
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        GITLEAKS_LICENSE: ${{{{ secrets.GITLEAKS_LICENSE }}}}''',
                "best_practices": [
                    "Fail the pipeline on CRITICAL/HIGH severity findings",
                    "Use dependabot for automated dependency updates",
                    "Implement secret scanning with push protection",
                    "Add container image scanning for Docker builds",
                ],
                "confidence": 0.95,
            }

        # Secret exposure issues
        if "secret" in desc_lower or "credential" in desc_lower or "CI-004" in rule_id:
            return {
                "summary": "CI/CD pipeline may expose secrets in logs or environment variables.",
                "risk": "Secrets printed in logs or exposed in environment variables can be accessed by unauthorized users, leading to credential theft and unauthorized access.",
                "impact": "Credential exposure, unauthorized access to cloud resources, data breaches, and compliance violations.",
                "fix_code": '''# Use GitHub Secrets - NEVER hardcode secrets
env:
  AWS_ACCESS_KEY_ID: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
  AWS_SECRET_ACCESS_KEY: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}

# Use OIDC for AWS authentication (preferred)
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
    aws-region: us-east-1''',
                "full_example": '''name: Deploy to AWS

on:
  push:
    branches: [main]

permissions:
  id-token: write  # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    # Preferred: Use OIDC for AWS authentication
    - name: Configure AWS credentials via OIDC
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
        aws-region: us-east-1
        role-session-name: github-actions-session

    # Alternative: Use GitHub Secrets (if OIDC not available)
    # - name: Configure AWS credentials
    #   uses: aws-actions/configure-aws-credentials@v4
    #   with:
    #     aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
    #     aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
    #     aws-region: us-east-1

    - name: Deploy application
      run: |
        echo "Deploying application..."
        # Your deployment commands here
      env:
        # Use secrets, never hardcode
        DATABASE_URL: ${{{{ secrets.DATABASE_URL }}}}
        API_KEY: ${{{{ secrets.API_KEY }}}}''',
                "best_practices": [
                    "Use OIDC authentication instead of long-lived credentials",
                    "Enable secret scanning and push protection",
                    "Rotate secrets regularly and use short-lived credentials",
                    "Use environment-specific secrets for isolation",
                ],
                "confidence": 0.95,
            }

        # Default CI/CD fix
        return {
            "summary": f"CI/CD pipeline issue detected: {title}",
            "risk": "This CI/CD pipeline configuration may impact security, reliability, or deployment quality.",
            "impact": "Potential security vulnerabilities, deployment failures, or quality issues in production.",
            "fix_code": f'''# Fix for {rule_id}
# Apply CI/CD best practices:
# 1. Add security scanning steps
# 2. Use secrets management
# 3. Implement proper error handling
# 4. Add deployment approvals
# 5. Configure proper permissions''',
            "full_example": f'''# Fixed CI/CD pipeline for {rule_id}
# File: {file_path if file_path else ".github/workflows/ci.yml"}

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run tests
      run: npm test

  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
    - uses: actions/checkout@v4
    
    - name: Run security scans
      run: |
        echo "Add security scanning commands"

  deploy:
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy
      run: |
        echo "Deploy to production"''',
            "best_practices": [
                "Use environment protection rules for production",
                "Implement deployment approvals for critical environments",
                "Add rollback mechanisms for failed deployments",
                "Use branch protection rules for main branches",
            ],
            "confidence": 0.75,
        }

    def _get_default_fix(
        self,
        rule_id: str,
        title: str,
        description: str
    ) -> dict[str, Any]:
        """Generate default fallback fix."""
        return {
            "summary": f"Issue detected: {title}",
            "risk": "This configuration issue may impact security, reliability, or compliance posture.",
            "impact": "Potential security vulnerabilities, service disruptions, or compliance violations if not addressed.",
            "fix_code": f"# Fix for {rule_id}\n# Review the recommendation and apply appropriate changes",
            "full_example": f"# Fixed configuration for {rule_id}\n# Apply best practices based on the technology and issue type",
            "best_practices": [
                "Review the issue description and recommendation carefully",
                "Apply fixes in a staging environment first",
                "Test thoroughly before deploying to production",
                "Monitor for any unexpected behavior after changes",
            ],
            "confidence": 0.50,
        }


# Singleton instance
_fix_generator: AIFixGenerator | None = None


def get_fix_generator() -> AIFixGenerator:
    """Get or create AI fix generator instance."""
    global _fix_generator
    if _fix_generator is None:
        _fix_generator = AIFixGenerator()
    return _fix_generator


async def generate_fix_for_finding(finding: dict[str, Any], file_content: str = "") -> dict[str, Any]:
    """Generate AI fix for a finding."""
    generator = get_fix_generator()
    return await generator.generate_fix(finding, file_content)
