"""Live cluster security analysis — reuses DevArchAI rule concepts."""

from __future__ import annotations

from typing import Any

REMEDIATION: dict[str, str] = {
    "K8S-SEC-PRIV": "Set securityContext.privileged=false and use least-privilege capabilities.",
    "K8S-SEC-ROOT": "Set securityContext.runAsNonRoot=true and runAsUser > 0.",
    "K8S-SEC-HOSTNET": "Disable hostNetwork unless required for node-level networking.",
    "K8S-SEC-HOSTPID": "Disable hostPID to prevent host process namespace access.",
    "K8S-SEC-HOSTPATH": "Avoid hostPath mounts; use PVCs or ConfigMaps instead.",
    "K8S-SEC-CAP": "Drop ALL capabilities and add only required ones.",
    "K8S-SEC-ALLOW-PRIV-ESC": "Set allowPrivilegeEscalation=false in securityContext.",
    "K8S-SEC-READONLY-ROOTFS": "Set readOnlyRootFilesystem=true where compatible.",
    "K8S-SEC-DEFAULT-SA": "Create dedicated service accounts with minimal permissions.",
    "K8S-SEC-RBAC-WILDCARD": "Replace wildcard RBAC rules with explicit resources and verbs.",
    "K8S-SEC-RBAC-CLUSTER-ADMIN": "Avoid binding cluster-admin; use scoped Roles.",
    "K8S-SEC-EXPOSED-LB": "Restrict LoadBalancer exposure and use NetworkPolicies.",
    "K8S-SEC-INGRESS-TLS": "Enable TLS on Ingress resources.",
    "K8S-SCALE-002": "Define resource limits for CPU and memory.",
    "K8S-SCALE-003": "Define resource requests for scheduling stability.",
    "K8S-REL-001": "Add liveness and readiness probes.",
    "K8S-SEC-TAG": "Pin images to immutable tags or digests.",
    "K8S-SCALE-001": "Run at least 2 replicas for availability.",
}


def _container_spec(pod: Any, name: str) -> Any | None:
    for c in pod.spec.containers or []:
        if c.name == name:
            return c
    return None


def _finding(
    rule_id: str,
    title: str,
    description: str,
    severity: str,
    namespace: str,
    resource: str,
    container: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "title": title,
        "description": description,
        "severity": severity,
        "namespace": namespace,
        "resource": resource,
        "container": container,
        "evidence": evidence or {},
        "recommendation": REMEDIATION.get(rule_id, "Review and remediate according to Kubernetes best practices."),
        "remediation": REMEDIATION.get(rule_id, "Review and remediate according to Kubernetes best practices."),
    }


