"""Worker tasks module."""

from devarchai.workers.tasks.scan_tasks import execute_scan, cancel_scan
from devarchai.workers.tasks.report_tasks import generate_report, export_report_pdf
from devarchai.workers.tasks.email_tasks import (
    send_welcome_email,
    send_scan_complete_email,
    send_invitation_email,
    send_weekly_digest,
)

__all__ = [
    # Scan tasks
    "execute_scan",
    "cancel_scan",
    # Report tasks
    "generate_report",
    "export_report_pdf",
    # Email tasks
    "send_welcome_email",
    "send_scan_complete_email",
    "send_invitation_email",
    "send_weekly_digest",
]
