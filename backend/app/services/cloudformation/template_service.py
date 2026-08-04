"""CloudFormation template loading and rendering.

Handles loading YAML templates from disk and replacing
placeholders with runtime values.
"""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Templates live in backend/templates/ (sibling to app/)
_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"


class CloudFormationTemplateError(Exception):
    """Raised when template operations fail."""


def load_template(filename: str) -> str:
    """Load a CloudFormation template from the templates directory.

    Args:
        filename: Template filename (e.g., "aws-role-v1.yaml").

    Returns:
        Raw template content as a string.

    Raises:
        CloudFormationTemplateError: If file not found or unreadable.
    """
    template_path = _TEMPLATES_DIR / filename

    if not template_path.exists():
        raise CloudFormationTemplateError(
            f"Template not found: {template_path}",
        )

    try:
        content = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CloudFormationTemplateError(
            f"Failed to read template {filename}: {exc}",
        ) from exc

    logger.debug(
        "template_loaded",
        filename=filename,
        size_bytes=len(content),
    )

    return content


def render_template(template_content: str, variables: dict[str, str]) -> str:
    """Replace template placeholders with runtime values.

    Placeholders use double-brace syntax: {{VARIABLE_NAME}}
    All variables must be provided — missing keys raise an error.

    Args:
        template_content: Raw template string with placeholders.
        variables: Mapping of variable names to replacement values.

    Returns:
        Rendered template with all placeholders replaced.

    Raises:
        CloudFormationTemplateError: If a required variable is missing.
    """
    result = template_content

    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        if placeholder not in result:
            logger.warning(
                "template_placeholder_not_found",
                placeholder=placeholder,
            )
            continue
        result = result.replace(placeholder, str(value))

    # Check for any remaining unreplaced placeholders
    import re

    remaining = re.findall(r"\{\{(\w+)\}\}", result)
    if remaining:
        raise CloudFormationTemplateError(
            f"Missing required template variables: {', '.join(remaining)}",
        )

    logger.debug(
        "template_rendered",
        variables=list(variables.keys()),
    )

    return result