def analyze_cluster_security(
    pods: list[Any],
    deployments: list[Any],
    services: list[Any] | None = None,
    ingresses: list[Any] | None = None,
    rbac_api: Any | None = None,
) -> list[dict[str, Any]]:
    """Analyze live cluster objects for security misconfigurations."""
    findings: list[dict[str, Any]] = []
    services = services or []
    ingresses = ingresses or []

    for pod in pods:
        ns = pod.metadata.namespace
        pod_name = pod.metadata.name
        sa = pod.spec.service_account_name or "default"

        if sa == "default":
            findings.append(
                _finding(
                    "K8S-SEC-DEFAULT-SA",
                    "Pod uses default service account",
                    "Workloads should use dedicated service accounts with scoped permissions.",
                    "low",
                    ns,
                    f"Pod/{pod_name}",
                )
            )

        for cs in pod.status.container_statuses or []:
            container = _container_spec(pod, cs.name)
            if not container:
                continue

            sc = container.security_context
            spec_sc = pod.spec.security_context

            if sc and sc.privileged:
                findings.append(
                    _finding(
                        "K8S-SEC-PRIV",
                        "Privileged container detected",
                        "Container runs with privileged=true which grants host-level access.",
                        "high",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            if sc and sc.allow_privilege_escalation is True:
                findings.append(
                    _finding(
                        "K8S-SEC-ALLOW-PRIV-ESC",
                        "allowPrivilegeEscalation enabled",
                        "Container can gain more privileges than its parent process.",
                        "medium",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            if sc and sc.read_only_root_filesystem is False:
                findings.append(
                    _finding(
                        "K8S-SEC-READONLY-ROOTFS",
                        "Writable root filesystem",
                        "Container root filesystem is writable; prefer readOnlyRootFilesystem=true.",
                        "low",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            caps = (sc.capabilities.add if sc and sc.capabilities else None) or []
            dangerous = {"SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "DAC_READ_SEARCH"}
            bad_caps = [c for c in caps if c in dangerous or c == "*"]
            if bad_caps:
                findings.append(
                    _finding(
                        "K8S-SEC-CAP",
                        "Dangerous Linux capabilities",
                        f"Container adds high-risk capabilities: {', '.join(bad_caps)}",
                        "high",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                        {"capabilities": bad_caps},
                    )
                )

            run_as_user = (sc.run_as_user if sc else None) or (spec_sc.run_as_user if spec_sc else None)
            if run_as_user == 0:
                findings.append(
                    _finding(
                        "K8S-SEC-ROOT",
                        "Container running as root",
                        "Container UID 0 can increase blast radius on compromise.",
                        "high",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            if pod.spec.host_network:
                findings.append(
                    _finding(
                        "K8S-SEC-HOSTNET",
                        "Pod uses hostNetwork",
                        "Pod shares the host network namespace.",
                        "medium",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            if pod.spec.host_pid:
                findings.append(
                    _finding(
                        "K8S-SEC-HOSTPID",
                        "Pod uses hostPID",
                        "Pod can observe host processes.",
                        "medium",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            for vol in pod.spec.volumes or []:
                if vol.host_path:
                    findings.append(
                        _finding(
                            "K8S-SEC-HOSTPATH",
                            "Pod mounts hostPath volume",
                            f"hostPath mount exposes host filesystem at {vol.host_path.path}",
                            "medium",
                            ns,
                            f"Pod/{pod_name}",
                            cs.name,
                            {"path": vol.host_path.path},
                        )
                    )

            if not container.resources or not container.resources.limits:
                findings.append(
                    _finding(
                        "K8S-SCALE-002",
                        "Missing resource limits",
                        "No CPU/memory limits defined for container.",
                        "medium",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            if not container.resources or not container.resources.requests:
                findings.append(
                    _finding(
                        "K8S-SCALE-003",
                        "Missing resource requests",
                        "No CPU/memory requests defined for scheduling.",
                        "low",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            if not container.liveness_probe and not container.readiness_probe:
                findings.append(
                    _finding(
                        "K8S-REL-001",
                        "Missing health probes",
                        "No liveness/readiness probes configured.",
                        "medium",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                    )
                )

            image = container.image or ""
            if ":" not in image or image.endswith(":latest"):
                findings.append(
                    _finding(
                        "K8S-SEC-TAG",
                        "Container uses latest or untagged image",
                        f"Image {image} is not pinned to an immutable tag or digest.",
                        "low",
                        ns,
                        f"Pod/{pod_name}",
                        cs.name,
                        {"image": image},
                    )
                )

    for dep in deployments:
        ns = dep.metadata.namespace
        name = dep.metadata.name
        if (dep.spec.replicas or 0) == 1:
            findings.append(
                _finding(
                    "K8S-SCALE-001",
                    "Deployment has single replica",
                    "Single-replica deployments reduce availability during disruptions.",
                    "low",
                    ns,
                    f"Deployment/{name}",
                )
            )

    for svc in services:
        ns = svc.metadata.namespace
        name = svc.metadata.name
        if svc.spec.type == "LoadBalancer":
            findings.append(
                _finding(
                    "K8S-SEC-EXPOSED-LB",
                    "LoadBalancer service exposed",
                    "Service is externally reachable via cloud load balancer.",
                    "medium",
                    ns,
                    f"Service/{name}",
                    evidence={"type": svc.spec.type},
                )
            )

    for ing in ingresses:
        ns = ing.metadata.namespace
        name = ing.metadata.name
        tls_hosts = set()
        for tls in ing.spec.tls or []:
            tls_hosts.update(tls.hosts or [])
        hosts = [r.host for r in (ing.spec.rules or []) if r.host]
        if hosts and not tls_hosts:
            findings.append(
                _finding(
                    "K8S-SEC-INGRESS-TLS",
                    "Ingress without TLS",
                    f"Ingress exposes hosts without TLS: {', '.join(hosts[:3])}",
                    "medium",
                    ns,
                    f"Ingress/{name}",
                    evidence={"hosts": hosts[:5]},
                )
            )

    if rbac_api:
        findings.extend(_analyze_rbac(rbac_api))

    return findings[:300]


def _analyze_rbac(rbac_api: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        cluster_roles = rbac_api.list_cluster_role(_request_timeout=15).items
        for cr in cluster_roles:
            for rule in cr.rules or []:
                verbs = set(rule.verbs or [])
                resources = rule.resources or []
                if "*" in verbs or "*" in resources:
                    findings.append(
                        _finding(
                            "K8S-SEC-RBAC-WILDCARD",
                            "Wildcard RBAC rule detected",
                            f"ClusterRole {cr.metadata.name} contains wildcard permissions.",
                            "high",
                            "",
                            f"ClusterRole/{cr.metadata.name}",
                            evidence={"verbs": list(verbs), "resources": list(resources)},
                        )
                    )
                if cr.metadata.name == "cluster-admin" and rule.verbs and "get" in verbs:
                    pass  # expected for cluster-admin definition

        bindings = rbac_api.list_cluster_role_binding(_request_timeout=15).items
        for binding in bindings:
            if binding.role_ref.name == "cluster-admin":
                for subject in binding.subjects or []:
                    findings.append(
                        _finding(
                            "K8S-SEC-RBAC-CLUSTER-ADMIN",
                            "cluster-admin binding detected",
                            f"Subject {subject.kind}/{subject.name} bound to cluster-admin.",
                            "high",
                            subject.namespace or "",
                            f"ClusterRoleBinding/{binding.metadata.name}",
                            evidence={
                                "subject": f"{subject.kind}/{subject.name}",
                            },
                        )
                    )
    except Exception:
        pass
    return findings
