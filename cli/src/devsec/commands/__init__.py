"""Command registrations for the DevArchAI CLI."""

from devsec.commands.auth_cmd import app as auth_app
from devsec.commands.config_cmd import app as config_app
from devsec.commands.project_cmd import app as project_app
from devsec.commands.version import version_cmd

__all__ = ["auth_app", "config_app", "project_app", "version_cmd"]
