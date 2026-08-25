"""Regression tests for Technology Coverage aggregation.

Guards the invariant that every technology_details entry satisfies
    total_findings == findings_count == sum(severity_counts.values())
with all five severity buckets always present, and that canonical
technology classification assigns each finding to exactly one card.

Reproduces the reported bug: Kubernetes manifests with misspelled
filenames (backend-deployemt.yaml, statefullset.yaml) were classified as
"code", so 21 real Kubernetes findings vanished from the Kubernetes card
while its severity badges summed to a different number.
"""

from uuid import uuid4

import pytest

from app.models.finding import Category, Finding, Severity
from app.models.scan import Scan, ScanStatus

DEPLOYEMT = "/kubernetes/Backend/backend-deployemt.yaml"
STATEFULLSET = "/kubernetes/DB-Service/statefullset.yaml"
INGRESS = "/helm-chart/ingress.yaml"
DOCKERFILE = "Frontend/Dockerfile"
WORKFLOW_CI = ".github/workflows/ci.yml"
WORKFLOW_BACKEND = ".github/workflows/backend.yml"

DETECTED_STACK = {
    "docker_files": [DOCKERFILE],
    "kubernetes_files": [
        DEPLOYEMT,
        STATEFULLSET,
        INGRESS,
        "/kubernetes/extras/deployment.yaml",
    ],
    "github_actions_files": [WORKFLOW_CI, WORKFLOW_BACKEND],
    "helm_files": ["Chart.yaml", "values.yaml"],
}


def _finding(scan_id, rule_id, severity, category, file_path, scanner_name, rule_name):
    return Finding(
        id=uuid4(),
        scan_id=scan_id,
        rule_id=rule_id,
        rule_name=rule_name,
        severity=severity,
        category=category,
        description=f"{rule_id} detected",
        recommendation="Fix it",
        file_path=file_path,
        summary=f"{rule_id} summary",
        risk="risk",
        impact="impact",
        confidence=0.9,
        scanner_name=scanner_name,
    )


def _seed_findings(scan_id):
    """Mirror the real ECOMMERCE distribution: 29 findings.

    - kubernetes bucket: 22 (19 info + 2 high + 1 medium)
    - docker bucket: 4 (1 high + 1 low + 2 info)
    - github_actions bucket: 3 (1 high + 1 medium + 1 info)
    """
    findings = []
    # 14 INFO Checkov on the misspelled deployment manifest
    for i in range(14):
        findings.append(_finding(
            scan_id, f"Checkov/CKV_K8S_{i}", Severity.INFO, Category.RELIABILITY,
            DEPLOYEMT, "Checkov", f"K8S check {i}",
        ))
    # 4 INFO Checkov on the misspelled statefulset manifest
    for i in range(4):
        findings.append(_finding(
            scan_id, f"Checkov/CKV_K8S_1{i}", Severity.INFO, Category.RELIABILITY,
            STATEFULLSET, "Checkov", f"K8S sts check {i}",
        ))
    # 1 INFO Checkov on a native-named manifest under helm-chart/
    findings.append(_finding(
        scan_id, "Checkov/CKV_K8S_21", Severity.INFO, Category.SECURITY,
        INGRESS, "Checkov", "Ingress check",
    ))
    # DevArchAI rules (2 high, 1 medium) on the misspelled manifest
    findings.append(_finding(
        scan_id, "K8S-SEC-001", Severity.HIGH, Category.SECURITY,
        DEPLOYEMT, "DevArchAI", "Missing NetworkPolicy",
    ))
    findings.append(_finding(
        scan_id, "K8S-SCALE-001", Severity.HIGH, Category.SCALABILITY,
        DEPLOYEMT, "DevArchAI", "No resource limits",
    ))
    findings.append(_finding(
        scan_id, "K8S-REL-002", Severity.MEDIUM, Category.RELIABILITY,
        DEPLOYEMT, "DevArchAI", "No probes",
    ))
    # Docker
    findings.append(_finding(
        scan_id, "DKR-SEC-001", Severity.HIGH, Category.SECURITY,
        DOCKERFILE, "", "Root user",
    ))
    findings.append(_finding(
        scan_id, "DKR-REL-001", Severity.LOW, Category.RELIABILITY,
        DOCKERFILE, "", "No healthcheck",
    ))
    findings.append(_finding(
        scan_id, "Checkov/CKV_DOCKER_2", Severity.INFO, Category.RELIABILITY,
        DOCKERFILE, "Checkov", "Docker check 2",
    ))
    findings.append(_finding(
        scan_id, "Checkov/CKV_DOCKER_3", Severity.INFO, Category.RELIABILITY,
        DOCKERFILE, "Checkov", "Docker check 3",
    ))
    # GitHub Actions
    findings.append(_finding(
        scan_id, "CI-SEC-001", Severity.HIGH, Category.SECURITY,
        WORKFLOW_CI, "", "No security scanning",
    ))
    findings.append(_finding(
        scan_id, "CI-SEC-003", Severity.MEDIUM, Category.SECURITY,
        WORKFLOW_CI, "", "Pinned actions",
    ))
    findings.append(_finding(
        scan_id, "Checkov/CKV2_GHA_1", Severity.INFO, Category.SECURITY,
        WORKFLOW_BACKEND, "Checkov", "GHA check",
    ))
    return findings


