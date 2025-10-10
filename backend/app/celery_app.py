"""Celery application for async tasks"""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "vision_chatbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import tasks
from app.tasks import pubmed_tasks, pathway_tasks, file_tasks

__all__ = ["celery_app"]

