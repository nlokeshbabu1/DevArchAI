"""
Azure Terraform Security Scanner

Scans Azure Terraform configurations for security issues.
Implements rules from docs/rules/azu_helm.md
"""


from app.rules.base import RuleFinding, Severity


class AzureScanner:
    """
    Scanner for Azure Terraform resources.
    
    Detects security misconfigurations in:
    - Storage accounts
    - Network security groups
    - SQL servers
    - Key Vaults
    - IAM/Role assignments
    - App Services
    """

    def __init__(self):
        self.findings: list[RuleFinding] = []
        self.files_scanned: list[str] = []

    def scan(self, parsed_files: list) -> list[RuleFinding]:
        """
        Scan parsed Terraform files for Azure security issues.
        
        Args:
            parsed_files: List of ParsedFile objects with terraform resources
            
        Returns:
            List of security findings
        """
        self.findings = []

        for parsed_file in parsed_files:
            # Access ParsedFile attributes directly (it's a dataclass, not dict)
            if parsed_file.file_type != "terraform":
                continue

            self.files_scanned.append(parsed_file.file_path)
            resources = parsed_file.parsed_data.get("resources", [])

            for resource in resources:
                resource_type = resource.get("type", "")

                # Route to appropriate scanner based on resource type
                if resource_type == "azurerm_storage_account":
                    self._check_storage_account(resource, parsed_file.file_path)
                elif resource_type == "azurerm_network_security_group":
                    self._check_nsg(resource, parsed_file.file_path)
                elif resource_type == "azurerm_sql_firewall_rule":
                    self._check_sql_firewall(resource, parsed_file.file_path)
                elif resource_type == "azurerm_role_assignment":
                    self._check_rbac(resource, parsed_file.file_path)
                elif resource_type == "azurerm_app_service":
                    self._check_app_service(resource, parsed_file.file_path)
                elif resource_type == "azurerm_key_vault":
                    self._check_key_vault(resource, parsed_file.file_path)

        return self.findings

    def _check_storage_account(self, resource: dict, file_path: str) -> None:
        """Check Azure storage account security."""
        resource_name = resource.get("name", "unknown")
        properties = resource.get("properties", {})

        # AZ-STORAGE-001: Public blob access
        allow_blob_public = properties.get("allow_blob_public_access", False)
        if allow_blob_public:
            self.findings.append(RuleFinding(
                rule_id="AZ-STORAGE-001",
                rule_name="Storage Account Public Access",
                severity=Severity.CRITICAL,
                category="security",
                description=f"Storage account '{resource_name}' allows public blob access",
                recommendation="Set allow_blob_public_access = false",
                file_path=file_path,
                resource_name=resource_name,
                confidence=0.95,
            ))

        # AZ-STORAGE-002: Network rules
        network_rules = properties.get("network_rules", {})
        default_action = network_rules.get("default_action", "Allow")
        if default_action == "Allow":
            self.findings.append(RuleFinding(
                rule_id="AZ-STORAGE-002",
                rule_name="Storage Account Network Rules",
                severity=Severity.HIGH,
                category="security",
                description=f"Storage account '{resource_name}' has permissive network rules",
                recommendation="Set network_rules.default_action = 'Deny'",
                file_path=file_path,
                resource_name=resource_name,
                confidence=0.9,
            ))

    def _check_nsg(self, resource: dict, file_path: str) -> None:
        """Check Network Security Group configuration."""
        resource_name = resource.get("name", "unknown")
        properties = resource.get("properties", {})

        security_rules = properties.get("security_rules", [])

        # AZ-NETWORK-001: Missing security rules
        if not security_rules:
            self.findings.append(RuleFinding(
                rule_id="AZ-NETWORK-001",
                rule_name="NSG Missing Security Rules",
                severity=Severity.HIGH,
                category="security",
                description=f"Network Security Group '{resource_name}' has no security rules defined",
                recommendation="Define explicit security rules with least privilege access",
                file_path=file_path,
                resource_name=resource_name,
                confidence=0.95,
            ))

    def _check_sql_firewall(self, resource: dict, file_path: str) -> None:
        """Check SQL Server firewall configuration."""
        resource_name = resource.get("name", "unknown")
        properties = resource.get("properties", {})

        # AZ-NETWORK-002: Open firewall
        start_ip = properties.get("start_ip_address", "")
        end_ip = properties.get("end_ip_address", "")

        if start_ip == "0.0.0.0" and end_ip == "255.255.255.255":
            self.findings.append(RuleFinding(
                rule_id="AZ-NETWORK-002",
                rule_name="SQL Server Firewall Open to Internet",
                severity=Severity.CRITICAL,
                category="security",
                description=f"SQL Server firewall rule '{resource_name}' allows access from any IP",
                recommendation="Restrict firewall rules to specific IP ranges",
                file_path=file_path,
                resource_name=resource_name,
                confidence=1.0,
            ))

    def _check_rbac(self, resource: dict, file_path: str) -> None:
        """Check RBAC role assignments."""
        resource_name = resource.get("name", "unknown")
        properties = resource.get("properties", {})

        # AZ-IAM-001: Overly permissive RBAC
        role_name = properties.get("role_definition_name", "")
        scope = properties.get("scope", "")

        if role_name == "Contributor" and "/subscriptions/" in scope and "/resourceGroups/" not in scope:
            self.findings.append(RuleFinding(
                rule_id="AZ-IAM-001",
                rule_name="Overly Permissive RBAC Assignment",
                severity=Severity.HIGH,
                category="security",
                description=f"Role assignment '{resource_name}' grants Contributor at subscription scope",
                recommendation="Use least privilege scope (resource group or resource level)",
                file_path=file_path,
                resource_name=resource_name,
                confidence=0.9,
            ))

    def _check_app_service(self, resource: dict, file_path: str) -> None:
        """Check App Service configuration."""
        resource_name = resource.get("name", "unknown")
        properties = resource.get("properties", {})

        # AZ-IAM-002: Missing managed identity
        identity = properties.get("identity", {})
        if not identity:
            self.findings.append(RuleFinding(
                rule_id="AZ-IAM-002",
                rule_name="App Service Missing Managed Identity",
                severity=Severity.MEDIUM,
                category="security",
                description=f"App Service '{resource_name}' does not have managed identity enabled",
                recommendation="Enable system-assigned managed identity",
                file_path=file_path,
                resource_name=resource_name,
                confidence=0.85,
            ))

    def _check_key_vault(self, resource: dict, file_path: str) -> None:
        """Check Key Vault configuration."""
        resource_name = resource.get("name", "unknown")
        properties = resource.get("properties", {})

        # AZ-KEYVAULT-001: Public access
        network_acls = properties.get("network_acls", {})
        default_action = network_acls.get("default_action", "Allow")

        if default_action == "Allow":
            self.findings.append(RuleFinding(
                rule_id="AZ-KEYVAULT-001",
                rule_name="Key Vault Public Access",
                severity=Severity.CRITICAL,
                category="security",
                description=f"Key Vault '{resource_name}' is accessible from public internet",
                recommendation="Set network_acls.default_action = 'Deny'",
                file_path=file_path,
                resource_name=resource_name,
                confidence=0.95,
            ))
