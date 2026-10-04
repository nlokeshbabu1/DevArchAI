"""Tests for Kubernetes upgrade readiness engine."""

from __future__ import annotations

from app.kubernetes.api_compatibility import analyze_api_compatibility, scan_resource_api_versions
from app.kubernetes.crd_analyzer import analyze_crds
from app.kubernetes.upgrade_readiness import (
    analyze_upgrade_readiness,
    build_upgrade_plan,
    build_what_could_break,
    explain_version_risk,
)


def test_scan_deprecated_ingress_api():
    resources = [
        {"api_version": "networking.k8s.io/v1beta1", "kind": "Ingress", "namespace": "default", "name": "web"},
        {"api_version": "apps/v1", "kind": "Deployment", "namespace": "default", "name": "api"},
    ]
    scanned = scan_resource_api_versions(resources)
    ingress = next(s for s in scanned if "Ingress" in s["api"])
    assert ingress["affected_count"] == 1
    assert ingress["deprecated"] is True


def test_api_compatibility_blocking_for_removed_api():
    resources = [
        {"api_version": "networking.k8s.io/v1beta1", "kind": "Ingress", "namespace": "ns", "name": "ing"},
    ]
    scanned = scan_resource_api_versions(resources)
    result = analyze_api_compatibility(
        current_version="v1.30.0",
        target_version="v1.34",
        discovered_apis=scanned,
    )
    assert result["blocking_count"] >= 1
    assert not result["compatible"]


def test_api_compatibility_compatible_when_no_deprecated():
    resources = [
        {"api_version": "apps/v1", "kind": "Deployment", "namespace": "ns", "name": "dep"},
    ]
    scanned = scan_resource_api_versions(resources)
    result = analyze_api_compatibility(
        current_version="v1.30.0",
        target_version="v1.34",
        discovered_apis=scanned,
    )
    assert result["compatible"] is True
    assert result["blocking_count"] == 0


def test_crd_analyzer_high_risk_beta_storage():
    crds = [{
        "name": "widgets.example.com",
        "group": "example.com",
        "versions": ["v1beta1"],
        "served_versions": ["v1beta1"],
        "storage_version": "v1beta1",
        "conversion_strategy": "None",
        "instance_count": 14,
    }]
    result = analyze_crds(crds, target_version="v1.34")
    assert result["high_risk_count"] >= 1
    assert result["crds"][0]["risk"] in ("high", "warning", "blocking")


def test_upgrade_readiness_full_analysis():
    discovery = {
        "api_resources": [
            {"api_version": "apps/v1", "kind": "Deployment", "namespace": "default", "name": "api"},
            {"api_version": "batch/v1beta1", "kind": "CronJob", "namespace": "default", "name": "backup"},
        ],
        "crds": [],
        "webhooks": [{"type": "Validating", "name": "test"}],
        "workloads": {"deployments": 1, "statefulsets": 0, "daemonsets": 0, "jobs": 0, "cronjobs": 1},
        "ingress_count": 0,
        "persistent_volume_claims": [],
        "network_policies": [],
    }
    result = analyze_upgrade_readiness(
        current_version="v1.30.0",
        target_version="v1.34",
        discovery=discovery,
    )
    assert result["readiness_score"] >= 0
    assert result["readiness_score"] <= 100
    assert len(result["upgrade_path_versions"]) == 4
    assert result["upgrade_path"]
    assert result["what_could_break"]["categories"]
    assert result["upgrade_plan"]["phases"]


def test_upgrade_path_steps_v130_to_v134():
    discovery = {"api_resources": [], "crds": [], "webhooks": [], "workloads": {}, "ingress_count": 0}
    result = analyze_upgrade_readiness(
        current_version="v1.30.0",
        target_version="v1.34",
        discovery=discovery,
    )
    versions = result["upgrade_path_versions"]
    assert versions == ["v1.31", "v1.32", "v1.33", "v1.34"]


def test_explain_version_risk():
    discovery = {"api_resources": [], "crds": [], "webhooks": [], "workloads": {}, "ingress_count": 0}
    result = analyze_upgrade_readiness(
        current_version="v1.30.0",
        target_version="v1.34",
        discovery=discovery,
    )
    explanation = explain_version_risk(result, "v1.32")
    assert explanation["target_version"] == "v1.32"
    assert "status" in explanation


def test_build_what_could_break_categories():
    api_compat = {
        "blocking": [{"api": "batch/v1beta1/CronJob", "affected_count": 2, "kind": "CronJob"}],
        "warnings": [],
    }
    crd_analysis = {"crds": [], "warnings": [], "blocking": []}
    discovery = {"webhooks": [{"name": "wh1"}], "workloads": {"deployments": 3}, "ingress_count": 0}
    result = build_what_could_break(
        api_compat=api_compat,
        crd_analysis=crd_analysis,
        discovery=discovery,
    )
    categories = {c["category"] for c in result["categories"]}
    assert "apis" in categories
    assert "webhooks" in categories


def test_build_upgrade_plan_phases():
    plan = build_upgrade_plan(
        blocking_apis=[{"api": "batch/v1beta1/CronJob", "affected_count": 1}],
        crd_warnings=[],
        upgrade_path=[{"to_version": "v1.31", "status": "warning"}],
    )
    assert plan["total_phases"] >= 3
    assert plan["phases"][0]["title"] == "Fix deprecated APIs"
