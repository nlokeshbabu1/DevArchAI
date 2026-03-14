"""
Kubernetes Security Rules - DevSecOps Rule Set (K8S-SEC-001 to K8S-SEC-010)

Production-grade Kubernetes security scanning rules for DevArchAI.
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["kubernetes"])
class K8sMissingNetworkPolicyRule(BaseRule):
    """K8S-SEC-001: Check for missing NetworkPolicy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-001",
            name="Missing Network Policy",
            description="Without NetworkPolicies, all pods can communicate freely, violating zero-trust principles",
            recommendation="Create restrictive network policies:\n\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: default-deny\nspec:\n  podSelector: {}\n  policyTypes:\n  - Ingress\n  - Egress",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "networking", "security", "networkpolicy"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        has_network_policy = False
        has_workload = False
        workload_names = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind")
            name = resource.get("name", "")

            if kind in ["Deployment", "StatefulSet", "DaemonSet", "Pod", "ReplicaSet"]:
                has_workload = True
                workload_names.append(name)
            if kind == "NetworkPolicy":
                has_network_policy = True

        if has_workload and not has_network_policy:
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


@register_rule(file_types=["kubernetes"])
class K8sPrivilegedContainerRule(BaseRule):
    """K8S-SEC-002: Check for privileged containers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-002",
            name="Privileged Container",
            description="Privileged containers bypass Kubernetes security controls and can access host resources",
            recommendation="Disable privileged mode:\n\nsecurityContext:\n  privileged: false",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "privileged"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])
                init_containers = resource.get("properties", {}).get("init_containers", [])

                for container in containers + init_containers:
                    security_context = container.get("security_context", {})
                    if security_context.get("privileged"):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' runs in privileged mode",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sRunAsRootAllowedRule(BaseRule):
    """K8S-SEC-003: Check if runAsRoot is allowed."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-003",
            name="runAsRoot Allowed",
            description="Containers should not run as root. Missing runAsNonRoot allows root execution",
            recommendation="Enable runAsNonRoot:\n\nsecurityContext:\n  runAsNonRoot: true\n  runAsUser: 1000",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "root", "user"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                pod_security_context = resource.get("properties", {}).get("pod_security_context", {})
                containers = resource.get("properties", {}).get("containers", [])

                # Check pod-level security context
                pod_run_as_non_root = pod_security_context.get("runAsNonRoot")

                for container in containers:
                    container_security_context = container.get("security_context", {})
                    container_run_as_non_root = container_security_context.get("runAsNonRoot")
                    run_as_user = container_security_context.get("runAsUser", 0)

                    # Flag if neither pod nor container enforces non-root
                    if not pod_run_as_non_root and not container_run_as_non_root:
                        if run_as_user == 0 or run_as_user is None:
                            findings.append(RuleFinding(
                                rule_id=self.rule.id,
                                rule_name=self.rule.name,
                                severity=self.rule.severity,
                                category=self.rule.category,
                                description=f"Container '{container.get('name')}' can run as root",
                                recommendation=self.rule.recommendation,
                                file_path=file_path,
                                resource_name=container.get("name"),
                                metadata={"container": container.get("name")},
                            ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingResourceLimitsRule(BaseRule):
    """K8S-SEC-004: Check for missing resource limits."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-004",
            name="Missing Resource Limits",
            description="Pods without resource limits can destabilize clusters and cause denial of service",
            recommendation="Define CPU and memory limits:\n\nresources:\n  limits:\n    memory: \"512Mi\"\n    cpu: \"1\"\n  requests:\n    memory: \"256Mi\"\n    cpu: \"0.5\"",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "resources", "limits"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    resources_config = container.get("resources", {})
                    limits = resources_config.get("limits", {})

                    if not limits.get("cpu") or not limits.get("memory"):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' has no resource limits",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingLivenessProbeRule(BaseRule):
    """K8S-SEC-005: Check for missing liveness probe."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-005",
            name="Missing Liveness Probe",
            description="Liveness probes detect application crashes and restart unhealthy containers",
            recommendation="Add liveness probe:\n\nlivenessProbe:\n  httpGet:\n    path: /healthz\n    port: 8080\n  initialDelaySeconds: 15\n  periodSeconds: 10",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "probe", "health", "liveness"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    if not container.get("liveness_probe"):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' has no liveness probe",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingReadinessProbeRule(BaseRule):
    """K8S-SEC-006: Check for missing readiness probe."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-006",
            name="Missing Readiness Probe",
            description="Readiness probes ensure traffic is only sent to containers ready to handle requests",
            recommendation="Add readiness probe:\n\nreadinessProbe:\n  httpGet:\n    path: /ready\n    port: 8080\n  initialDelaySeconds: 5\n  periodSeconds: 5",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "probe", "health", "readiness"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    if not container.get("readiness_probe"):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' has no readiness probe",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sHostPathVolumeRule(BaseRule):
    """K8S-SEC-007: Check for hostPath volume usage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-007",
            name="HostPath Volume Used",
            description="HostPath volumes expose host filesystem to containers, creating security risks",
            recommendation="Avoid hostPath volumes. Use PersistentVolumes, emptyDir, or config maps instead",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "volume", "hostpath", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                volumes = resource.get("properties", {}).get("volumes", [])

                for volume in volumes:
                    if volume.get("host_path"):
                        host_path = volume.get("host_path", {})
                        path = host_path.get("path", "unknown")
                        path_type = host_path.get("type", "")

                        # Extra severity for sensitive paths
                        sensitive_paths = ["/etc", "/var", "/root", "/home", "/proc", "/sys"]
                        is_sensitive = any(path.startswith(sp) for sp in sensitive_paths)
                        severity = Severity.CRITICAL if is_sensitive else self.rule.severity

                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=severity,
                            category=self.rule.category,
                            description=f"HostPath volume '{volume.get('name')}' mounts '{path}'",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=volume.get("name"),
                            metadata={"path": path, "type": path_type},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sPrivilegeEscalationAllowedRule(BaseRule):
    """K8S-SEC-008: Check if privilege escalation is allowed."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-008",
            name="Privilege Escalation Allowed",
            description="Containers should not allow privilege escalation. allowPrivilegeEscalation should be false",
            recommendation="Disable privilege escalation:\n\nsecurityContext:\n  allowPrivilegeEscalation: false",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "privilege-escalation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    security_context = container.get("security_context", {})
                    allow_escalation = security_context.get("allowPrivilegeEscalation")

                    # Flag if explicitly true or not set (defaults to true)
                    if allow_escalation is True or allow_escalation is None:
                        # Don't flag if runAsNonRoot is true (mitigates risk)
                        run_as_non_root = security_context.get("runAsNonRoot")
                        if not run_as_non_root:
                            findings.append(RuleFinding(
                                rule_id=self.rule.id,
                                rule_name=self.rule.name,
                                severity=self.rule.severity,
                                category=self.rule.category,
                                description=f"Container '{container.get('name')}' allows privilege escalation",
                                recommendation=self.rule.recommendation,
                                file_path=file_path,
                                resource_name=container.get("name"),
                                metadata={"container": container.get("name")},
                            ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingPodSecurityContextRule(BaseRule):
    """K8S-SEC-009: Check for missing pod security context."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-009",
            name="Missing Pod Security Context",
            description="Security contexts enforce container security policies at pod level",
            recommendation="Add pod security context:\n\nsecurityContext:\n  runAsNonRoot: true\n  runAsUser: 1000\n  fsGroup: 1000\n  seccompProfile:\n    type: RuntimeDefault",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "context"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                pod_security_context = resource.get("properties", {}).get("pod_security_context")

                if not pod_security_context:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sInsecureCapabilitiesRule(BaseRule):
    """K8S-SEC-010: Check for insecure Linux capabilities."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-010",
            name="Insecure Capabilities",
            description="Dangerous Linux capabilities like CAP_SYS_ADMIN can escalate privileges",
            recommendation="Drop all capabilities and add only what's needed:\n\nsecurityContext:\n  capabilities:\n    drop: [\"ALL\"]\n    add: [\"NET_BIND_SERVICE\"]",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "capabilities", "linux"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        dangerous_capabilities = [
            "CAP_SYS_ADMIN", "SYS_ADMIN",  # Most dangerous - almost root
            "CAP_NET_ADMIN", "NET_ADMIN",  # Network manipulation
            "CAP_SYS_PTRACE", "SYS_PTRACE",  # Process tracing
            "CAP_SYS_MODULE", "SYS_MODULE",  # Kernel modules
            "CAP_DAC_READ_SEARCH", "DAC_READ_SEARCH",  # Bypass file permissions
            "CAP_NET_RAW", "NET_RAW",  # Raw sockets
            "CAP_SYS_RAWIO", "SYS_RAWIO",  # Raw I/O
            "CAP_MKNOD", "MKNOD",  # Create device files
            "CAP_CHOWN", "CHOWN",  # Change file ownership
            "CAP_FOWNER", "FOWNER",  # Bypass permission checks
            "CAP_SETUID", "SETUID",  # Manipulate UIDs
            "CAP_SETGID", "SETGID",  # Manipulate GIDs
        ]

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    security_context = container.get("security_context", {})
                    capabilities = security_context.get("capabilities", {})
                    added_caps = capabilities.get("add", [])

                    for cap in added_caps:
                        if cap.upper() in dangerous_capabilities or cap in dangerous_capabilities:
                            findings.append(RuleFinding(
                                rule_id=self.rule.id,
                                rule_name=self.rule.name,
                                severity=self.rule.severity,
                                category=self.rule.category,
                                description=f"Container '{container.get('name')}' adds dangerous capability: {cap}",
                                recommendation=self.rule.recommendation,
                                file_path=file_path,
                                resource_name=container.get("name"),
                                metadata={"container": container.get("name"), "capability": cap},
                            ))

        return findings
