"""
Terraform File Parser
"""

import json
import re
from pathlib import Path
from typing import Any

from app.parsers.base import BaseParser, ParsedFile


class TerraformParser(BaseParser):
    """Parser for Terraform configuration files (.tf, .tf.json)."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".tf", ".tf.json"]
        self.tfvars_extensions = [".tfvars", ".tfvars.json"]

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        suffix = file_path.suffix.lower()
        return suffix in self.supported_extensions or suffix in self.tfvars_extensions

    def parse(self, file_path: Path, content: str) -> ParsedFile:
        """Parse Terraform file and extract resources."""
        suffix = file_path.suffix.lower()

        # Handle tfvars files differently - they don't have resources/backends
        if suffix in self.tfvars_extensions:
            return self._parse_tfvars(file_path, content)

        parse_errors = []
        parsed_data = {
            "resources": [],
            "data_sources": [],
            "modules": [],
            "variables": [],
            "outputs": [],
            "providers": [],
            "backends": [],
            "terraform_blocks": [],
        }

        try:
            if suffix == ".tf.json":
                # JSON format
                parsed_data = self._parse_json_terraform(json.loads(content))
            else:
                # HCL format - use regex-based parsing
                parsed_data = self._parse_hcl_terraform(content)
        except Exception as e:
            parse_errors.append(str(e))

        return ParsedFile(
            file_path=str(file_path),
            file_type="terraform",
            raw_content=content,
            parsed_data=parsed_data,
            line_count=len(content.splitlines()),
            parse_errors=parse_errors,
        )

    def _parse_tfvars(self, file_path: Path, content: str) -> ParsedFile:
        """Parse .tfvars files - these only contain variable values."""
        # tfvars files don't have resources, backends, or providers
        # They only contain variable assignments
        parsed_data = {
            "resources": [],
            "data_sources": [],
            "modules": [],
            "variables": [],
            "outputs": [],
            "providers": [],
            "backends": [],
            "terraform_blocks": [],
            "is_tfvars": True,
            "variable_names": self._extract_tfvars_names(content),
        }

        return ParsedFile(
            file_path=str(file_path),
            file_type="terraform_vars",  # Different file type for filtering
            raw_content=content,
            parsed_data=parsed_data,
            line_count=len(content.splitlines()),
            parse_errors=[],
        )

    def _extract_tfvars_names(self, content: str) -> list[str]:
        """Extract variable names from tfvars content."""
        names = []
        # Match variable = value patterns
        pattern = r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        for match in re.finditer(pattern, content, re.MULTILINE):
            names.append(match.group(1))
        return names

    def _parse_hcl_terraform(self, content: str) -> dict[str, Any]:
        """Parse HCL Terraform content using regex patterns."""
        result = {
            "resources": [],
            "data_sources": [],
            "modules": [],
            "variables": [],
            "outputs": [],
            "providers": [],
            "backends": [],
            "terraform_blocks": [],
        }

        # Extract terraform blocks (for metadata)
        terraform_block_pattern = r'terraform\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(terraform_block_pattern, content, re.DOTALL):
            block_content = match.group(1)
            result["terraform_blocks"].append({
                "raw_content": block_content,
            })

        # Extract backend blocks directly from content (both inside and outside terraform blocks)
        # This pattern handles nested braces correctly
        backend_pattern = r'backend\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(backend_pattern, content, re.DOTALL):
            backend_type = match.group(1)
            backend_body = match.group(2)

            # Check for locking mechanisms
            has_locking = self._check_backend_locking(backend_type, backend_body)
            
            # Check for encryption
            has_encryption = "encrypt" in backend_body.lower() and "= true" in backend_body.lower()

            # Check if already added (avoid duplicates)
            already_exists = any(
                b["type"] == backend_type and b["raw_config"].strip() == backend_body.strip()
                for b in result["backends"]
            )

            if not already_exists:
                result["backends"].append({
                    "type": backend_type,
                    "has_locking": has_locking,
                    "has_encryption": has_encryption,
                    "has_remote_state": self._is_remote_backend(backend_type),
                    "raw_config": backend_body,
                })

        # Extract resource blocks
        resource_pattern = r'resource\s+"(\w+)"\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(resource_pattern, content, re.DOTALL):
            resource_type = match.group(1)
            resource_name = match.group(2)
            resource_body = match.group(3)

            resource_data = {
                "type": resource_type,
                "name": resource_name,
                "raw_body": resource_body,
                "has_lifecycle": "lifecycle" in resource_body,
                "has_tags": "tags" in resource_body or "Tags" in resource_body,
            }

            # Extract specific resource properties
            if resource_type == "aws_s3_bucket":
                resource_data["versioning"] = "versioning" in resource_body
                resource_data["encryption"] = "server_side_encryption" in resource_body or "sse" in resource_body.lower()
            elif resource_type == "aws_security_group":
                resource_data["ingress_rules"] = resource_body.count("ingress")
                resource_data["egress_rules"] = resource_body.count("egress")
            elif resource_type == "aws_db_instance":
                resource_data["multi_az"] = "multi_az" in resource_body
                resource_data["backup_retention"] = "backup_retention_period" in resource_body

            result["resources"].append(resource_data)

        # Extract provider configurations
        provider_pattern = r'provider\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(provider_pattern, content, re.DOTALL):
            result["providers"].append({
                "name": match.group(1),
                "raw_config": match.group(2),
            })

        # Extract variables
        var_pattern = r'variable\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(var_pattern, content, re.DOTALL):
            result["variables"].append({
                "name": match.group(1),
                "raw_config": match.group(2),
            })

        # Extract outputs
        output_pattern = r'output\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(output_pattern, content, re.DOTALL):
            result["outputs"].append({
                "name": match.group(1),
                "raw_config": match.group(2),
            })

        # Extract modules
        module_pattern = r'module\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(module_pattern, content, re.DOTALL):
            result["modules"].append({
                "name": match.group(1),
                "source": self._extract_source(match.group(2)),
            })

        return result

    def _is_remote_backend(self, backend_type: str) -> bool:
        """Check if backend type supports remote state."""
        remote_backends = {"s3", "gcs", "azurerm", "consul", "remote", "http", "pg", "etcdv3", "oss", "cos"}
        return backend_type.lower() in remote_backends

    def _check_backend_locking(self, backend_type: str, backend_body: str) -> bool:
        """Check if backend has locking configured."""
        backend_type = backend_type.lower()

        # Remove comments from backend body for accurate checking
        backend_body_no_comments = re.sub(r'#.*$', '', backend_body, flags=re.MULTILINE)

        # S3 backend: check for dynamodb_table or use_lockfile (Terraform 1.10+)
        if backend_type == "s3":
            # Check for DynamoDB table (traditional approach for team/CI environments)
            has_dynamodb = "dynamodb_table" in backend_body_no_comments
            # Check for use_lockfile = true (Terraform 1.10+ built-in file-based locking)
            has_use_lockfile = "use_lockfile" in backend_body_no_comments and "use_lockfile = true" in backend_body_no_comments
            return has_dynamodb or has_use_lockfile

        # GCS backend: has built-in locking
        if backend_type == "gcs":
            return True

        # Azure backend: has built-in locking
        if backend_type == "azurerm":
            return True

        # Consul backend: has built-in locking
        if backend_type == "consul":
            return True

        # Remote backend (Terraform Cloud): has built-in locking
        if backend_type == "remote":
            return True

        # HTTP backend: no locking
        if backend_type == "http":
            return False

        # PostgreSQL backend: has built-in locking
        if backend_type == "pg":
            return True

        # Default: check for common locking patterns
        return "lock" in backend_body_no_comments.lower() or "dynamodb" in backend_body_no_comments.lower()

    def _parse_json_terraform(self, data: dict) -> dict[str, Any]:
        """Parse JSON-formatted Terraform."""
        result = {
            "resources": [],
            "data_sources": [],
            "modules": [],
            "variables": [],
            "outputs": [],
            "providers": [],
            "backends": [],
            "terraform_blocks": [],
        }

        if "resource" in data:
            for resource_type, resources in data["resource"].items():
                for name, config in resources.items():
                    result["resources"].append({
                        "type": resource_type,
                        "name": name,
                        "config": config,
                    })

        if "backend" in data.get("terraform", {}):
            backend = data["terraform"]["backend"]
            for backend_type, config in backend.items():
                has_locking = self._check_backend_locking(backend_type, str(config))
                result["backends"].append({
                    "type": backend_type,
                    "has_locking": has_locking,
                    "has_remote_state": self._is_remote_backend(backend_type),
                    "config": config,
                })

        return result

    def _extract_source(self, body: str) -> str:
        """Extract module source from body."""
        match = re.search(r'source\s*=\s*"([^"]+)"', body)
        return match.group(1) if match else ""

    def extract_resources(self, parsed_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract resources for rule evaluation."""
        resources = []

        # Skip tfvars files - they don't have resources/backends
        if parsed_data.get("is_tfvars"):
            return resources

        for resource in parsed_data.get("resources", []):
            resources.append({
                "file_type": "terraform",
                "resource_type": resource.get("type"),
                "resource_name": resource.get("name"),
                "properties": resource,
            })

        for backend in parsed_data.get("backends", []):
            resources.append({
                "file_type": "terraform",
                "resource_type": "backend",
                "properties": backend,
            })

        return resources
