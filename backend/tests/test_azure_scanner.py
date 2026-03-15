"""
Tests for Azure Terraform Scanner
"""

import pytest

from app.rules.base import Severity
from app.scanners.azure_scanner import AzureScanner


class TestAzureScanner:
    """Test Azure security scanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = AzureScanner()
    
    def test_storage_public_access(self):
        """Test AZ-STORAGE-001: Storage account public access."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "storage.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_storage_account",
                            "name": "storage_account1",
                            "properties": {
                                "allow_blob_public_access": True,
                            },
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "AZ-STORAGE-001" for f in findings)
        storage_finding = next(f for f in findings if f.rule_id == "AZ-STORAGE-001")
        assert storage_finding.severity == Severity.CRITICAL
        assert "public" in storage_finding.description.lower()
    
    def test_storage_network_rules(self):
        """Test AZ-STORAGE-002: Storage network rules."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "storage.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_storage_account",
                            "name": "storage_account1",
                            "properties": {
                                "allow_blob_public_access": False,  # Secure
                                "network_rules": {
                                    "default_action": "Allow",
                                },
                            },
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) == 1
        assert findings[0].rule_id == "AZ-STORAGE-002"
        assert findings[0].severity == Severity.HIGH
    
    def test_sql_firewall_open(self):
        """Test AZ-NETWORK-002: SQL firewall open to internet."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "sql.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_sql_firewall_rule",
                            "name": "allow_all",
                            "properties": {
                                "start_ip_address": "0.0.0.0",
                                "end_ip_address": "255.255.255.255",
                            },
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) == 1
        assert findings[0].rule_id == "AZ-NETWORK-002"
        assert findings[0].severity == Severity.CRITICAL
        assert "firewall" in findings[0].description.lower()
    
    def test_key_vault_public_access(self):
        """Test AZ-KEYVAULT-001: Key Vault public access."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "keyvault.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_key_vault",
                            "name": "example_kv",
                            "properties": {
                                "network_acls": {
                                    "default_action": "Allow",
                                },
                            },
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) == 1
        assert findings[0].rule_id == "AZ-KEYVAULT-001"
        assert findings[0].severity == Severity.CRITICAL
    
    def test_overly_permissive_rbac(self):
        """Test AZ-IAM-001: Overly permissive RBAC."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "rbac.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_role_assignment",
                            "name": "contributor_assignment",
                            "properties": {
                                "role_definition_name": "Contributor",
                                "scope": "/subscriptions/12345678-1234-1234-1234-123456789012",
                            },
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) == 1
        assert findings[0].rule_id == "AZ-IAM-001"
        assert findings[0].severity == Severity.HIGH
    
    def test_nsg_missing_rules(self):
        """Test AZ-NETWORK-001: NSG missing security rules."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "nsg.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_network_security_group",
                            "name": "example_nsg",
                            "properties": {
                                "security_rules": [],
                            },
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) == 1
        assert findings[0].rule_id == "AZ-NETWORK-001"
        assert findings[0].severity == Severity.HIGH
    
    def test_app_service_missing_identity(self):
        """Test AZ-IAM-002: App Service missing managed identity."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "appservice.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_app_service",
                            "name": "example_app",
                            "properties": {},
                        }
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        assert len(findings) == 1
        assert findings[0].rule_id == "AZ-IAM-002"
        assert findings[0].severity == Severity.MEDIUM
    
    def test_secure_configuration(self):
        """Test that secure configurations pass."""
        parsed_files = [
            {
                "file_type": "terraform",
                "file_path": "secure.tf",
                "parsed_data": {
                    "resources": [
                        {
                            "type": "azurerm_storage_account",
                            "name": "secure_storage",
                            "properties": {
                                "allow_blob_public_access": False,
                                "network_rules": {
                                    "default_action": "Deny",
                                },
                            },
                        },
                        {
                            "type": "azurerm_key_vault",
                            "name": "secure_kv",
                            "properties": {
                                "network_acls": {
                                    "default_action": "Deny",
                                },
                            },
                        },
                    ]
                },
            }
        ]
        
        findings = self.scanner.scan(parsed_files)
        
        # Should have no findings for secure resources
        assert len(findings) == 0
