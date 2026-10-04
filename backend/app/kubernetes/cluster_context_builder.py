"""Build structured Kubernetes context for AI analysis."""

from __future__ import annotations

from typing import Any


def build_cluster_ai_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Structured, redacted cluster context for LLM — no secrets."""
    overview = snapshot.get("overview", {})
    pods = snapshot.get("pods", [])
    events = snapshot.get("events", [])
    security = snapshot.get("security_findings", [])

    problem_pods = [
        p for p in pods
        if p.get("status_reason") in ("CrashLoopBackOff", "OOMKilled", "ImagePullBackOff", "ErrImagePull")
        or p.get("status") in ("Failed", "Pending")
    ][:20]

    priority_events = [e for e in events if e.get("priority")][:30]

    return {
        "cluster_metadata": {
            "name": snapshot.get("cluster_name"),
            "provider": snapshot.get("provider"),
            "version": snapshot.get("kubernetes_version"),
            "region": snapshot.get("region"),
            "status": snapshot.get("status"),
        },
        "overview": overview,
        "problem_pods": problem_pods,
        "priority_events": priority_events,
        "security_findings": security[:30],
        "health_score": snapshot.get("health_score"),
        "version_advisor": snapshot.get("version_advisor"),
        "nodes_summary": {
            "total": overview.get("nodes", {}).get("total"),
            "ready": overview.get("nodes", {}).get("ready"),
            "not_ready": overview.get("nodes", {}).get("not_ready"),
        },
    }


def build_incident_context(
    *,
    pod: dict[str, Any] | None,
    related_events: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Correlate pod state, events, and cluster context for AIOps."""
    node_name = pod.get("node") if pod else None
    node = next((n for n in snapshot.get("nodes", []) if n.get("name") == node_name), None)

    return {
        "pod": pod,
        "events": related_events,
        "node": node,
        "cluster_overview": snapshot.get("overview"),
        "security_findings_for_pod": [
            f for f in snapshot.get("security_findings", [])
            if pod and f.get("resource", "").endswith(pod.get("name", ""))
        ],
    }
