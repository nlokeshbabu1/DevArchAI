"""Rule Engine"""

# Import all rule modules to register them
from app.rules import (
    cicd,
    cost,
    dockerfile,
    kubernetes,
    observability,
    reliability,
    scalability,
    security,
    terraform,
)
from app.rules.base import (
    BaseRule,
    Category,
    Rule,
    RuleFinding,
    RuleRegistry,
    Severity,
    register_rule,
    registry,
)

# Import file type filter
from app.rules.file_type_filter import (
    FILE_TYPE_DEFINITIONS,
    IGNORE_PATTERNS,
    RULE_MODULE_MAP,
    FileTypeRuleFilter,
    categorize_files,
    detect_file_type,
    filter_files_by_type,
    get_applicable_rule_modules,
    rule_filter,
    should_ignore,
)

__all__ = [
    "BaseRule",
    "Rule",
    "RuleFinding",
    "RuleRegistry",
    "Severity",
    "Category",
    "register_rule",
    "registry",
    # File type filtering
    "FileTypeRuleFilter",
    "detect_file_type",
    "should_ignore",
    "get_applicable_rule_modules",
    "filter_files_by_type",
    "categorize_files",
    "rule_filter",
    "FILE_TYPE_DEFINITIONS",
    "IGNORE_PATTERNS",
    "RULE_MODULE_MAP",
]
