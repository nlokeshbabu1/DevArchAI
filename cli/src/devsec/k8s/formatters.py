"""Rich formatters for Kubernetes CLI output."""

from __future__ import annotations

from typing import Any

from rich.table import Table

from devsec.output.console import get_console, print_muted, print_success, print_warning


def _short_id(value: str) -> str:
    return value[:8] if len(value) > 8 else value


def _provider_label(conn: dict[str, Any]) -> str:
    kind = conn.get("kind", "generic")
    if kind == "eks":
        return "AWS / EKS"
    if kind == "aks":
        return "Azure / AKS"
    if kind == "gke":
        return "GCP / GKE"
    return "On-Prem / kubeconfig"


def _status_label(conn: dict[str, Any]) -> str:
    status = conn.get("health_status") or conn.get("status") or "unknown"
    if status == "connected":
        return "✓ Healthy"
    if status in ("degraded", "permission_denied"):
        return "⚠ Degraded"
    if status in ("disconnected", "error", "unreachable", "auth_failed"):
        return "✗ Unhealthy"
    return status


def render_clusters_table(clusters: list[dict[str, Any]]) -> Table:
    table = Table(title="Kubernetes Clusters", show_lines=False, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Provider")
    table.add_column("Version", no_wrap=True)
    table.add_column("Nodes", justify="right", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("ID", style="dim", no_wrap=True)
    for conn in clusters:
        if not conn.get("is_active", True):
            continue
        table.add_row(
            conn.get("cluster_name") or conn.get("name", "?"),
            _provider_label(conn),
            conn.get("kubernetes_version") or "-",
            str(conn.get("node_count") if conn.get("node_count") is not None else "-"),
            _status_label(conn),
            _short_id(str(conn.get("id", ""))),
        )
    return table


def render_checklist(checks: dict[str, bool], title: str = "Validation") -> None:
    console = get_console()
    console.print(f"\n[bold]{title}[/bold]")
    for label, ok in checks.items():
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {mark} {label.replace('_', ' ').title()}")


def render_cluster_summary(conn: dict[str, Any]) -> None:
    console = get_console()
    console.print(f"\n[bold]Cluster:[/bold] {conn.get('cluster_name') or conn.get('name')}")
    if conn.get("kubernetes_version"):
        console.print(f"  Version: {conn['kubernetes_version']}")
    if conn.get("node_count") is not None:
        console.print(f"  Nodes: {conn['node_count']}")
    if conn.get("pod_count") is not None:
        console.print(f"  Pods: {conn['pod_count']}")
    console.print(f"  Connection ID: {conn.get('id')}")


def render_health_score(score: dict[str, Any]) -> None:
    console = get_console()
    overall = score.get("overall", "—")
    console.print(f"\n[bold]Cluster Health Score:[/bold] {overall}/100")
    sub = score.get("sub_scores") or {}
    if sub:
        table = Table(show_header=True, header_style="bold", show_lines=False)
        table.add_column("Category")
        table.add_column("Score", justify="right")
        for key, val in sub.items():
            table.add_row(key.replace("_", " ").title(), str(val))
        console.print(table)


def render_security_findings(findings: list[dict[str, Any]]) -> None:
    if not findings:
        print_success("No security findings detected.")
        return
    table = Table(title="Security Findings", header_style="bold cyan")
    table.add_column("Severity", no_wrap=True)
    table.add_column("Rule")
    table.add_column("Namespace")
    table.add_column("Resource")
    table.add_column("Title")
    for f in findings[:50]:
        sev = str(f.get("severity", "medium")).upper()
        table.add_row(
            sev,
            str(f.get("rule_id", "-")),
            str(f.get("namespace", "-")),
            str(f.get("resource", "-")),
            str(f.get("title", f.get("description", "-")))[:60],
        )
    get_console().print(table)
    if len(findings) > 50:
        print_muted(f"... and {len(findings) - 50} more findings")


def render_version_advisor(advisor: dict[str, Any]) -> None:
    console = get_console()
    console.print(f"\n[bold]Version Advisor[/bold]")
    console.print(f"  Current:     {advisor.get('current_version', '—')}")
    console.print(f"  Recommended: {advisor.get('recommended_version', '—')}")
    console.print(f"  Status:      {advisor.get('upgrade_status', '—')}")
    console.print(f"  Impact:      {advisor.get('impact_summary', '—')}")
    seq = advisor.get("recommended_sequence") or []
    if seq:
        console.print("  Upgrade path:")
        for v in seq:
            console.print(f"    → {v}")


def render_resource_table(
    title: str,
    items: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> None:
    if not items:
        print_muted(f"No {title.lower()} found.")
        return
    table = Table(title=title, header_style="bold cyan")
    for header, _ in columns:
        table.add_column(header)
    for item in items[:100]:
        table.add_row(*(str(item.get(key, "—")) for _, key in columns))
    get_console().print(table)
    if len(items) > 100:
        print_muted(f"... and {len(items) - 100} more")


def render_ai_recommendations(result: dict[str, Any]) -> None:
    console = get_console()
    if result.get("summary"):
        console.print(f"\n[bold]{result['summary']}[/bold]")
    recs = result.get("recommendations") or []
    if not recs:
        print_success("No issues requiring AI recommendations.")
        return
    for rec in recs:
        console.print(f"\n[bold cyan]{rec.get('finding') or rec.get('issue')}[/bold cyan]")
        console.print(f"  Issue:          {rec.get('issue', '—')}")
        console.print(f"  Likely cause:   {rec.get('likely_cause', '—')}")
        console.print(f"  Recommendation: {rec.get('recommendation', '—')}")
        console.print(f"  Impact: {rec.get('impact', '—')}  Confidence: {rec.get('confidence', '—')}")


def render_overview(data: dict[str, Any]) -> None:
    conn = data.get("connection") or {}
    overview = data.get("overview") or {}
    render_cluster_summary(conn)
    nodes = overview.get("nodes") or {}
    pods = overview.get("pods") or {}
    console = get_console()
    console.print(f"\n[bold]Overview[/bold]")
    console.print(f"  Nodes:       {nodes.get('total', 0)} ({nodes.get('ready', 0)} ready)")
    console.print(f"  Pods:        {pods.get('total', 0)} ({pods.get('running', 0)} running)")
    console.print(f"  Deployments: {(overview.get('deployments') or {}).get('total', 0)}")
    console.print(f"  Services:    {(overview.get('services') or {}).get('total', 0)}")
    console.print(f"  Namespaces:  {(overview.get('namespaces') or {}).get('total', 0)}")
    if data.get("health_score"):
        render_health_score(data["health_score"])
