"""Tests for local technology stack detection."""

from __future__ import annotations

from pathlib import Path

from devsec.utils.detect import detect_stack


def _write(tree: dict, root: Path) -> None:
    for rel, content in tree.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_docker_and_compose_detected(tmp_path: Path):
    _write(
        {
            "Dockerfile": "FROM python:3.12\n",
            "docker-compose.yml": "services:\n  app:\n    image: x\n",
        },
        tmp_path,
    )
    stack = detect_stack(str(tmp_path))
    assert stack.has_docker is True
    assert stack.has_docker_compose is True
    assert "docker" in stack.technologies


def test_terraform_detected(tmp_path: Path):
    _write({"main.tf": 'resource "aws_s3_bucket" "b" {}\n'}, tmp_path)
    stack = detect_stack(str(tmp_path))
    assert stack.has_terraform is True
    assert stack.terraform_files == ["main.tf"]


def test_kubernetes_detected_via_manifest_content(tmp_path: Path):
    _write(
        {
            "k8s/deploy.yaml": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n",
            "k8s/svc.yaml": "apiVersion: v1\nkind: Service\nmetadata:\n  name: web\n",
        },
        tmp_path,
    )
    stack = detect_stack(str(tmp_path))
    assert stack.has_kubernetes is True
    assert len(stack.kubernetes_files) == 2


def test_non_kubernetes_yaml_ignored(tmp_path: Path):
    _write({"config.yml": "some:\n  unrelated: config\n"}, tmp_path)
    stack = detect_stack(str(tmp_path))
    assert stack.has_kubernetes is False


def test_github_actions_detected(tmp_path: Path):
    _write(
        {
            ".github/workflows/ci.yml": "name: CI\non: push\n",
            ".github/workflows/release.yaml": "name: Release\n",
        },
        tmp_path,
    )
    stack = detect_stack(str(tmp_path))
    assert stack.has_github_actions is True
    assert ".github/workflows/ci.yml" in stack.github_actions_files


def test_helm_requires_valid_chart(tmp_path: Path):
    _write(
        {"chart/Chart.yaml": "apiVersion: v2\nname: mychart\nversion: 1.0.0\n"},
        tmp_path,
    )
    stack = detect_stack(str(tmp_path))
    assert stack.has_helm is True
    assert stack.helm_files == ["chart/Chart.yaml"]


def test_helm_invalid_chart_not_detected(tmp_path: Path):
    _write({"Chart.yaml": "not: a: chart\n"}, tmp_path)
    stack = detect_stack(str(tmp_path))
    assert stack.has_helm is False


def test_languages_detected(tmp_path: Path):
    _write(
        {
            "a.py": "x",
            "b.py": "x",
            "c.js": "x",
            "d.tsx": "x",
        },
        tmp_path,
    )
    stack = detect_stack(str(tmp_path))
    assert "python" in stack.languages
    assert "node" in stack.languages


def test_empty_project(tmp_path: Path):
    stack = detect_stack(str(tmp_path))
    assert stack.technologies == []
    assert stack.file_count == 0


def test_to_backend_dict_contains_detected_stack_fields(tmp_path: Path):
    _write({"Dockerfile": "FROM alpine\n"}, tmp_path)
    stack = detect_stack(str(tmp_path))
    payload = stack.to_backend_dict()
    assert payload["has_docker"] is True
    assert payload["docker_files"] == ["Dockerfile"]
    assert "languages" not in payload
