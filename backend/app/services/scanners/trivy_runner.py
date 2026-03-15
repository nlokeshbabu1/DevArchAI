"""Trivy vulnerability scanner integration."""

import asyncio
import json

import structlog

from app.engines.scanner_engine import BaseScanner, ScannerFinding, ScannerSeverity

logger = structlog.get_logger(__name__)


class TrivyScanner(BaseScanner):
    """Trivy vulnerability scanner for containers and filesystems."""

    @property
    def scanner_id(self) -> str:
        return "trivy"

    @property
    def scanner_name(self) -> str:
        return "Trivy"

    @property
    def supported_file_types(self) -> list[str]:
        return [".tf", ".yaml", ".yml", "Dockerfile", "docker-compose.yml", "package.json", "requirements.txt"]

    async def check_availability(self) -> bool:
        """Check if Trivy is installed."""
        try:
            result = await asyncio.create_subprocess_exec(
                "trivy",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("Trivy not found in PATH")
            return False

    async def scan(
        self,
        repo_path: str,
        file_paths: list[str],
        timeout_seconds: int = 300,
    ) -> list[ScannerFinding]:
        """
        Run Trivy scan against repository.

        Args:
            repo_path: Path to repository
            file_paths: Files to scan
            timeout_seconds: Scan timeout

        Returns:
            List of findings
        """
        findings = []

        try:
            # Run Trivy filesystem scan
            cmd = [
                "trivy",
                "fs",
                "--format",
                "json",
                "--security-checks",
                "vuln,config,secret",
                "--severity",
                "CRITICAL,HIGH,MEDIUM,LOW",
                repo_path,
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

            if process.returncode not in (0, 1):  # 1 means findings found
                logger.error(
                    "Trivy scan failed",
                    returncode=process.returncode,
                    stderr=stderr.decode(),
                )
                return findings

            # Parse JSON output
            output = stdout.decode()
            findings = self.parse_output(output)

            logger.info(
                "Trivy scan completed",
                findings_count=len(findings),
                repo_path=repo_path,
            )

        except asyncio.TimeoutError:
            logger.error("Trivy scan timed out", timeout=timeout_seconds)
        except Exception as e:
            logger.exception("Trivy scan failed", error=str(e))

        return findings

    def parse_output(self, raw_output: str) -> list[ScannerFinding]:
        """Parse Trivy JSON output into unified findings."""
        findings = []

        try:
            data = json.loads(raw_output)
            results = data.get("Results", [])

            for result in results:
                file_path = result.get("Target", "unknown")
                vulnerabilities = result.get("Vulnerabilities", [])
                misconfigurations = result.get("Misconfigurations", [])
                secrets = result.get("Secrets", [])

                # Parse vulnerabilities
                for vuln in vulnerabilities:
                    findings.append(
                        ScannerFinding(
                            scanner_id=self.scanner_id,
                            rule_id=vuln.get("VulnerabilityID", "UNKNOWN"),
                            rule_name=f"Vulnerability: {vuln.get('PkgName', 'unknown')}",
                            severity=self._map_severity(vuln.get("Severity", "UNKNOWN")),
                            category="security",
                            description=vuln.get("Description", "No description"),
                            recommendation=f"Upgrade to {vuln.get('FixedVersion', 'latest version')}",
                            file_path=file_path,
                            cve_id=vuln.get("VulnerabilityID"),
                            cvss_score=vuln.get("CVSS", {}).get("nvd", {}).get("V3Score"),
                            raw_data=vuln,
                        )
                    )

                # Parse misconfigurations
                for misconfig in misconfigurations:
                    for finding_data in misconfig.get("CauseMetadata", {}).get("Occurrences", []):
                        findings.append(
                            ScannerFinding(
                                scanner_id=self.scanner_id,
                                rule_id=misconfig.get("ID", "UNKNOWN"),
                                rule_name=misconfig.get("Title", "Misconfiguration"),
                                severity=self._map_severity(misconfig.get("Severity", "UNKNOWN")),
                                category="security",
                                description=misconfig.get("Message", "Configuration issue detected"),
                                recommendation=misconfig.get("Resolution", "Fix the configuration"),
                                file_path=file_path,
                                line_number=finding_data.get("StartLine"),
                                raw_data=misconfig,
                            )
                        )

                # Parse secrets
                for secret in secrets:
                    findings.append(
                        ScannerFinding(
                            scanner_id=self.scanner_id,
                            rule_id="SECRET_DETECTED",
                            rule_name=f"Secret Detected: {secret.get('RuleID', 'unknown')}",
                            severity=ScannerSeverity.CRITICAL,
                            category="security",
                            description=f"Potential secret found: {secret.get('Match', '***')}",
                            recommendation="Remove secret from code and use secrets management",
                            file_path=file_path,
                            line_number=secret.get("StartLine"),
                            raw_data=secret,
                        )
                    )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Trivy output", error=str(e))
        except Exception as e:
            logger.exception("Error parsing Trivy results", error=str(e))

        return findings

    def _map_severity(self, severity: str) -> ScannerSeverity:
        """Map Trivy severity to internal severity."""
        severity_map = {
            "CRITICAL": ScannerSeverity.CRITICAL,
            "HIGH": ScannerSeverity.HIGH,
            "MEDIUM": ScannerSeverity.MEDIUM,
            "LOW": ScannerSeverity.LOW,
            "UNKNOWN": ScannerSeverity.INFO,
        }
        return severity_map.get(severity.upper(), ScannerSeverity.INFO)
