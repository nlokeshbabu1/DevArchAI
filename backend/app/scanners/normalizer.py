"""
Normalize external scanner outputs into DevArchAI's RuleFinding schema.

Maps external severity levels and finding attributes to DevArchAI
Category and Severity enums.
"""

from app.rule_engine.base import Category, RuleFinding, Severity

SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
    "none": Severity.INFO,
    "unknown": Severity.INFO,
    "moderate": Severity.MEDIUM,
    "negligible": Severity.LOW,
    "important": Severity.HIGH,
    "warning": Severity.LOW,
    "error": Severity.HIGH,
}


def map_severity(external_severity: str | None) -> Severity:
    """Map external severity string to DevArchAI Severity enum."""
    if not external_severity:
        return Severity.INFO
    return SEVERITY_MAP.get(external_severity.lower().strip(), Severity.INFO)


CATEGORY_KEYWORDS: dict[str, Category] = {
    "secret": Category.SECURITY,
    "credential": Category.SECURITY,
    "password": Category.SECURITY,
    "token": Category.SECURITY,
    "key": Category.SECURITY,
    "cve": Category.SECURITY,
    "vulnerability": Category.SECURITY,
    "cwe": Category.SECURITY,
    "injection": Category.SECURITY,
    "xss": Category.SECURITY,
    "sqli": Category.SECURITY,
    "permission": Category.SECURITY,
    "privilege": Category.SECURITY,
    "auth": Category.SECURITY,
    "tls": Category.SECURITY,
    "ssl": Category.SECURITY,
    "encryption": Category.SECURITY,
    "dockerfile": Category.RELIABILITY,
    "docker": Category.RELIABILITY,
    "kubernetes": Category.RELIABILITY,
    "k8s": Category.RELIABILITY,
    "terraform": Category.RELIABILITY,
    "iac": Category.RELIABILITY,
    "misconfig": Category.RELIABILITY,
    "cost": Category.COST,
    "scalability": Category.SCALABILITY,
    "observability": Category.OBSERVABILITY,
    "monitoring": Category.OBSERVABILITY,
}


def detect_category(description: str, rule_id: str) -> Category:
    """Detect the most appropriate DevArchAI category from scanner context."""
    combined = f"{rule_id} {description}".lower()
    for keyword, cat in CATEGORY_KEYWORDS.items():
        if keyword in combined:
            return cat
    return Category.SECURITY
