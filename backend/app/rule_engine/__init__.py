"""Canonical rule engine package for production scanning.

This is the ONE authoritative rule engine used by:
  - SyncScanService (unified_scan.py, scans.py, repo_analysis.py, public_scans.py)
  - ScanService (scan_worker.py, repo_analysis.py)
  - Celery scan_repository_task

Rules self-register via @register_rule decorator at import time.
RuleRegistry is a singleton — all consumers share the same registry.

DEPRECATED: app.rules/ is a legacy rule system NOT used by production scanning.
DEPRECATED: app.engines.rule_engine.py (YAMLRuleEngine) is NOT used in production.
DEPRECATED: RuleRunner is dead code — use RuleRegistry.evaluate_all() directly.
"""

from app.rule_engine.rules import (
    cicd_rules,
    devops_tool_rules,
    docker_rules,
    kubernetes_rules,
    terraform_rules,
)

__all__ = []