BUCKETS = {"critical", "high", "medium", "low", "info"}


@pytest.mark.asyncio
async def test_technology_coverage_totals_match_severity_counts(client, test_db):
    """total_findings == sum(severity_counts.values()) per technology."""
    scan_id = uuid4()
    scan = Scan(
        id=scan_id,
        repository_url="https://github.com/test/k8s-coverage-repo",
        branch="main",
        status=ScanStatus.COMPLETED,
        overall_score=70.0,
        detected_stack=DETECTED_STACK,
    )
    test_db.add(scan)
    for f in _seed_findings(scan_id):
        test_db.add(f)
    await test_db.commit()

    response = await client.get(f"/api/v1/scan/results/{scan_id}")
    assert response.status_code == 200
    data = response.json()

    # --- Top-level counts: five buckets, zero-filled, self-consistent ---
    assert set(data["severity_counts"].keys()) == BUCKETS
    assert data["severity_counts"] == {
        "critical": 0, "high": 4, "medium": 2, "low": 1, "info": 22,
    }
    assert data["findings_count"] == sum(data["severity_counts"].values()) == 29
    assert data["risk_distribution"] == data["severity_counts"]

    details = {d["technology"]: d for d in data["technology_details"]}

    # --- Every entry: complete buckets and the core invariant ---
    for tech, entry in details.items():
        assert set(entry["severity_counts"].keys()) == BUCKETS, tech
        assert entry["total_findings"] == entry["findings_count"], tech
        assert entry["total_findings"] == sum(entry["severity_counts"].values()), (
            f"{tech}: total {entry['total_findings']} != "
            f"sum {entry['severity_counts']}"
        )

    # --- Kubernetes absorbs ALL 22 k8s findings incl. misspelled filenames ---
    k8s = details["kubernetes"]
    assert k8s["findings_count"] == 22
    assert k8s["severity_counts"] == {
        "critical": 0, "high": 2, "medium": 1, "low": 0, "info": 19,
    }
    assert k8s["files_count"] == 4

    # --- Helm: files but zero findings, zeros explicit ---
    helm = details["helm"]
    assert helm["files_count"] == 2
    assert helm["findings_count"] == 0
    assert helm["severity_counts"] == {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
    }

    # --- Docker / GitHub Actions buckets ---
    assert details["docker"]["severity_counts"] == {
        "critical": 0, "high": 1, "medium": 0, "low": 1, "info": 2,
    }
    assert details["github_actions"]["severity_counts"] == {
        "critical": 0, "high": 1, "medium": 1, "low": 0, "info": 1,
    }

    # --- Cards partition all findings; nothing is lost or double-counted ---
    assert sum(d["findings_count"] for d in details.values()) == len(data["findings"])

    # --- Each serialized finding carries its canonical technology ---
    per_tech_tally = {}
    for f in data["findings"]:
        assert f["technology"], f"finding {f['rule_id']} missing technology"
        per_tech_tally[f["technology"]] = per_tech_tally.get(f["technology"], 0) + 1
    assert per_tech_tally == {"kubernetes": 22, "docker": 4, "github_actions": 3}

    # --- Helm reportable via stack even with zero findings ---
    assert "helm" in data["detected_technologies"]


@pytest.mark.asyncio
async def test_severity_counts_lowercase_and_zero_filled(client, test_db):
    """Enum-name/value mismatch must never leak uppercase keys or drop zeros."""
    scan_id = uuid4()
    scan = Scan(
        id=scan_id,
        repository_url="https://github.com/test/single-finding",
        branch="main",
        status=ScanStatus.COMPLETED,
        detected_stack={"docker_files": ["Dockerfile"]},
    )
    test_db.add(scan)
    test_db.add(_finding(
        scan_id, "X-001", Severity.INFO, Category.SECURITY,
        "Dockerfile", "", "Only an info finding",
    ))
    await test_db.commit()

    response = await client.get(f"/api/v1/scan/results/{scan_id}")
    assert response.status_code == 200
    data = response.json()

    assert set(data["severity_counts"].keys()) == BUCKETS
    assert data["severity_counts"]["info"] == 1
    assert sum(data["severity_counts"].values()) == data["findings_count"]

    docker = next(d for d in data["technology_details"] if d["technology"] == "docker")
    assert docker["total_findings"] == 1
    assert docker["severity_counts"]["info"] == 1
    assert docker["severity_counts"]["critical"] == 0
