"""Checkov infrastructure-as-code scanner integration."""

import asyncio
import json

import structlog

from app.engines.scanner_engine import BaseScanner, ScannerFinding, ScannerSeverity

logger = structlog.get_logger(__name__)


class CheckovScanner(BaseScanner):
    """Checkov scanner for infrastructure-as-code security and compliance."""

    @property
    def scanner_id(self) -> str:
        return "checkov"

    @property
    def scanner_name(self) -> str:
        return "Checkov"

    @property
    def supported_file_types(self) -> list[str]:
        return [".tf", ".tf.json", ".yaml", ".yml", "Dockerfile", "docker-compose.yml", "template.yaml"]

    async def check_availability(self) -> bool:
        """Check if Checkov is installed."""
        try:
            result = await asyncio.create_subprocess_exec(
                "checkov",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("Checkov not found in PATH")
            return False

    async def scan(
        self,
        repo_path: str,
        file_paths: list[str],
        timeout_seconds: int = 300,
    ) -> list[ScannerFinding]:
        """
        Run Checkov scan against repository.

        Args:
            repo_path: Path to repository
            file_paths: Files to scan
            timeout_seconds: Scan timeout

        Returns:
            List of findings
        """
        findings = []

        try:
            # Run Checkov scan
            cmd = [
                "checkov",
                "--directory",
                repo_path,
                "--output",
                "json",
                "--compact",
                "--check",
                "CKV_AWS,CKV_K8S,CKV_DOCKER,CKV_TF,CKV_GHA",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )

            # Checkov returns 1 if findings found, 0 if clean
            if process.returncode not in (0, 1):
                logger.error(
                    "Checkov scan failed",
                    returncode=process.returncode,
                    stderr=stderr.decode(),
                )
                return findings

            # Parse JSON output
            output = stdout.decode()
            findings = self.parse_output(output)

            logger.info(
                "Checkov scan completed",
                findings_count=len(findings),
                repo_path=repo_path,
            )

        except asyncio.TimeoutError:
            logger.error("Checkov scan timed out", timeout=timeout_seconds)
        except Exception as e:
            logger.exception("Checkov scan failed", error=str(e))

        return findings

    def parse_output(self, raw_output: str) -> list[ScannerFinding]:
        """Parse Checkov JSON output into unified findings."""
        findings = []

        try:
            data = json.loads(raw_output)

            # Parse failed checks
            failed_checks = data.get("failed_checks", [])

            for check in failed_checks:
                check_id = check.get("check_id", "UNKNOWN")
                severity = check.get("severity", "MEDIUM")

                findings.append(
                    ScannerFinding(
                        scanner_id=self.scanner_id,
                        rule_id=check_id,
                        rule_name=check.get("check_name", "Check Failed"),
                        severity=self._map_severity(severity),
                        category=self._map_category(check_id),
                        description=check.get("guideline", "Security or compliance check failed"),
                        recommendation=check.get("recommendation", "Review and fix the configuration"),
                        file_path=check.get("file_path", "unknown"),
                        line_number=check.get("file_line_range", [None])[0] if check.get("file_line_range") else None,
                        resource_name=check.get("resource", ""),
                        raw_data=check,
                    )
                )

            # Parse secret findings
            secrets = data.get("secrets", [])
            for secret in secrets:
                findings.append(
                    ScannerFinding(
                        scanner_id=self.scanner_id,
                        rule_id="CKV_SECRET",
                        rule_name="Secret Detected",
                        severity=ScannerSeverity.CRITICAL,
                        category="security",
                        description=f"Potential secret found in {secret.get('file_path', 'unknown')}",
                        recommendation="Remove secret from code and use secrets management",
                        file_path=secret.get("file_path", "unknown"),
                        line_number=secret.get("line", 0),
                        raw_data=secret,
                    )
                )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Checkov output", error=str(e))
        except Exception as e:
            logger.exception("Error parsing Checkov results", error=str(e))

        return findings

    def _map_severity(self, severity: str) -> ScannerSeverity:
        """Map Checkov severity to internal severity."""
        severity_map = {
            "CRITICAL": ScannerSeverity.CRITICAL,
            "HIGH": ScannerSeverity.HIGH,
            "MEDIUM": ScannerSeverity.MEDIUM,
            "LOW": ScannerSeverity.LOW,
            "INFO": ScannerSeverity.INFO,
        }
        return severity_map.get(severity.upper(), ScannerSeverity.MEDIUM)

    def _map_category(self, check_id: str) -> str:
        """Map Checkov check ID to category."""
        if check_id.startswith("CKV_AWS"):
            return "security"
        elif check_id.startswith("CKV_K8S"):
            return "reliability"
        elif check_id.startswith("CKV_DOCKER"):
            return "security"
        elif check_id.startswith("CKV_TF"):
            return "reliability"
        elif check_id.startswith("CKV_GHA"):
            return "security"
        return "security"
