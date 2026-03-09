"""Celery application configuration."""

from celery import Celery
from devarchai.config import settings

# Create Celery application
celery_app = Celery(
    "devarchai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "devarchai.workers.tasks.scan_tasks",
        "devarchai.workers.tasks.report_tasks",
        "devarchai.workers.tasks.email_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=["json"],
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Result settings
    result_expires=3600,
    result_persistent=True,
    # Rate limiting
    worker_send_task_events=True,
    task_send_sent_event=True,
)


def get_celery_app() -> Celery:
    """Get Celery application instance."""
    return celery_app
