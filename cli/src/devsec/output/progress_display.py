"""Rich terminal rendering for backend-driven scan lifecycle progress."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from devsec.models.scan import ScanStateResponse, TechnologyResult
from devsec.output.console import get_console, is_no_color, is_quiet

# Ordered base lifecycle stages (must match backend scan_lifecycle.py).
_BASE_STAGES: list[tuple[str, str]] = [
    ("connecting_repository", "Connecting to repository"),
    ("cloning", "Cloning repository"),
    ("cloned", "Repository cloned"),
    ("detecting_technologies", "Detecting technologies"),
    ("scanning", "Scanning infrastructure"),
    ("analyzing", "Analyzing findings"),
    ("scan_completed", "Scan completed"),
]

_STAGE_INDEX = {stage_id: idx for idx, (stage_id, _) in enumerate(_BASE_STAGES)}


def format_technology_label(tech_id: str, name: str | None = None) -> str:
    if name:
        return name
    labels = {
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "helm": "Helm",
        "terraform": "Terraform",
        "github_actions": "GitHub Actions",
        "gitlab_ci": "GitLab CI",
        "jenkins": "Jenkins",
        "circleci": "CircleCI",
        "azure_devops": "Azure DevOps",
        "ansible": "Ansible",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "docker_compose": "Docker Compose",
    }
    return labels.get(tech_id, tech_id.replace("_", " ").title())


def _progress_bar(percent: int, width: int = 15) -> str:
    pct = max(0, min(100, percent))
    filled = int(width * pct / 100)
    return f"{'█' * filled}{'░' * (width - filled)} {pct}%"


@dataclass
class LifecycleProgressRenderer:
    """Incremental stderr renderer — only prints new/changed lines."""

    completed_stages: set[str] = field(default_factory=set)
    current_stage: str | None = None
    technologies: dict[str, TechnologyResult] = field(default_factory=dict)
    tech_status: dict[str, str] = field(default_factory=dict)
    progress: int | None = None
    ai_status: str | None = None
    failed: bool = False
    error_message: str | None = None
    _printed_stage_lines: set[str] = field(default_factory=set)
    _printed_tech_lines: set[str] = field(default_factory=set)
    _ai_line_printed: str | None = None
    _last_scan_bar: str | None = None

    def apply_state(self, state: ScanStateResponse) -> None:
        stage = state.stage or state.current_operation
        if stage:
            idx = _STAGE_INDEX.get(stage)
            if idx is not None:
                for stage_id, _ in _BASE_STAGES[:idx]:
                    self.completed_stages.add(stage_id)
                self.current_stage = stage
            elif stage == "failed":
                self.failed = True
            elif stage == "scan_completed":
                for stage_id, _ in _BASE_STAGES:
                    self.completed_stages.add(stage_id)
                self.current_stage = "scan_completed"

        if state.status.lower() == "failed":
            self.failed = True
            self.error_message = state.error_message or state.message
            self.ai_status = None

        if state.progress is not None:
            self.progress = state.progress

        if state.stage == "scan_completed" or state.status.lower() == "completed":
            for stage_id, _ in _BASE_STAGES:
                self.completed_stages.add(stage_id)
            self.current_stage = "scan_completed"
            self.progress = 100

        for tech in state.technology_items:
            self.technologies[tech.id] = tech
            if tech.status in {"scanning", "completed", "scanned"}:
                self.tech_status[tech.id] = tech.status

        if state.ai_status:
            self.ai_status = state.ai_status

    def apply_ws(self, msg_type: str, data: dict) -> None:
        if msg_type in {"scan_stage", "scan_progress", "stage_transition"}:
            stage = data.get("stage") or data.get("lifecycle_stage")
            if stage:
                fake = ScanStateResponse(
                    scan_id=str(data.get("scan_id", "")),
                    status=str(data.get("status", "running")),
                    stage=str(stage),
                    progress=data.get("progress"),
                    message=data.get("message"),
                )
                self.apply_state(fake)
            if data.get("progress") is not None:
                self.progress = int(data["progress"])
        elif msg_type == "technology_detected":
            tech_id = str(data.get("technology") or data.get("id") or "")
            if tech_id:
                name = data.get("name") or format_technology_label(tech_id)
                self.technologies[tech_id] = TechnologyResult(
                    id=tech_id,
                    name=name,
                    status="detected",
                )
        elif msg_type == "technology_scan_started":
            tech_id = str(data.get("technology") or data.get("technology_id") or "")
            if tech_id:
                self.tech_status[tech_id] = "scanning"
        elif msg_type == "technology_scan_completed":
            tech_id = str(data.get("technology") or data.get("technology_id") or "")
            if tech_id:
                self.tech_status[tech_id] = "completed"
                findings = int(data.get("findings") or data.get("findings_count") or 0)
                existing = self.technologies.get(tech_id)
                name = existing.name if existing else format_technology_label(tech_id)
                self.technologies[tech_id] = TechnologyResult(
                    id=tech_id,
                    name=name,
                    status="completed",
                    findings=findings,
                )
        elif msg_type in {"scan_failed", "scan_cancelled"}:
            self.failed = True
            self.error_message = data.get("error_message") or data.get("message")
            self.ai_status = None
        elif msg_type in {"scan_completed", "scan_complete"}:
            for stage_id, _ in _BASE_STAGES:
                self.completed_stages.add(stage_id)
            self.current_stage = "scan_completed"
            self.progress = 100
        elif msg_type in {"ai_started", "ai.analysis.started", "AI_STARTED"}:
            self.ai_status = "processing"
        elif msg_type in {
            "ai_completed",
            "ai.analysis.completed",
            "AI_COMPLETED",
            "ai.analysis.completed",
            "ai_analysis_completed",
        }:
            self.ai_status = "completed"
        elif msg_type in {"ai.analysis.failed", "AI_ANALYSIS_FAILED", "ai_analysis_failed"}:
            self.ai_status = "failed"
        elif msg_type == "ai_progress":
            self.ai_status = "processing"

    def render(self) -> None:
        if is_quiet():
            return
        console = get_console(stderr=True)

        # Print each lifecycle stage once — only when completed (no duplicate in-progress lines).
        for stage_id, label in _BASE_STAGES:
            line_key = f"stage:{stage_id}"
            if stage_id in self.completed_stages and line_key not in self._printed_stage_lines:
                self._print_line(console, f"✓ {label}")
                self._printed_stage_lines.add(line_key)

        # Active scanning: single updating progress line (not repeated stage labels).
        if (
            self.current_stage == "scanning"
            and "scanning" not in self.completed_stages
            and self.progress is not None
        ):
            bar_line = f"Scanning infrastructure\n    {_progress_bar(self.progress)}"
            if bar_line != self._last_scan_bar:
                self._print_line(console, bar_line)
                self._last_scan_bar = bar_line

        for tech_id in sorted(self.technologies.keys(), key=lambda t: self.technologies[t].name or t):
            tech = self.technologies[tech_id]
            label = format_technology_label(tech_id, tech.name)
            status = self.tech_status.get(tech_id, tech.status)
            line_key = f"tech:{tech_id}:{status}"
            if line_key in self._printed_tech_lines:
                continue
            if status in {"completed", "scanned"}:
                self._print_line(console, f"  {label}\n    ✓ scanned")
                self._printed_tech_lines.add(line_key)
            elif status == "scanning":
                self._print_line(console, f"  {label}\n    scanning...")
                self._printed_tech_lines.add(line_key)
            elif status == "detected" and tech_id not in self.tech_status:
                self._print_line(console, f"  {label}")
                self._printed_tech_lines.add(f"tech:{tech_id}:detected")

        if self.failed and self.error_message:
            self._print_line(console, f"✗ Scan failed\n    {self.error_message}")
            return

        scan_done = "scan_completed" in self.completed_stages or self.current_stage == "scan_completed"
        if scan_done and self.ai_status:
            ai_line = self._ai_line()
            if ai_line and ai_line != self._ai_line_printed:
                self._print_line(console, ai_line)
                self._ai_line_printed = ai_line

    def _ai_line(self) -> str | None:
        if not self.ai_status:
            return None
        status = self.ai_status.lower()
        if status == "pending":
            return "AI analysis\n    ⠋ Queued — starting recommendation engine..."
        if status in {"processing", "running"}:
            return "AI analysis\n    ⠋ Generating remediation recommendations..."
        if status == "completed":
            return "✓ AI recommendations ready"
        if status == "failed":
            return "✗ AI analysis failed"
        return None

    def _print_line(self, console, text: str) -> None:
        if is_no_color():
            print(text, file=sys.stderr)
            return
        console.print(text)
