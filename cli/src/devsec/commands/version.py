"""``devsec version`` - print version information."""

from __future__ import annotations

import platform

from devsec._version import __version__
from devsec.config import Config
from devsec.output.console import print_muted


def version_cmd(*, json: bool = False) -> dict:
    """Build (and optionally print) version information."""
    data = {
        "app": "devsec",
        "version": __version__,
        "python": platform.python_version(),
        "api_url": Config().api_url_display(),
    }
    if not json:
        print_muted(
            f"devsec {__version__} (Python {platform.python_version()}) - API: {data['api_url']}"
        )
    return data
