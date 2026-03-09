"""
Dockerfile Parser
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.parsers.base import BaseParser, ParsedFile


class DockerfileParser(BaseParser):
    """Parser for Dockerfiles."""
    
    def __init__(self):
        super().__init__()
        self.supported_filenames = ["Dockerfile", "Containerfile"]
        self.supported_extensions = [".dockerfile"]
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a Dockerfile."""
        return (
            file_path.name in self.supported_filenames or
            file_path.suffix in self.supported_extensions or
            "dockerfile" in file_path.name.lower()
        )
    
    def parse(self, file_path: Path, content: str) -> ParsedFile:
        """Parse Dockerfile and extract instructions."""
        parse_errors = []
        parsed_data = {
            "instructions": [],
            "base_image": None,
            "exposed_ports": [],
            "env_vars": {},
            "volumes": [],
            "user": None,
            "workdir": None,
            "healthcheck": None,
            "labels": {},
            "copy_commands": [],
            "run_commands": [],
            "security_issues": [],
        }
        
        try:
            lines = content.splitlines()
            current_instruction = None
            multiline_content = ""
            
            for line_num, line in enumerate(lines, 1):
                # Skip comments and empty lines
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                
                # Handle line continuation
                if multiline_content:
                    multiline_content += " " + stripped.rstrip("\\").strip()
                    if not stripped.endswith("\\"):
                        # End of multiline
                        self._parse_instruction(
                            multiline_content,
                            line_num,
                            parsed_data,
                        )
                        multiline_content = ""
                    continue
                
                if stripped.endswith("\\"):
                    multiline_content = stripped.rstrip("\\").strip()
                    continue
                
                # Parse single-line instruction
                self._parse_instruction(stripped, line_num, parsed_data)
            
            # Handle any remaining multiline content
            if multiline_content:
                self._parse_instruction(multiline_content, len(lines), parsed_data)
            
            # Analyze security issues
            parsed_data["security_issues"] = self._analyze_security(parsed_data)
            
        except Exception as e:
            parse_errors.append(str(e))
        
        return ParsedFile(
            file_path=str(file_path),
            file_type="dockerfile",
            raw_content=content,
            parsed_data=parsed_data,
            line_count=len(content.splitlines()),
            parse_errors=parse_errors,
        )
    
    def _parse_instruction(self, instruction: str, line_num: int, parsed_data: Dict) -> None:
        """Parse a single Dockerfile instruction."""
        # Match instruction pattern
        match = re.match(r'^(\w+)\s*(.*)', instruction, re.IGNORECASE)
        if not match:
            return
        
        cmd = match.group(1).upper()
        args = match.group(2).strip()
        
        instruction_data = {
            "instruction": cmd,
            "arguments": args,
            "line_number": line_num,
        }
        
        parsed_data["instructions"].append(instruction_data)
        
        # Parse specific instructions
        if cmd == "FROM":
            parsed_data["base_image"] = self._parse_from(args)
        elif cmd == "EXPOSE":
            parsed_data["exposed_ports"].extend(self._parse_expose(args))
        elif cmd == "ENV":
            parsed_data["env_vars"].update(self._parse_env(args))
        elif cmd == "VOLUME":
            parsed_data["volumes"].extend(self._parse_volume(args))
        elif cmd == "USER":
            parsed_data["user"] = args
        elif cmd == "WORKDIR":
            parsed_data["workdir"] = args
        elif cmd == "HEALTHCHECK":
            parsed_data["healthcheck"] = self._parse_healthcheck(args)
        elif cmd == "LABEL":
            parsed_data["labels"].update(self._parse_label(args))
        elif cmd == "COPY" or cmd == "ADD":
            parsed_data["copy_commands"].append({
                "instruction": cmd,
                "source": args.split()[0] if args.split() else "",
                "destination": args.split()[-1] if len(args.split()) > 1 else "",
                "line_number": line_num,
            })
        elif cmd == "RUN":
            parsed_data["run_commands"].append({
                "command": args,
                "line_number": line_num,
            })
    
    def _parse_from(self, args: str) -> Dict[str, Any]:
        """Parse FROM instruction."""
        parts = args.split()
        image = parts[0]
        
        # Parse image components
        registry = ""
        repository = ""
        tag = "latest"
        digest = ""
        
        if "@" in image:
            image_part, digest = image.split("@", 1)
        else:
            image_part = image
        
        if ":" in image_part:
            image_part, tag = image_part.rsplit(":", 1)
        
        if "/" in image_part:
            parts = image_part.split("/")
            if "." in parts[0] or ":" in parts[0]:
                registry = parts[0]
                repository = "/".join(parts[1:])
            else:
                repository = image_part
        else:
            repository = image_part
        
        return {
            "full": image,
            "registry": registry,
            "repository": repository,
            "tag": tag,
            "digest": digest,
            "is_latest": tag == "latest",
            "has_digest": bool(digest),
        }
    
    def _parse_expose(self, args: str) -> List[Dict[str, Any]]:
        """Parse EXPOSE instruction."""
        ports = []
        for port_spec in args.split():
            if "/" in port_spec:
                port, protocol = port_spec.split("/", 1)
            else:
                port = port_spec
                protocol = "tcp"
            
            ports.append({
                "port": int(port) if port.isdigit() else port,
                "protocol": protocol,
            })
        
        return ports
    
    def _parse_env(self, args: str) -> Dict[str, str]:
        """Parse ENV instruction."""
        env_vars = {}
        
        # Handle KEY=value format
        if "=" in args:
            pairs = re.findall(r'(\w+)=([^\s]+)', args)
            for key, value in pairs:
                env_vars[key] = value.strip('"\'')
        else:
            # Handle KEY value format
            parts = args.split(None, 1)
            if len(parts) == 2:
                env_vars[parts[0]] = parts[1].strip('"\'')
        
        return env_vars
    
    def _parse_volume(self, args: str) -> List[str]:
        """Parse VOLUME instruction."""
        volumes = []
        
        # Handle JSON array format
        if args.startswith("["):
            try:
                import json
                volumes = json.loads(args)
            except:
                pass
        else:
            # Handle space-separated format
            volumes = args.split()
        
        return volumes
    
    def _parse_healthcheck(self, args: str) -> Dict[str, Any]:
        """Parse HEALTHCHECK instruction."""
        if args.upper() == "NONE":
            return {"disabled": True}
        
        healthcheck = {"disabled": False}
        
        # Parse options
        interval_match = re.search(r'--interval=(\S+)', args)
        timeout_match = re.search(r'--timeout=(\S+)', args)
        retries_match = re.search(r'--retries=(\d+)', args)
        cmd_match = re.search(r'CMD\s+(.+)', args)
        
        if interval_match:
            healthcheck["interval"] = interval_match.group(1)
        if timeout_match:
            healthcheck["timeout"] = timeout_match.group(1)
        if retries_match:
            healthcheck["retries"] = int(retries_match.group(1))
        if cmd_match:
            healthcheck["command"] = cmd_match.group(1)
        
        return healthcheck
    
    def _parse_label(self, args: str) -> Dict[str, str]:
        """Parse LABEL instruction."""
        labels = {}
        
        # Handle KEY=value format
        pairs = re.findall(r'(\w+\.?\w*)=([^\s]+)', args)
        for key, value in pairs:
            labels[key] = value.strip('"\'')
        
        return labels
    
    def _analyze_security(self, parsed_data: Dict) -> List[Dict[str, Any]]:
        """Analyze Dockerfile for security issues."""
        issues = []
        
        # Check for root user
        if not parsed_data.get("user") or parsed_data["user"] == "root":
            issues.append({
                "issue": "running_as_root",
                "severity": "high",
                "description": "Container runs as root user",
                "recommendation": "Add USER instruction to run as non-root",
            })
        
        # Check for latest tag
        base_image = parsed_data.get("base_image", {})
        if base_image and base_image.get("is_latest"):
            issues.append({
                "issue": "latest_tag",
                "severity": "medium",
                "description": "Using 'latest' tag for base image",
                "recommendation": "Pin to specific version tag",
            })
        
        # Check for missing healthcheck
        if not parsed_data.get("healthcheck"):
            issues.append({
                "issue": "no_healthcheck",
                "severity": "low",
                "description": "No HEALTHCHECK instruction",
                "recommendation": "Add HEALTHCHECK for container health monitoring",
            })
        
        # Check for ADD instead of COPY
        for cmd in parsed_data.get("copy_commands", []):
            if cmd["instruction"] == "ADD" and not cmd["source"].startswith(("http://", "https://")):
                issues.append({
                    "issue": "add_instead_of_copy",
                    "severity": "low",
                    "description": f"Using ADD instead of COPY at line {cmd['line_number']}",
                    "recommendation": "Use COPY unless extracting archives or fetching URLs",
                    "line_number": cmd["line_number"],
                })
        
        # Check for secrets in ENV
        secret_patterns = ["password", "secret", "key", "token", "credential", "api_key"]
        for env_name in parsed_data.get("env_vars", {}).keys():
            if any(pattern in env_name.lower() for pattern in secret_patterns):
                issues.append({
                    "issue": "secret_in_env",
                    "severity": "critical",
                    "description": f"Potential secret in ENV variable: {env_name}",
                    "recommendation": "Use secrets management instead of ENV for sensitive data",
                })
        
        # Check for apt-get without clean
        for run_cmd in parsed_data.get("run_commands", []):
            cmd = run_cmd["command"]
            if "apt-get" in cmd and "install" in cmd and "clean" not in cmd and "rm" not in cmd:
                issues.append({
                    "issue": "apt_no_cleanup",
                    "severity": "low",
                    "description": f"apt-get install without cleanup at line {run_cmd['line_number']}",
                    "recommendation": "Add 'rm -rf /var/lib/apt/lists/*' to reduce image size",
                    "line_number": run_cmd["line_number"],
                })
        
        return issues
    
    def extract_resources(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract resources for rule evaluation."""
        return [
            {
                "file_type": "dockerfile",
                "base_image": parsed_data.get("base_image"),
                "exposed_ports": parsed_data.get("exposed_ports", []),
                "env_vars": parsed_data.get("env_vars", {}),
                "user": parsed_data.get("user"),
                "healthcheck": parsed_data.get("healthcheck"),
                "security_issues": parsed_data.get("security_issues", []),
                "properties": parsed_data,
            }
        ]
