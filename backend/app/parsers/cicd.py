"""
CI/CD Pipeline Parser - Production-grade support for all major CI/CD platforms.

Supports:
- GitHub Actions
- GitLab CI
- Jenkins (Declarative & Scripted)
- CircleCI
- Azure DevOps
- Travis CI
- Drone CI
"""

import re
from pathlib import Path
from typing import Any

import yaml

from app.parsers.base import BaseParser, ParsedFile


class CICDParser(BaseParser):
    """Parser for CI/CD pipeline configurations."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".yaml", ".yml"]
        self.ci_patterns = [
            ".github/workflows/",
            ".gitlab-ci.yml",
            ".gitlab-ci.yaml",
            ".circleci/config.yml",
            ".circleci/config.yaml",
            ".travis.yml",
            ".travis.yaml",
            "azure-pipelines.yml",
            "azure-pipelines.yaml",
            ".drone.yml",
            ".drone.yaml",
        ]
        # Files to explicitly ignore (documentation, etc.)
        self.ignored_filenames = {"README.md", "README.yaml", "README.yml", "example.yml", "example.yaml"}

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a CI/CD configuration."""
        path_str = str(file_path).lower()
        file_name = file_path.name.lower()

        # Ignore documentation files even in CI/CD directories
        if file_name in self.ignored_filenames:
            return False

        # Jenkinsfile (no extension)
        if file_path.name == "Jenkinsfile":
            return True

        # Must be YAML/YML file for other CI/CD types
        if file_path.suffix.lower() not in self.supported_extensions:
            return False

        # Check for CI/CD specific paths and filenames
        for pattern in self.ci_patterns:
            if pattern in path_str:
                return True

        return False

    def parse(self, file_path: Path, content: str) -> ParsedFile:
        """Parse CI/CD configuration file."""
        parse_errors = []
        parsed_data = {
            "ci_type": self._detect_ci_type(file_path),
            "jobs": [],
            "stages": [],
            "triggers": [],
            "environments": [],
            "secrets_usage": [],
            "artifacts": [],
            "caching": [],
            "security_features": {},
        }

        try:
            if file_path.name == "Jenkinsfile":
                parsed_data = self._parse_jenkinsfile(content)
            else:
                # YAML-based CI/CD
                docs = list(yaml.safe_load_all(content))
                for doc in docs:
                    if doc and isinstance(doc, dict):
                        parsed_data = self._parse_yaml_cicd(doc, parsed_data, file_path)

        except yaml.YAMLError as e:
            parse_errors.append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            parse_errors.append(str(e))

        return ParsedFile(
            file_path=str(file_path),
            file_type="cicd",
            raw_content=content,
            parsed_data=parsed_data,
            line_count=len(content.splitlines()),
            parse_errors=parse_errors,
        )

    def _detect_ci_type(self, file_path: Path) -> str:
        """Detect CI/CD platform type."""
        path_str = str(file_path)
        file_name = file_path.name.lower()

        if ".github/workflows" in path_str:
            return "github_actions"
        elif ".gitlab-ci" in path_str:
            return "gitlab_ci"
        elif ".circleci" in path_str:
            return "circleci"
        elif ".travis" in path_str:
            return "travis"
        elif "azure-pipelines" in path_str or file_name == "azure-pipelines.yml":
            return "azure_devops"
        elif file_path.name == "Jenkinsfile":
            return "jenkins"
        elif ".drone" in path_str:
            return "drone"

        return "unknown"

    def _parse_yaml_cicd(self, doc: dict, parsed_data: dict) -> dict:
        """Parse YAML-based CI/CD configuration."""
        ci_type = parsed_data.get("ci_type", "unknown")

        if ci_type == "github_actions":
            return self._parse_github_actions(doc, parsed_data)
        elif ci_type == "gitlab_ci":
            return self._parse_gitlab_ci(doc, parsed_data)
        elif ci_type == "circleci":
            return self._parse_circleci(doc, parsed_data)
        elif ci_type == "azure_devops":
            return self._parse_azure_devops(doc, parsed_data)

        # Generic YAML parsing
        return self._parse_generic_cicd(doc, parsed_data)

    def _parse_github_actions(self, doc: dict, parsed_data: dict) -> dict:
        """Parse GitHub Actions workflow."""
        # Extract jobs
        jobs = doc.get("jobs", {})
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue

            job_data = {
                "name": job_name,
                "runs_on": job_config.get("runs-on", "unknown"),
                "steps": job_config.get("steps", []),
                "needs": job_config.get("needs", []),
                "environment": job_config.get("environment"),
                "permissions": job_config.get("permissions"),
                "container": job_config.get("container"),
                "services": job_config.get("services", {}),
            }

            # Analyze steps
            for step in job_data["steps"]:
                if isinstance(step, dict):
                    # Check for secrets usage
                    uses = step.get("uses", "")
                    run = step.get("run", "")

                    if "${{ secrets." in str(run) or "${{ secrets." in str(uses):
                        parsed_data["secrets_usage"].append({
                            "job": job_name,
                            "step": step.get("name", uses),
                        })

                    # Check for artifact upload/download
                    if "actions/upload-artifact" in uses:
                        parsed_data["artifacts"].append({
                            "type": "upload",
                            "job": job_name,
                        })
                    elif "actions/download-artifact" in uses:
                        parsed_data["artifacts"].append({
                            "type": "download",
                            "job": job_name,
                        })

                    # Check for caching
                    if "actions/cache" in uses:
                        parsed_data["caching"].append({
                            "job": job_name,
                            "path": step.get("with", {}).get("path", ""),
                        })

            parsed_data["jobs"].append(job_data)

        # Extract triggers
        on_triggers = doc.get("on", {})
        if isinstance(on_triggers, str):
            parsed_data["triggers"].append(on_triggers)
        elif isinstance(on_triggers, list):
            parsed_data["triggers"].extend(on_triggers)
        elif isinstance(on_triggers, dict):
            for trigger, config in on_triggers.items():
                parsed_data["triggers"].append({
                    "type": trigger,
                    "config": config,
                })

        # Security features
        parsed_data["security_features"] = {
            "has_permissions": bool(doc.get("permissions")),
            "has_environment_protection": any(
                job.get("environment") for job in parsed_data["jobs"]
            ),
            "uses_oidc": any(
                "id-token: write" in str(job.get("permissions", ""))
                for job in parsed_data["jobs"]
            ),
        }

        return parsed_data

    def _parse_gitlab_ci(self, doc: dict, parsed_data: dict) -> dict:
        """Parse GitLab CI configuration."""
        stages = doc.get("stages", [])
        parsed_data["stages"] = stages

        for key, value in doc.items():
            if key in ["stages", "variables", "include", "default"]:
                continue

            if isinstance(value, dict):
                job_data = {
                    "name": key,
                    "stage": value.get("stage", "test"),
                    "script": value.get("script", []),
                    "image": value.get("image"),
                    "services": value.get("services", []),
                    "variables": value.get("variables", {}),
                    "tags": value.get("tags", []),
                    "only": value.get("only", []),
                    "except": value.get("except", []),
                }

                parsed_data["jobs"].append(job_data)

                # Check for environment
                if "environment" in value:
                    parsed_data["environments"].append(value["environment"])

        return parsed_data

    def _parse_circleci(self, doc: dict, parsed_data: dict) -> dict:
        """Parse CircleCI configuration."""
        jobs = doc.get("jobs", {})
        workflows = doc.get("workflows", {})

        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict):
                parsed_data["jobs"].append({
                    "name": job_name,
                    "docker": job_config.get("docker", []),
                    "steps": job_config.get("steps", []),
                    "resource_class": job_config.get("resource_class"),
                })

        for workflow_name, workflow_config in workflows.items():
            if isinstance(workflow_config, dict):
                for job in workflow_config.get("jobs", []):
                    if isinstance(job, str):
                        parsed_data["triggers"].append({
                            "workflow": workflow_name,
                            "job": job,
                        })

        return parsed_data

    def _parse_azure_devops(self, doc: dict, parsed_data: dict) -> dict:
        """Parse Azure DevOps pipeline."""
        stages = doc.get("stages", [])

        for stage in stages:
            if isinstance(stage, dict):
                parsed_data["stages"].append(stage.get("displayName", stage.get("stage", "")))

                for job in stage.get("jobs", []):
                    if isinstance(job, dict):
                        parsed_data["jobs"].append({
                            "name": job.get("job", job.get("displayName", "")),
                            "pool": job.get("pool", {}),
                            "steps": job.get("steps", []),
                            "variables": job.get("variables", []),
                        })

        # Triggers
        if "trigger" in doc:
            parsed_data["triggers"].append({"type": "ci", "config": doc["trigger"]})
        if "pr" in doc:
            parsed_data["triggers"].append({"type": "pr", "config": doc["pr"]})

        return parsed_data

    def _parse_jenkinsfile(self, content: str) -> dict:
        """Parse Jenkinsfile (basic regex-based parsing)."""
        parsed_data = {
            "ci_type": "jenkins",
            "pipeline_type": "unknown",
            "stages": [],
            "agents": [],
            "environment": {},
            "tools": [],
            "triggers": [],
            "post_actions": [],
        }

        # Detect pipeline type
        if "pipeline {" in content:
            parsed_data["pipeline_type"] = "declarative"
        elif "node {" in content:
            parsed_data["pipeline_type"] = "scripted"

        # Extract stages
        stage_pattern = r'stage\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(stage_pattern, content, re.DOTALL):
            parsed_data["stages"].append({
                "name": match.group(1),
                "content": match.group(2),
            })

        # Extract agent
        agent_match = re.search(r'agent\s*(?:\{([^}]+)\}|\(\s*([^\)]+)\s*\))', content)
        if agent_match:
            parsed_data["agents"].append(agent_match.group(1) or agent_match.group(2))

        # Extract environment variables
        env_match = re.search(r'environment\s*\{([^}]+)\}', content)
        if env_match:
            env_content = env_match.group(1)
            for line in env_content.split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    parsed_data["environment"][key.strip()] = value.strip().strip('"\'')

        return parsed_data

    def _parse_generic_cicd(self, doc: dict, parsed_data: dict) -> dict:
        """Generic CI/CD parsing for unknown types."""
        # Try to extract common patterns
        if "jobs" in doc:
            parsed_data["jobs"] = doc["jobs"]
        if "stages" in doc:
            parsed_data["stages"] = doc["stages"]
        if "workflow" in doc:
            parsed_data["triggers"] = doc["workflow"]

        return parsed_data

    def extract_resources(self, parsed_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract resources for rule evaluation."""
        resources = []

        for job in parsed_data.get("jobs", []):
            resources.append({
                "file_type": "cicd",
                "ci_type": parsed_data.get("ci_type"),
                "kind": "job",
                "name": job.get("name", ""),
                "properties": job,
            })

        resources.append({
            "file_type": "cicd",
            "ci_type": parsed_data.get("ci_type"),
            "kind": "pipeline",
            "properties": {
                "triggers": parsed_data.get("triggers", []),
                "environments": parsed_data.get("environments", []),
                "security_features": parsed_data.get("security_features", {}),
                "secrets_usage": parsed_data.get("secrets_usage", []),
            },
        })

        return resources
