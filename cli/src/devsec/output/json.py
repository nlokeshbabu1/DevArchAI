"""Machine-readable JSON output for CI/CD.

Every command that supports ``--json`` routes its primary result through
:func:`emit` and its error path through :func:`emit_error`. Both write only
to ``stdout``; diagnostics go to ``stderr`` via the console layer.
"""

from __future__ import annotations

import json
from typing import Any


def emit(data: Any) -> None:
    """Print a JSON-serializable object to stdout."""
    print(json.dumps(data, indent=2, default=str))


def emit_error(data: dict[str, Any]) -> None:
    """Print a JSON error payload to stdout (process should still exit non-zero)."""
    print(json.dumps(data, indent=2, default=str))
