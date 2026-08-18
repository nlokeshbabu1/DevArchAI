"""Tests for secure filesystem traversal and exclusion rules."""

from __future__ import annotations

import os
from pathlib import Path

from devsec.utils.errors import UsageError
from devsec.utils.filesystem import (
    HARD_EXCLUDES,
    IgnoreMatcher,
    iter_project_files,
    load_devsecignore,
    parse_ignore_lines,
)


def _write(tree: dict, root: Path) -> None:
    for rel, content in tree.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_default_excludes_hidden_secrets(tmp_path: Path):
    _write(
        {
            ".env": "DATABASE_URL=postgres://secret",
            ".env.production": "KEY=abc",
            "main.py": "print('hi')",
            "src/app.js": "x",
            "key.pem": "PRIVATE",
            "id_rsa": "PRIVATE",
            "node_modules/pkg/index.js": "x",
            "package.json": "{}",
        },
        tmp_path,
    )
    files = iter_project_files(tmp_path)
    rels = {f.rel_path for f in files}
    assert "main.py" in rels
    assert "src/app.js" in rels
    assert ".env" not in rels
    assert ".env.production" not in rels
    assert "key.pem" not in rels
    assert "id_rsa" not in rels
    assert "node_modules/pkg/index.js" not in rels
    assert "package.json" in rels


def test_hard_excludes_cannot_be_negated(tmp_path: Path):
    (tmp_path / ".devsecignore").write_text("!.env\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1", encoding="utf-8")
    matcher = IgnoreMatcher(load_devsecignore(tmp_path))
    assert matcher.ignored_file(".env") is True


def test_devsecignore_patterns(tmp_path: Path):
    (tmp_path / ".devsecignore").write_text(
        "build/\n*.generated.go\n!keep.generated.go\n", encoding="utf-8"
    )
    matcher = IgnoreMatcher(load_devsecignore(tmp_path))
    assert matcher.ignored_dir("build") is True
    assert matcher.ignored_file("x.generated.go") is True
    assert matcher.ignored_file("keep.generated.go") is False


def test_parse_ignore_lines_handles_comments_and_negation():
    rules = parse_ignore_lines(["# comment", "", "!keep.txt", "dist/", "/anchored.py"])
    assert [r.pattern for r in rules] == ["keep.txt", "dist", "anchored.py"]
    assert rules[0].negated is True
    assert rules[1].dir_only is True
    assert rules[2].anchored is True


def test_ignored_file_defaults_apply_without_project_file(tmp_path: Path):
    matcher = IgnoreMatcher()
    assert matcher.ignored_file(".env") is True
    assert matcher.ignored_file("dist/app.js") is True
    assert matcher.ignored_file("src/main.py") is False


def test_symlink_escape_skipped(tmp_path: Path):
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    os.symlink(outside, tmp_path / "escape.txt")
    (tmp_path / "normal.txt").write_text("ok", encoding="utf-8")
    files = iter_project_files(tmp_path)
    rels = {f.rel_path for f in files}
    assert "escape.txt" not in rels
    assert "normal.txt" in rels


def test_non_directory_raises(tmp_path: Path):
    file = tmp_path / "file.txt"
    file.write_text("x", encoding="utf-8")
    try:
        iter_project_files(file)
    except UsageError:
        pass
    else:
        raise AssertionError("expected UsageError")


def test_project_file_sizes_are_captured(tmp_path: Path):
    (tmp_path / "a.txt").write_text("12345", encoding="utf-8")
    files = iter_project_files(tmp_path)
    assert files[0].size == 5
    assert files[0].abs_path == (tmp_path / "a.txt").resolve()


def test_hard_excludes_are_secrets_and_vcs(tmp_path: Path):
    secrets = {p for p in HARD_EXCLUDES if not p.endswith("/")}
    assert ".env" in secrets
    assert "*.pem" in secrets
    assert "id_rsa" in secrets
