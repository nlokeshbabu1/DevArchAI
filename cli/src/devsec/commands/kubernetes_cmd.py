"""Kubernetes cluster commands — ``devsec k8s`` / ``devsec kubernetes``."""

from __future__ import annotations

import time
from typing import Any

import typer

from devsec.api.kubernetes import (
    disconnect_cluster,
    get_ai_job,
    get_deployments,
    get_events,
    get_health_score,
    get_latest_ai,
    get_nodes,
    get_overview,
    get_pods,
    get_services,
    get_upgrade_job,
    list_connections,
    refresh_cluster,
    security_scan,
    start_ai,
    start_upgrade_analysis,
    validate_connection,
    version_advisor,
)
from devsec.commands.base import command, make_client
from devsec.k8s.formatters import (
    render_ai_recommendations,
    render_checklist,
    render_cluster_summary,
    render_clusters_table,
    render_health_score,
    render_overview,
    render_resource_table,
    render_security_findings,
    render_version_advisor,
)
from devsec.k8s.providers import get_provider
from devsec.output.console import get_console, print_muted, print_success, print_warning
from devsec.utils.errors import UsageError

kubernetes_app = typer.Typer(
    help="Kubernetes cluster management and inspection.",
    no_args_is_help=True,
    add_completion=False,
)

_RUNNING_AI = frozenset({
    "queued", "running", "collecting", "checking_cache",
    "rag_retrieving", "mcp_retrieving", "generating",
})


def _pick_connection(connections: list[dict[str, Any]], cluster: str | None) -> dict[str, Any]:
    active = [c for c in connections if c.get("is_active")]
    if not active:
        raise UsageError(
            "No active Kubernetes connections found.",
            hint="Connect a cluster: devsec k8s config --kubeconfig ~/.kube/config",
        )
    if cluster:
        match = next(
            (
                c for c in active
                if c.get("id") == cluster
                or c.get("cluster_name") == cluster
                or c.get("name") == cluster
            ),
            None,
        )
        if not match:
            raise UsageError(f"Cluster not found: {cluster}")
        return match
    return active[0]


def _resolve(client: Any, cluster: str | None) -> dict[str, Any]:
    return _pick_connection(list_connections(client), cluster)


def _poll_ai(client: Any, connection_id: str, job_id: str, watch: bool, json_mode: bool) -> dict[str, Any]:
    if not watch:
        return get_ai_job(client, connection_id, job_id)
    for i in range(60):
        job = get_ai_job(client, connection_id, job_id)
        status = str(job.get("status", ""))
        if not json_mode:
            print_muted(f"AI analysis: {status.upper()}")
        if status in {"completed", "failed"}:
            return job
        time.sleep(3)
    raise UsageError("AI analysis timed out", hint="Check status: devsec k8s troubleshoot --watch")


# ---------------------------------------------------------------------------
# Connection commands
# ---------------------------------------------------------------------------

