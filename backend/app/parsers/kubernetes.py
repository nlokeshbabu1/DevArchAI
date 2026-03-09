"""
Kubernetes YAML Parser
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.parsers.base import BaseParser, ParsedFile


class KubernetesParser(BaseParser):
    """Parser for Kubernetes YAML manifests."""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = [".yaml", ".yml"]
        self.k8s_api_groups = ["apps", "batch", "networking.k8s.io", "autoscaling", "policy"]
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a Kubernetes manifest."""
        if file_path.suffix not in self.supported_extensions:
            return False
        
        # Check for kubernetes-specific directories
        k8s_indicators = ["kubernetes", "k8s", "manifests", "deployments", "helm"]
        return any(indicator in str(file_path).lower() for indicator in k8s_indicators)
    
    def parse(self, file_path: Path, content: str) -> ParsedFile:
        """Parse Kubernetes YAML file."""
        parse_errors = []
        parsed_data = {
            "resources": [],
            "deployments": [],
            "services": [],
            "configmaps": [],
            "secrets": [],
            "ingresses": [],
            "hpa": [],
            "pdb": [],
            "network_policies": [],
        }
        
        try:
            # Handle multi-document YAML
            documents = list(yaml.safe_load_all(content))
            
            for doc in documents:
                if not doc:
                    continue
                
                if not isinstance(doc, dict):
                    continue
                
                kind = doc.get("kind", "")
                api_version = doc.get("apiVersion", "")
                
                resource_data = {
                    "kind": kind,
                    "api_version": api_version,
                    "name": doc.get("metadata", {}).get("name", ""),
                    "namespace": doc.get("metadata", {}).get("namespace", "default"),
                    "labels": doc.get("metadata", {}).get("labels", {}),
                    "annotations": doc.get("metadata", {}).get("annotations", {}),
                    "spec": doc.get("spec", {}),
                    "raw": doc,
                }
                
                parsed_data["resources"].append(resource_data)
                
                # Categorize by kind
                if kind == "Deployment":
                    parsed_data["deployments"].append(self._parse_deployment(resource_data))
                elif kind == "Service":
                    parsed_data["services"].append(self._parse_service(resource_data))
                elif kind == "ConfigMap":
                    parsed_data["configmaps"].append(resource_data)
                elif kind == "Secret":
                    parsed_data["secrets"].append(resource_data)
                elif kind == "Ingress":
                    parsed_data["ingresses"].append(self._parse_ingress(resource_data))
                elif kind == "HorizontalPodAutoscaler":
                    parsed_data["hpa"].append(self._parse_hpa(resource_data))
                elif kind == "PodDisruptionBudget":
                    parsed_data["pdb"].append(self._parse_pdb(resource_data))
                elif kind == "NetworkPolicy":
                    parsed_data["network_policies"].append(self._parse_network_policy(resource_data))
                    
        except yaml.YAMLError as e:
            parse_errors.append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            parse_errors.append(str(e))
        
        return ParsedFile(
            file_path=str(file_path),
            file_type="kubernetes",
            raw_content=content,
            parsed_data=parsed_data,
            line_count=len(content.splitlines()),
            parse_errors=parse_errors,
        )
    
    def _parse_deployment(self, data: Dict) -> Dict[str, Any]:
        """Extract deployment-specific information."""
        spec = data.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        
        containers = []
        for container in pod_spec.get("containers", []):
            containers.append({
                "name": container.get("name", ""),
                "image": container.get("image", ""),
                "resources": container.get("resources", {}),
                "liveness_probe": "livenessProbe" in container,
                "readiness_probe": "readinessProbe" in container,
                "security_context": container.get("securityContext", {}),
                "env": container.get("env", []),
                "ports": container.get("ports", []),
            })
        
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", "default"),
            "replicas": spec.get("replicas", 1),
            "strategy": spec.get("strategy", {}),
            "containers": containers,
            "volumes": pod_spec.get("volumes", []),
            "service_account": pod_spec.get("serviceAccountName", ""),
            "node_selector": pod_spec.get("nodeSelector", {}),
            "affinity": pod_spec.get("affinity", {}),
            "tolerations": pod_spec.get("tolerations", []),
        }
    
    def _parse_service(self, data: Dict) -> Dict[str, Any]:
        """Extract service-specific information."""
        spec = data.get("spec", {})
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", "default"),
            "type": spec.get("type", "ClusterIP"),
            "ports": spec.get("ports", []),
            "selector": spec.get("selector", {}),
            "load_balancer_ip": spec.get("loadBalancerIP"),
        }
    
    def _parse_ingress(self, data: Dict) -> Dict[str, Any]:
        """Extract ingress-specific information."""
        spec = data.get("spec", {})
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", "default"),
            "rules": spec.get("rules", []),
            "tls": spec.get("tls", []),
            "annotations": data.get("annotations", {}),
        }
    
    def _parse_hpa(self, data: Dict) -> Dict[str, Any]:
        """Extract HPA-specific information."""
        spec = data.get("spec", {})
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", "default"),
            "target_ref": spec.get("scaleTargetRef", {}),
            "min_replicas": spec.get("minReplicas"),
            "max_replicas": spec.get("maxReplicas"),
            "metrics": spec.get("metrics", []),
        }
    
    def _parse_pdb(self, data: Dict) -> Dict[str, Any]:
        """Extract PDB-specific information."""
        spec = data.get("spec", {})
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", "default"),
            "min_available": spec.get("minAvailable"),
            "max_unavailable": spec.get("maxUnavailable"),
            "selector": spec.get("selector", {}),
        }
    
    def _parse_network_policy(self, data: Dict) -> Dict[str, Any]:
        """Extract network policy-specific information."""
        spec = data.get("spec", {})
        return {
            "name": data.get("name", ""),
            "namespace": data.get("namespace", "default"),
            "pod_selector": spec.get("podSelector", {}),
            "policy_types": spec.get("policyTypes", []),
            "ingress": spec.get("ingress", []),
            "egress": spec.get("egress", []),
        }
    
    def extract_resources(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract resources for rule evaluation."""
        resources = []
        
        for deployment in parsed_data.get("deployments", []):
            resources.append({
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": deployment.get("name"),
                "properties": deployment,
            })
        
        for hpa in parsed_data.get("hpa", []):
            resources.append({
                "file_type": "kubernetes",
                "kind": "HorizontalPodAutoscaler",
                "name": hpa.get("name"),
                "properties": hpa,
            })
        
        for service in parsed_data.get("services", []):
            resources.append({
                "file_type": "kubernetes",
                "kind": "Service",
                "name": service.get("name"),
                "properties": service,
            })
        
        for pdb in parsed_data.get("pdb", []):
            resources.append({
                "file_type": "kubernetes",
                "kind": "PodDisruptionBudget",
                "name": pdb.get("name"),
                "properties": pdb,
            })
        
        for ingress in parsed_data.get("ingresses", []):
            resources.append({
                "file_type": "kubernetes",
                "kind": "Ingress",
                "name": ingress.get("name"),
                "properties": ingress,
            })
        
        return resources
