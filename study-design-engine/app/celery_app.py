"""Celery client for dispatching tasks to the shared worker."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "darpan_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
