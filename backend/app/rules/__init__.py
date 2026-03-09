"""Rule Engine"""

from app.rules.base import (
    BaseRule,
    Rule,
    RuleFinding,
    RuleRegistry,
    Severity,
    Category,
    register_rule,
    registry,
)

# Import all rule modules to register them
from app.rules import security
from app.rules import reliability
from app.rules import scalability
from app.rules import cost
from app.rules import observability
from app.rules import dockerfile
from app.rules import terraform
from app.rules import kubernetes
from app.rules import cicd

__all__ = [
    "BaseRule",
    "Rule",
    "RuleFinding",
    "RuleRegistry",
    "Severity",
    "Category",
    "register_rule",
    "registry",
]
