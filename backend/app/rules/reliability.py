"""
Reliability Rules for Infrastructure Analysis
"""

from typing import Any, Dict, List
from app.rules.base import BaseRule, Rule, RuleFinding, Severity, Category, register_rule


@register_rule
class MissingBackupStrategyRule(BaseRule):
    """Check for missing backup strategy in Terraform."""
    
    @property
    def rule(self) -> Rule:
        return Rule(
            id="REL-001",
            name="Missing Backup Strategy",
            description="Database or storage resource does not have backup configuration",
            recommendation="Enable automated backups with appropriate retention period",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            tags=["terraform", "backup", "database"],
        )
    
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        
        for resource in resources:
            resource_type = resource.get("resource_type", "")
            
            if resource_type == "aws_db_instance":
                resource_data = resource.get("properties", {})
                raw_body = resource_data.get("raw_body", "")
                
                if "backup_retention_period" not in raw_body:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description="RDS instance has no backup retention configured",
                        recommendation="Set backup_retention_period to at least 7 days",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                    ))
            
            elif resource_type == "aws_s3_bucket":
                resource_data = resource.get("properties", {})
                raw_body = resource_data.get("raw_body", "")
                
                if "versioning" not in raw_body.lower():
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.HIGH,
                        category=self.rule.category,
                        description="S3 bucket does not have versioning enabled",
                        recommendation="Enable S3 versioning for data protection",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                    ))
        
        return findings


@register_rule
class MissingHealthCheckRule(BaseRule):
    """Check for missing health checks in Kubernetes."""
    
    @property
    def rule(self) -> Rule:
        return Rule(
            id="REL-002",
            name="Missing Health Checks",
            description="Container does not have liveness/readiness probes configured",
            recommendation="Configure liveness and readiness probes for all containers",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["kubernetes", "health", "probe"],
        )
    
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        
        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue
            
            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])
            
            for container in containers:
                has_liveness = container.get("liveness_probe", False)
                has_readiness = container.get("readiness_probe", False)
                
                if not has_liveness:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.HIGH,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no liveness probe",
                        recommendation="Add livenessProbe to detect and restart unhealthy containers",
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name"), "probe_type": "liveness"},
                    ))
                
                if not has_readiness:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.MEDIUM,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no readiness probe",
                        recommendation="Add readinessProbe to prevent traffic to unready containers",
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name"), "probe_type": "readiness"},
                    ))
        
        return findings


@register_rule
class MissingPDBRule(BaseRule):
    """Check for missing Pod Disruption Budget."""
    
    @property
    def rule(self) -> Rule:
        return Rule(
            id="REL-003",
            name="Missing Pod Disruption Budget",
            description="No PodDisruptionBudget found for deployment",
            recommendation="Create PDB to ensure minimum availability during voluntary disruptions",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "pdb", "availability"],
        )
    
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        
        # Collect deployments and PDBs
        deployments = []
        pdb_selectors = []
        
        for resource in resources:
            if resource.get("file_type") == "kubernetes":
                if resource.get("kind") == "Deployment":
                    deployments.append(resource)
                elif resource.get("kind") == "PodDisruptionBudget":
                    pdb_selectors.append(resource.get("properties", {}).get("selector", {}))
        
        # Check each deployment for PDB coverage
        for deployment in deployments:
            name = deployment.get("name", "")
            labels = deployment.get("properties", {}).get("labels", {})
            
            # Simple check - in production, match selectors properly
            has_pdb = any(
                pdb.get("matchLabels", {}).get("app") == labels.get("app")
                for pdb in pdb_selectors
            )
            
            if not has_pdb:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=name,
                ))
        
        return findings


@register_rule
class MissingMultiAZRule(BaseRule):
    """Check for missing multi-AZ configuration."""
    
    @property
    def rule(self) -> Rule:
        return Rule(
            id="REL-004",
            name="Missing Multi-AZ Configuration",
            description="Database or critical resource is not configured for multi-AZ deployment",
            recommendation="Enable multi-AZ for high availability",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "aws", "high-availability"],
        )
    
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        
        for resource in resources:
            if resource.get("resource_type") != "aws_db_instance":
                continue
            
            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")
            
            if "multi_az" not in raw_body.lower() or "multi_az = false" in raw_body.lower():
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description="RDS instance is not configured for multi-AZ",
                    recommendation="Set multi_az = true for production databases",
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                ))
        
        return findings


@register_rule
class DockerMissingHealthcheckRule(BaseRule):
    """Check for missing HEALTHCHECK in Dockerfile."""
    
    @property
    def rule(self) -> Rule:
        return Rule(
            id="REL-005",
            name="Missing Docker HEALTHCHECK",
            description="Dockerfile does not have HEALTHCHECK instruction",
            recommendation="Add HEALTHCHECK to enable container health monitoring",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["docker", "health", "monitoring"],
        )
    
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        
        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue
            
            healthcheck = resource.get("healthcheck")
            if not healthcheck or healthcheck.get("disabled"):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))
        
        return findings


@register_rule
class MissingDeploymentStrategyRule(BaseRule):
    """Check for missing deployment strategy."""
    
    @property
    def rule(self) -> Rule:
        return Rule(
            id="REL-006",
            name="Missing Deployment Strategy",
            description="Deployment does not specify a rollout strategy",
            recommendation="Use RollingUpdate strategy with appropriate maxSurge and maxUnavailable",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["kubernetes", "deployment", "strategy"],
        )
    
    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        
        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue
            
            deployment = resource.get("properties", {})
            strategy = deployment.get("strategy", {})
            
            if not strategy:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=deployment.get("name"),
                ))
        
        return findings
