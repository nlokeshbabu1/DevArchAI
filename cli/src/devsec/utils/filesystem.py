"""Secure filesystem traversal and exclusion rules.

The CLI never uploads repository content in Phase 1, but the exclusion engine
here is the same one Phase 2 will use before any content leaves the machine.
It enforces, in order:

1. **Hard exclusions** - secrets and VCS/build internals that can *never* be
   negated (``.env*``, private keys, ``.git/``, ``node_modules/``, ...).
2. **Default exclusions** - safe defaults applied to every project.
3. **``.devsecignore``** - project-local gitignore-style patterns appended
   after the defaults (negation ``!`` is allowed here).

Safety properties:

- Symlinks pointing outside the repository root are never followed.
- Symlinked directories are never descended into (prevents cycles).
- Paths are normalized and anchored to the resolved repository root.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from devsec.utils.errors import UsageError

# ---------------------------------------------------------------------------
# Pattern list definitions
# ---------------------------------------------------------------------------

# Never uploadable, regardless of .devsecignore negation.
HARD_EXCLUDES: tuple[str, ...] = (
    ".git/",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    ".aws/",
    ".ssh/",
    "node_modules/",
    ".venv/",
    "venv/",
    "*.pyc",
    "__pycache__/",
)

# Safe defaults applied to every project (can be negated by .devsecignore).
DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".gitignore",
    ".devsecignore",
    "dist/",
    "build/",
    "coverage/",
    ".tox/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".coverage",
    "*.log",
    "*.tmp",
    "*.swp",
    "*.bak",
    ".idea/",
    ".vscode/",
    "*.min.js",
    "*.map",
    "terraform.tfstate",
    "terraform.tfstate.*",
    ".terraform/",
    "Pipfile.lock",
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
)

# Cap on the number of files walked (metadata only, protects the CLI itself).
MAX_FILES = 200_000
# Files larger than this are excluded from content reading during detection.
MAX_READABLE_FILE_SIZE = 20 * 1024 * 1024  # 20 MiB


@dataclass
class IgnoreRule:
    """A single gitignore-style rule."""

    pattern: str
    negated: bool = False
    dir_only: bool = False
    anchored: bool = False
    regex: re.Pattern = field(init=False)

    def __post_init__(self) -> None:
        self.regex = re.compile(f"^{_translate(self.pattern)}$")


def _translate(pat: str) -> str:
    """Translate a gitignore glob to a regular expression fragment."""
    i, n = 0, len(pat)
    res = ""
    while i < n:
        c = pat[i]
        i += 1
        if c == "*":
            if i < n and pat[i] == "*":
                i += 1
                if i < n and pat[i] == "/":
                    i += 1
                    res += "(?:.*/)?"
                else:
                    res += ".*"
            else:
                res += "[^/]*"
        elif c == "?":
            res += "[^/]"
        elif c == "[":
            j = i
            if j < n and pat[j] in "!]":
                j += 1
            while j < n and pat[j] != "]":
                j += 1
            if j >= n:
                res += "\\["
            else:
                stuff = pat[i:j].replace("\\", "\\\\")
                if stuff.startswith("!"):
                    stuff = "^" + stuff[1:]
                res += "[" + stuff + "]"
                i = j + 1
        else:
            res += re.escape(c)
    return res


def parse_ignore_lines(lines: list[str]) -> list[IgnoreRule]:
    """Parse gitignore-style lines into rules."""
    rules: list[IgnoreRule] = []
    for raw in lines:
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("\\#"):
            line = line[1:]
        negated = False
        if line.startswith("!"):
            negated = True
            line = line[1:]
        if not line:
            continue
        dir_only = line.endswith("/")
        line = line.rstrip("/")
        anchored = line.startswith("/")
        line = line.lstrip("/")
        if not line:
            continue
        rules.append(IgnoreRule(line, negated=negated, dir_only=dir_only, anchored=anchored))
    return rules


def _matches(rule: IgnoreRule, rel: str) -> bool:
    """Match a normalized relative path (posix, no leading slash) against a rule."""
    segments = rel.split("/")
    if "/" not in rule.pattern:
        # Pattern has no slash: match against any path segment.
        return any(rule.regex.match(seg) for seg in segments)
    # Pattern is anchored (starts with '/') or contains a slash: match full path.
    candidate = "/".join(segments)
    return bool(rule.regex.match(candidate))


def _rule_applies_to_dir(rule: IgnoreRule, rel_dir: str) -> bool:
    """Decide whether a rule excludes a directory (and hence its subtree)."""
    if not rule.dir_only and "/" in rule.pattern:
        return _matches(rule, rel_dir)
    return rule.dir_only and _matches(rule, rel_dir)


class IgnoreMatcher:
    """Evaluate hard + default + project rules for a working tree."""

    def __init__(
        self,
        project_patterns: list[str] | None = None,
        *,
        hard_patterns: tuple[str, ...] = HARD_EXCLUDES,
        default_patterns: tuple[str, ...] = DEFAULT_EXCLUDES,
    ) -> None:
        self._hard = parse_ignore_lines(list(hard_patterns))
        self._rules = parse_ignore_lines(list(default_patterns))
        self._rules.extend(parse_ignore_lines(project_patterns or []))

    def ignored_dir(self, rel: str) -> bool:
        """Return True if a directory (and its subtree) should be skipped."""
        if any(_rule_applies_to_dir(r, rel) for r in self._hard):
            return True
        excluded = False
        for rule in self._rules:
            if _rule_applies_to_dir(rule, rel):
                excluded = not rule.negated
        return excluded

    def ignored_file(self, rel: str) -> bool:
        """Return True if a file should be skipped."""
        if any(_matches(r, rel) for r in self._hard):
            return True
        excluded = False
        for rule in self._rules:
            if _matches(rule, rel):
                excluded = not rule.negated
        return excluded


def load_devsecignore(root: Path) -> list[str]:
    """Read ``.devsecignore`` patterns from a repository root (if present)."""
    ignore_file = root / ".devsecignore"
    if not ignore_file.is_file():
        return []
    try:
        return ignore_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise UsageError(
            f"Unable to read .devsecignore: {exc}", hint="Check file permissions."
        ) from exc


@dataclass
class ProjectFile:
    """A file eligible for analysis in a project tree."""

    rel_path: str
    abs_path: Path
    size: int


def iter_project_files(
    root: Path,
    matcher: IgnoreMatcher | None = None,
) -> list[ProjectFile]:
    """Walk a project tree, applying exclusion rules and safety checks."""
    try:
        root_resolved = root.resolve(strict=True)
    except OSError as exc:
        raise UsageError(
            f"Directory does not exist or is not accessible: {root}", hint=str(exc)
        ) from exc
    if not root_resolved.is_dir():
        raise UsageError(f"Not a directory: {root}")

    matcher = matcher or IgnoreMatcher()
    files: list[ProjectFile] = []

    def _walk(directory: Path) -> None:
        if len(files) >= MAX_FILES:
            return
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise UsageError(
                f"Unable to read directory {directory}: {exc}", hint="Check permissions."
            ) from exc

        for entry in entries:
            if len(files) >= MAX_FILES:
                break
            entry_path = Path(entry.path)
            rel = entry_path.relative_to(root_resolved).as_posix()

            is_symlink = entry.is_symlink()
            if is_symlink:
                try:
                    target = entry_path.resolve(strict=True)
                except OSError:
                    continue
                # Reject symlinks that escape the repository root.
                try:
                    target.relative_to(root_resolved)
                except ValueError:
                    continue
                if target.is_dir():
                    continue  # Never descend into symlinked directories.

            try:
                if entry.is_dir(follow_symlinks=False):
                    if matcher.ignored_dir(rel):
                        continue
                    _walk(entry_path)
                    continue
            except OSError:
                continue

            if not entry.is_file(follow_symlinks=False):
                continue
            if matcher.ignored_file(rel):
                continue
            try:
                size = entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
            files.append(ProjectFile(rel_path=rel, abs_path=entry_path, size=size))

    _walk(root_resolved)
    return files


def project_summary(root: Path) -> dict:
    """Collect lightweight metadata about a project tree."""
    matcher = IgnoreMatcher(load_devsecignore(root))
    files = iter_project_files(root, matcher=matcher)
    total = sum(f.size for f in files)
    return {
        "root": str(root.resolve()),
        "file_count": len(files),
        "files_analyzed": len(files),
        "total_size_bytes": total,
    }
