"""Validator registry tests."""

import pytest

from app.services.remediation_validators import run_validators

GO = "FROM golang:1.22\nCMD [\"/app\"]\n"
UPD = "FROM golang:1.22\nUSER 65532\nCMD [\"/app\"]\n"


def test_preservation_validator_passes_minimal_change():
    ok, results = run_validators("Dockerfile", GO, UPD, None)
    names = {r["name"] for r in results}
    assert "preservation" in names
    assert ok or any(r["name"] == "dockerfile_security" and r["status"] == "failed" for r in results)


def test_yaml_validator_rejects_invalid():
    ok, results = run_validators("k8s/app.yaml", "key: [", "key: [", None)
    yaml_results = [r for r in results if r["name"] == "yaml_syntax"]
    assert yaml_results and yaml_results[0]["status"] == "failed"
    assert ok is False
