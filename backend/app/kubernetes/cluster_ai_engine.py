"""Kubernetes cluster AI engine — reuses DevArchAI RAG/MCP/LLM pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from app.ai.context_engine import (
    AIContextEngine,
    AIRecommendation,
    StaticRecommendationBuilder,
    is_llm_rate_limited,
)
from app.config import settings
from app.kubernetes.cache import get_cluster_cache
from app.kubernetes.cluster_context_builder import build_cluster_ai_context, build_incident_context

logger = structlog.get_logger(__name__)

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}


@dataclass
class ClusterFinding:
    """Normalized finding for cluster AI analysis."""

    rule_id: str
    title: str
    severity: str
    namespace: str
    resource: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    technology: str = "kubernetes"

    def fingerprint(self) -> str:
        raw = json.dumps(
            {
                "rule_id": self.rule_id,
                "namespace": self.namespace,
                "resource": self.resource,
                "title": self.title,
                "evidence": self.evidence,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def as_finding_proxy(self) -> Any:
        """Minimal object compatible with AIContextEngine."""

        class _Proxy:
            pass

        p = _Proxy()
        p.rule_id = self.rule_id
        p.rule_name = self.title
        p.description = self.description
        p.severity = self.severity
        p.category = "security"
        p.technology = self.technology
        p.file_path = f"{self.namespace}/{self.resource}"
        p.line_number = 0
        return p


@dataclass
class ClusterAIResult:
    summary: str
    recommendations: list[dict[str, Any]]
    finding_count: int
    recommendation_count: int
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "recommendations": self.recommendations,
            "finding_count": self.finding_count,
            "recommendation_count": self.recommendation_count,
            "sources": self.sources,
            "generated_at": datetime.now(UTC).isoformat(),
        }


class ClusterAIEngine:
    """Cache → RAG → MCP → LLM pipeline for Kubernetes cluster findings."""

    def __init__(self) -> None:
        self._context_engine = AIContextEngine()
        self._cache = get_cluster_cache()
        self._static_builder = StaticRecommendationBuilder()

    async def analyze_findings(
        self,
        findings: list[dict[str, Any]],
        snapshot: dict[str, Any],
        *,
        max_findings: int = 10,
        max_llm_calls: int | None = None,
    ) -> ClusterAIResult:
        normalized = self._normalize_findings(findings, snapshot)
        normalized.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity.lower(), 99))
        recommendations: list[dict[str, Any]] = []
        sources: set[str] = set()
        llm_budget = max_llm_calls if max_llm_calls is not None else settings.K8S_AI_MAX_LLM_CALLS
        llm_used = 0

        for finding in normalized[:max_findings]:
            use_llm = llm_used < llm_budget and not is_llm_rate_limited()
            rec, llm_called = await self._analyze_single(finding, snapshot, use_llm=use_llm)
            if llm_called:
                llm_used += 1
            recommendations.append(rec)
            if rec.get("source"):
                sources.add(str(rec["source"]))

        summary = self._build_summary(snapshot, normalized, recommendations)
        return ClusterAIResult(
            summary=summary,
            recommendations=recommendations,
            finding_count=len(normalized),
            recommendation_count=len(recommendations),
            sources=sorted(sources),
        )

    def _normalize_findings(
        self,
        security_findings: list[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> list[ClusterFinding]:
        items: list[ClusterFinding] = []
        for f in security_findings:
            items.append(
                ClusterFinding(
                    rule_id=str(f.get("rule_id", "K8S-UNKNOWN")),
                    title=str(f.get("title", "Kubernetes finding")),
                    severity=str(f.get("severity", "medium")),
                    namespace=str(f.get("namespace", "")),
                    resource=str(f.get("resource", "")),
                    description=str(f.get("description", f.get("title", ""))),
                    evidence=dict(f.get("evidence") or {}),
                )
            )

        for pod in snapshot.get("pods", []):
            reason = pod.get("status_reason") or pod.get("status")
            if reason in ("CrashLoopBackOff", "OOMKilled", "ImagePullBackOff", "ErrImagePull", "Failed"):
                items.append(
                    ClusterFinding(
                        rule_id="K8S-AIOPS-POD",
                        title=f"Pod issue: {reason}",
                        severity="high" if reason in ("CrashLoopBackOff", "OOMKilled") else "medium",
                        namespace=str(pod.get("namespace", "")),
                        resource=f"Pod/{pod.get('name')}",
                        description=f"Pod {pod.get('name')} in state {reason}",
                        evidence={
                            "restart_count": pod.get("restart_count"),
                            "node": pod.get("node"),
                        },
                    )
                )
        return items

    def _payload_from_recommendation(
        self,
        finding: ClusterFinding,
        recommendation: AIRecommendation,
    ) -> dict[str, Any]:
        return {
            "finding": finding.title,
            "rule_id": finding.rule_id,
            "resource": finding.resource,
            "namespace": finding.namespace,
            "issue": recommendation.summary or finding.title,
            "evidence": [finding.description, *list(finding.evidence.values())],
            "likely_cause": recommendation.ai_explanation,
            "recommendation": recommendation.fix_example or recommendation.summary,
            "impact": recommendation.impact or finding.severity,
            "confidence": recommendation.confidence,
            "suggested_next_steps": recommendation.best_practices or [],
            "source": recommendation.source,
            "why_it_matters": recommendation.risk,
        }

    async def _analyze_single(
        self,
        finding: ClusterFinding,
        snapshot: dict[str, Any],
        *,
        use_llm: bool = True,
    ) -> tuple[dict[str, Any], bool]:
        fp = finding.fingerprint()
        cached = await self._cache.get_recommendation(finding.rule_id, fp)
        if cached:
            cached["source"] = "cache"
            cached["finding"] = finding.title
            cached["resource"] = finding.resource
            cached["namespace"] = finding.namespace
            return cached, False

        proxy = finding.as_finding_proxy()

        if not use_llm or is_llm_rate_limited():
            recommendation = self._static_builder.build(proxy, fp)
            recommendation.source = "deterministic"
            payload = self._payload_from_recommendation(finding, recommendation)
            await self._cache.set_recommendation(finding.rule_id, fp, payload)
            return payload, False

        context = await self._context_engine.build_context(
            proxy,
            file_snippet=json.dumps(finding.evidence, default=str)[:1500],
        )

        recommendation: AIRecommendation = await self._context_engine.generate_recommendation(
            proxy,
            context,
            fp,
        )

        payload = self._payload_from_recommendation(finding, recommendation)
        await self._cache.set_recommendation(finding.rule_id, fp, payload)
        return payload, True

    def _build_summary(
        self,
        snapshot: dict[str, Any],
        findings: list[ClusterFinding],
        recommendations: list[dict[str, Any]],
    ) -> str:
        overview = snapshot.get("overview", {})
        health = snapshot.get("health_score", {})
        return (
            f"Cluster {snapshot.get('cluster_name')} analysis complete. "
            f"Health score: {health.get('overall', 'n/a')}. "
            f"{len(findings)} findings analyzed, {len(recommendations)} recommendations generated."
        )

    def _severity_bucket(self, severity: str) -> str:
        s = severity.lower()
        if s in ("critical", "high"):
            return "critical" if s == "critical" else "high"
        if s == "medium":
            return "medium"
        return "informational"

    def _compute_dimension_scores(self, snapshot: dict[str, Any]) -> dict[str, int]:
        health = snapshot.get("health_score", {}) or {}
        overview = snapshot.get("overview", {}) or {}
        pods = overview.get("pods", {})
        nodes = overview.get("nodes", {})
        deployments = overview.get("deployments", {})

        reliability = 100
        if pods.get("crash_loop_back_off", 0):
            reliability -= min(40, pods["crash_loop_back_off"] * 10)
        if pods.get("pending", 0):
            reliability -= min(20, pods["pending"] * 2)
        if nodes.get("not_ready", 0):
            reliability -= min(30, nodes["not_ready"] * 15)
        if deployments.get("degraded", 0):
            reliability -= min(25, deployments["degraded"] * 5)

        security = int(health.get("security", health.get("overall", 80)) or 80)
        configuration = int(health.get("configuration", health.get("overall", 80)) or 80)
        upgrade_readiness = int(
            (snapshot.get("version_advisor") or {}).get("readiness_score")
            or health.get("upgrade", health.get("overall", 75))
            or 75
        )

        overall = max(0, min(100, int(
            (reliability + security + configuration + upgrade_readiness) / 4
        )))

        return {
            "overall": overall,
            "reliability": max(0, min(100, reliability)),
            "security": max(0, min(100, security)),
            "configuration": max(0, min(100, configuration)),
            "upgrade_readiness": max(0, min(100, upgrade_readiness)),
        }

    async def run_copilot_analysis(
        self,
        snapshot: dict[str, Any],
        *,
        max_findings: int = 15,
    ) -> dict[str, Any]:
        """Evidence-based Kubernetes AI Copilot analysis."""
        context = build_cluster_ai_context(snapshot)
        findings = self._normalize_findings(snapshot.get("security_findings", []), snapshot)
        scores = self._compute_dimension_scores(snapshot)

        ai_result = await self.analyze_findings(
            snapshot.get("security_findings", []),
            snapshot,
            max_findings=max_findings,
            max_llm_calls=settings.K8S_AI_MAX_LLM_CALLS,
        )

        by_severity: dict[str, list[dict[str, Any]]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "informational": [],
        }

        for rec in ai_result.recommendations:
            bucket = self._severity_bucket(str(rec.get("impact", "medium")))
            by_severity[bucket].append({
                "title": rec.get("finding") or rec.get("issue"),
                "severity": bucket,
                "confidence": rec.get("confidence", "medium"),
                "affected_resource": rec.get("resource"),
                "namespace": rec.get("namespace"),
                "evidence": rec.get("evidence", []),
                "explanation": rec.get("likely_cause") or rec.get("issue"),
                "recommended_action": rec.get("recommendation"),
                "remediation": rec.get("suggested_next_steps", []),
                "source": rec.get("source"),
                "rule_id": rec.get("rule_id"),
            })

        return {
            "summary": ai_result.summary,
            "health_scores": scores,
            "findings_by_severity": by_severity,
            "recommendations": ai_result.recommendations,
            "finding_count": ai_result.finding_count,
            "recommendation_count": ai_result.recommendation_count,
            "sources": ai_result.sources,
            "cluster_context": context,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    async def run_troubleshoot(
        self,
        snapshot: dict[str, Any],
        question: str,
    ) -> dict[str, Any]:
        """Investigate a cluster problem using deterministic evidence + AI."""
        q = question.lower()
        pods = snapshot.get("pods", [])
        deployments = snapshot.get("deployments", [])
        events = snapshot.get("events", [])
        services = snapshot.get("services", [])

        matched_pods = [
            p for p in pods
            if q in str(p.get("name", "")).lower()
            or q in str(p.get("namespace", "")).lower()
        ]
        matched_deployments = [
            d for d in deployments
            if q in str(d.get("name", "")).lower()
        ]

        target_pod = None
        if matched_pods:
            target_pod = matched_pods[0]
        elif matched_deployments:
            dep_name = matched_deployments[0].get("name")
            target_pod = next(
                (p for p in pods if p.get("name", "").startswith(str(dep_name))),
                None,
            )

        related_events = [
            e for e in events
            if target_pod and (
                str(target_pod.get("name", "")) in str(e.get("resource", ""))
                or str(target_pod.get("namespace", "")) == str(e.get("namespace", ""))
            )
        ][:20]

        incident = build_incident_context(
            pod=target_pod,
            related_events=related_events,
            snapshot=snapshot,
        )

        findings: list[ClusterFinding] = []
        if target_pod:
            reason = target_pod.get("status_reason") or target_pod.get("status")
            findings.append(
                ClusterFinding(
                    rule_id="K8S-TROUBLESHOOT",
                    title=f"Troubleshooting: {target_pod.get('name')} ({reason})",
                    severity="high",
                    namespace=str(target_pod.get("namespace", "")),
                    resource=f"Pod/{target_pod.get('name')}",
                    description=question,
                    evidence={
                        "status": reason,
                        "restart_count": target_pod.get("restart_count"),
                        "node": target_pod.get("node"),
                        "events": [e.get("message") for e in related_events[:5]],
                    },
                )
            )
        else:
            problem_pods = [
                p for p in pods
                if p.get("status_reason") in (
                    "CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "Pending",
                )
            ][:5]
            for p in problem_pods:
                findings.append(
                    ClusterFinding(
                        rule_id="K8S-TROUBLESHOOT",
                        title=f"Pod issue: {p.get('status_reason')}",
                        severity="medium",
                        namespace=str(p.get("namespace", "")),
                        resource=f"Pod/{p.get('name')}",
                        description=question,
                        evidence={"status": p.get("status_reason")},
                    )
                )

        recommendations = []
        for idx, finding in enumerate(findings[:3]):
            # Troubleshoot: only the primary finding uses LLM (1 call max).
            rec, _ = await self._analyze_single(finding, snapshot, use_llm=(idx == 0))
            recommendations.append({
                **rec,
                "root_cause": rec.get("likely_cause"),
                "confidence": rec.get("confidence", "medium"),
                "evidence": list(finding.evidence.values()) + related_events[:3],
                "recommended_fix": rec.get("recommendation"),
            })

        root_cause = recommendations[0].get("root_cause") if recommendations else (
            "No matching workload found — review cluster events and pod status"
        )

        return {
            "question": question,
            "root_cause": root_cause,
            "confidence": recommendations[0].get("confidence", "low") if recommendations else "low",
            "evidence": incident,
            "matched_resources": {
                "pods": matched_pods[:5],
                "deployments": matched_deployments[:5],
                "services": [
                    s for s in services
                    if q in str(s.get("name", "")).lower()
                ][:5],
            },
            "recommendations": recommendations,
            "recommended_fix": recommendations[0].get("recommended_fix") if recommendations else None,
            "generated_at": datetime.now(UTC).isoformat(),
        }


_cluster_ai_engine: ClusterAIEngine | None = None


def get_cluster_ai_engine() -> ClusterAIEngine:
    global _cluster_ai_engine
    if _cluster_ai_engine is None:
        _cluster_ai_engine = ClusterAIEngine()
    return _cluster_ai_engine