@kubernetes_app.command("config")
@command
def kubernetes_config(
    kubeconfig: str = typer.Option(..., "--kubeconfig", help="Path to kubeconfig file."),
    context: str | None = typer.Option(None, "--context", help="Kubernetes context name."),
    name: str | None = typer.Option(None, "--name", help="Connection display name."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Configure and connect a cluster via kubeconfig (local / on-premises)."""
    _, client = make_client()
    try:
        provider = get_provider("kubeconfig", kubeconfig=kubeconfig, context=context)
        prereq = provider.validate_prerequisites(client)
        if not json:
            render_checklist(prereq["checks"], "Kubeconfig Validation")
            render_cluster_summary({
                "cluster_name": prereq.get("cluster_name"),
                "kubernetes_version": prereq.get("kubernetes_version"),
                "name": name or prereq.get("cluster_name"),
            })
        conn = provider.connect(client, name or prereq.get("cluster_name") or "cluster")
        if not json:
            print_success(f"Connected: {conn.get('cluster_name') or conn.get('name')}")
            print_muted(f"Connection ID: {conn.get('id')}")
            print_muted("View in Web UI: /kubernetes")
        return {"connection": conn, "validation": prereq}
    finally:
        client.close()


@kubernetes_app.command("connect")
@command
def kubernetes_connect(
    type: str = typer.Option("kubeconfig", "--type", "-t", help="Provider: kubeconfig, eks, aks, gke."),
    kubeconfig: str | None = typer.Option(None, "--kubeconfig", help="Kubeconfig path (kubeconfig type)."),
    context: str | None = typer.Option(None, "--context", help="Kubernetes context."),
    region: str = typer.Option("us-east-1", "--region", help="AWS region (EKS)."),
    cluster_name: str | None = typer.Option(None, "--cluster-name", help="EKS cluster name."),
    name: str | None = typer.Option(None, "--name", help="Connection display name."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Connect a Kubernetes cluster (kubeconfig, EKS, AKS, or GKE)."""
    _, client = make_client()
    try:
        provider = get_provider(
            type,
            kubeconfig=kubeconfig,
            context=context,
            region=region,
            cluster_name=cluster_name,
        )
        if type.lower() in ("eks",):
            prereq = provider.validate_prerequisites(client)
            if not json:
                render_checklist(prereq["checks"], "EKS Prerequisites")
                clusters = prereq.get("clusters") or []
                if clusters and not cluster_name:
                    console = get_console()
                    console.print("\n[bold]Available EKS clusters:[/bold]")
                    for i, c in enumerate(clusters, 1):
                        console.print(f"  {i}. {c.get('name')} ({c.get('version', '?')})")
                    raise UsageError(
                        "Select a cluster with --cluster-name",
                        hint=f"Example: devsec k8s connect --type eks --region {region} --cluster-name {clusters[0].get('name')}",
                    )
        elif type.lower() in ("kubeconfig", "generic", "local"):
            if not kubeconfig:
                raise UsageError("--kubeconfig is required", hint="devsec k8s config --kubeconfig ~/.kube/config")
            prereq = provider.validate_prerequisites(client)
            if not json:
                render_checklist(prereq["checks"], "Validation")
        conn = provider.connect(client, name or cluster_name or "cluster", cluster_name=cluster_name)
        if not json:
            print_success(f"Connected: {conn.get('cluster_name') or conn.get('name')}")
            print_muted(f"Connection ID: {conn.get('id')}")
        return {"connection": conn}
    finally:
        client.close()


@kubernetes_app.command("disconnect")
@command
def kubernetes_disconnect(
    cluster: str = typer.Argument(..., help="Connection id or cluster name."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Disconnect a Kubernetes cluster."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        result = disconnect_cluster(client, conn["id"])
        if not json:
            print_success(f"Disconnected: {conn.get('cluster_name') or conn.get('name')}")
        return {"disconnected": conn["id"], **result}
    finally:
        client.close()


# ---------------------------------------------------------------------------
# List / status / inspect
# ---------------------------------------------------------------------------

@kubernetes_app.command("list")
@command
def kubernetes_list(
    *,
    json: bool = False,
) -> dict[str, Any]:
    """List connected Kubernetes clusters."""
    _, client = make_client()
    try:
        clusters = list_connections(client)
        data = {"clusters": clusters}
        if not json:
            active = [c for c in clusters if c.get("is_active")]
            if active:
                get_console().print(render_clusters_table(active))
                print_muted(f"{len(active)} active connection(s)")
            else:
                print_muted("No clusters connected.")
                print_muted("Connect: devsec k8s config --kubeconfig ~/.kube/config")
        return data
    finally:
        client.close()


@kubernetes_app.command("status")
@command
def kubernetes_status(
    cluster: str | None = typer.Argument(None, help="Connection id or cluster name."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Show connection status for a cluster."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        validated = validate_connection(client, conn["id"])
        data = {"connection": validated}
        if not json:
            render_cluster_summary(validated)
            status = validated.get("health_status") or validated.get("status")
            if status == "connected":
                print_success(f"Status: {status}")
            elif status in ("error", "unreachable", "auth_failed"):
                print_warning(f"Status: {status}")
                if validated.get("error_message"):
                    print_warning(validated["error_message"])
            else:
                print_muted(f"Status: {status}")
        return data
    finally:
        client.close()


@kubernetes_app.command("inspect")
@command
def kubernetes_inspect(
    cluster: str | None = typer.Argument(None, help="Connection id or cluster name."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Inspect cluster overview."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = get_overview(client, conn["id"])
        if not json:
            render_overview(data)
        return data
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Health / security / version
# ---------------------------------------------------------------------------

@kubernetes_app.command("health")
@command
def kubernetes_health(
    cluster: str | None = typer.Argument(None),
    refresh: bool = typer.Option(False, "--refresh", help="Force refresh cluster snapshot."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Show cluster health score (from backend evidence engine)."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        if refresh:
            refresh_cluster(client, conn["id"])
        score = get_health_score(client, conn["id"])
        data = {"health_score": score, "connection_id": conn["id"]}
        if not json:
            render_health_score(score)
            evidence = score.get("evidence") or {}
            for category, items in evidence.items():
                warnings = [e for e in items if isinstance(e, dict) and e.get("severity") in ("high", "medium")]
                if warnings:
                    print_warning(f"{category}: {len(warnings)} issue(s)")
        return data
    finally:
        client.close()


@kubernetes_app.command("security")
@command
def kubernetes_security(
    cluster: str | None = typer.Argument(None),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Run Kubernetes security scan."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = security_scan(client, conn["id"])
        if not json:
            render_security_findings(data.get("findings") or [])
            if data.get("health_score"):
                render_health_score(data["health_score"])
        return data
    finally:
        client.close()


@kubernetes_app.command("version")
@command
def kubernetes_version(
    cluster: str | None = typer.Argument(None),
    target: str | None = typer.Option(None, "--target", help="Target K8s version e.g. v1.34"),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Show Kubernetes version advisor."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = version_advisor(client, conn["id"], target_version=target)
        if not json:
            render_version_advisor(data)
        return data
    finally:
        client.close()


@kubernetes_app.command("advisor")
@command
def kubernetes_advisor(
    cluster: str | None = typer.Argument(None),
    target: str | None = typer.Option(None, "--target", help="Target K8s version e.g. v1.34"),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Show version upgrade advisor (alias for version)."""
    return kubernetes_version(cluster=cluster, target=target, json=json)


upgrade_app = typer.Typer(help="Kubernetes upgrade analysis.", no_args_is_help=True)
kubernetes_app.add_typer(upgrade_app, name="upgrade")


@upgrade_app.command("analyze")
@command
def kubernetes_upgrade_analyze(
    cluster: str | None = typer.Argument(None),
    target: str = typer.Option("v1.34", "--target", help="Target K8s version"),
    wait: bool = typer.Option(False, "--wait", help="Poll until analysis completes."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Run full upgrade readiness analysis against the cluster."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        if not json:
            print_muted(f"Starting upgrade analysis → {target}...")
        job = start_upgrade_analysis(client, conn["id"], target_version=target)
        job_id = job["id"]
        if not json:
            print_muted(f"Analysis job: {job_id[:8]}...")
        if wait or json:
            deadline = time.time() + 300
            while time.time() < deadline:
                result = get_upgrade_job(client, conn["id"], job_id)
                if result.get("status") in ("completed", "failed"):
                    if not json:
                        if result.get("status") == "completed":
                            r = result.get("result") or {}
                            print_success(
                                f"Readiness: {r.get('readiness_score', 'n/a')}/100 "
                                f"({r.get('risk', 'unknown')} risk)"
                            )
                            blocking = r.get("blocking_issues") or []
                            if blocking:
                                print_warning(f"{len(blocking)} blocking issue(s)")
                        else:
                            print_warning(result.get("error_message") or "Analysis failed")
                    return result
                time.sleep(3)
            raise UsageError("Upgrade analysis timed out", hint="Check Web UI for status.")
        return {"job": job, "connection_id": conn["id"]}
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Resource commands
# ---------------------------------------------------------------------------

@kubernetes_app.command("nodes")
@command
def kubernetes_nodes(
    cluster: str | None = typer.Argument(None),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """List cluster nodes."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = get_nodes(client, conn["id"])
        if not json:
            render_resource_table("Nodes", data.get("nodes") or [], [
                ("Name", "name"), ("Status", "status"),
                ("CPU", "cpu_allocatable"), ("Memory", "memory_allocatable"), ("Version", "version"),
            ])
        return data
    finally:
        client.close()


@kubernetes_app.command("pods")
@command
def kubernetes_pods(
    cluster: str | None = typer.Argument(None),
    namespace: str | None = typer.Option(None, "--namespace", "-n"),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """List cluster pods."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = get_pods(client, conn["id"], namespace=namespace)
        if not json:
            render_resource_table("Pods", data.get("pods") or [], [
                ("Namespace", "namespace"), ("Name", "name"),
                ("Status", "status_reason"), ("Node", "node"), ("Restarts", "restart_count"),
            ])
        return data
    finally:
        client.close()


@kubernetes_app.command("workloads")
@command
def kubernetes_workloads(
    cluster: str | None = typer.Argument(None),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """List deployments (workloads)."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = get_deployments(client, conn["id"])
        if not json:
            render_resource_table("Deployments", data.get("deployments") or [], [
                ("Namespace", "namespace"), ("Name", "name"),
                ("Ready", "ready"), ("Available", "available"), ("Replicas", "replicas"),
            ])
        return data
    finally:
        client.close()


@kubernetes_app.command("services")
@command
def kubernetes_services(
    cluster: str | None = typer.Argument(None),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """List cluster services."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = get_services(client, conn["id"])
        if not json:
            render_resource_table("Services", data.get("services") or [], [
                ("Namespace", "namespace"), ("Name", "name"),
                ("Type", "type"), ("Cluster IP", "cluster_ip"),
            ])
        return data
    finally:
        client.close()


@kubernetes_app.command("events")
@command
def kubernetes_events(
    cluster: str | None = typer.Argument(None),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """List cluster events."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        data = get_events(client, conn["id"])
        if not json:
            render_resource_table("Events", data.get("events") or [], [
                ("Namespace", "namespace"), ("Reason", "reason"),
                ("Resource", "resource"), ("Message", "message"),
            ])
        return data
    finally:
        client.close()


# ---------------------------------------------------------------------------
# AI troubleshooting
# ---------------------------------------------------------------------------

@kubernetes_app.command("troubleshoot")
@command
def kubernetes_troubleshoot(
    cluster: str | None = typer.Argument(None),
    question: str | None = typer.Argument(None, help="Natural-language question e.g. 'why is payment-api failing?'"),
    watch: bool = typer.Option(False, "--watch", help="Poll until AI analysis completes."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """AI-assisted cluster troubleshooting (collects evidence, submits to backend AI)."""
    _, client = make_client()
    try:
        conn = _resolve(client, cluster)
        if not json:
            print_muted("Collecting cluster evidence...")
            nodes = get_nodes(client, conn["id"])
            pods = get_pods(client, conn["id"])
            workloads = get_deployments(client, conn["id"])
            services = get_services(client, conn["id"])
            events = get_events(client, conn["id"])
            render_checklist({
                "cluster_connectivity": True,
                "nodes": len(nodes.get("nodes") or []) > 0,
                "pods": len(pods.get("pods") or []) > 0,
                "workloads": len(workloads.get("deployments") or []) >= 0,
                "services": len(services.get("services") or []) >= 0,
                "events": len(events.get("events") or []) >= 0,
            }, "Evidence Collection")
            pod_list = pods.get("pods") or []
            problems = [
                p for p in pod_list
                if str(p.get("status_reason", "")) in (
                    "CrashLoopBackOff", "Pending", "ImagePullBackOff", "ErrImagePull", "Failed",
                )
            ]
            if problems:
                print_warning(f"Problems detected: {len(problems)} pod(s) in unhealthy state")
                for p in problems[:5]:
                    print_muted(f"  {p.get('namespace')}/{p.get('name')}: {p.get('status_reason')}")
        if question:
            job = start_ai(client, conn["id"], question=question, analysis_type="troubleshoot")
        else:
            job = start_ai(client, conn["id"], analysis_type="copilot")
        job_id = job["id"]
        if not json:
            print_muted(f"AI analysis started (job: {job_id[:8]}...)")
            if not watch:
                print_muted("Run with --watch to wait for results, or check Web UI.")
        if watch or json:
            result = _poll_ai(client, conn["id"], job_id, watch, json)
            if not json and result.get("result"):
                render_ai_recommendations(result["result"])
            elif not json and result.get("status") == "failed":
                print_warning(result.get("error_message") or "AI analysis failed")
            return result
        return {"job": job, "connection_id": conn["id"]}
    finally:
        client.close()


@kubernetes_app.command("analyze")
@command
def kubernetes_analyze(
    cluster: str | None = typer.Argument(None),
    wait: bool = typer.Option(False, "--wait", help="Poll until AI analysis completes."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Queue AI analysis (alias for troubleshoot)."""
    return kubernetes_troubleshoot(cluster=cluster, watch=wait, json=json)


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------

@kubernetes_app.command("doctor")
@command
def kubernetes_doctor(
    cluster: str | None = typer.Argument(None, help="Optional cluster to diagnose."),
    kubeconfig: str | None = typer.Option(None, "--kubeconfig", help="Test kubeconfig without connecting."),
    context: str | None = typer.Option(None, "--context"),
    type: str = typer.Option("kubeconfig", "--type", help="Provider type for EKS checks."),
    *,
    json: bool = False,
) -> dict[str, Any]:
    """Diagnose CLI, auth, backend, and cluster connectivity."""
    config, client = make_client()
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    try:
        checks["cli"] = True
        checks["api_url_configured"] = bool(config.api_url)
        try:
            from devsec.api.auth import status as auth_status
            auth = auth_status(config, client)
            checks["authenticated"] = auth.get("authenticated", False)
            details["auth"] = auth
        except Exception:
            checks["authenticated"] = False
        try:
            client.get_json("/health")
            checks["backend_reachable"] = True
        except Exception:
            checks["backend_reachable"] = False
        if kubeconfig:
            provider = get_provider("kubeconfig", kubeconfig=kubeconfig, context=context)
            prereq = provider.validate_prerequisites(client)
            for k, v in prereq.get("checks", {}).items():
                checks[f"kubeconfig_{k}"] = v
            details["kubeconfig_test"] = prereq.get("test_result")
        if cluster:
            conn = _resolve(client, cluster)
            validated = validate_connection(client, conn["id"])
            checks["cluster_validated"] = validated.get("status") == "connected"
            details["connection"] = validated
        if type.lower() == "eks":
            try:
                provider = get_provider("eks", region="us-east-1")
                prereq = provider.validate_prerequisites(client)
                for k, v in prereq.get("checks", {}).items():
                    checks[f"eks_{k}"] = v
                details["eks"] = prereq
            except UsageError as exc:
                checks["eks_available"] = False
                details["eks_error"] = exc.message
        data = {"checks": checks, "details": details}
        if not json:
            render_checklist(checks, "DevArchAI Kubernetes Doctor")
            failed = [k for k, v in checks.items() if not v]
            if failed:
                print_warning(f"{len(failed)} check(s) failed")
            else:
                print_success("All checks passed")
        return data
    finally:
        client.close()
