"""Celery application for background twin pipeline tasks."""

import sys
from pathlib import Path

from celery import Celery

from app.config import settings

# Add twin-generator to Python path so its scripts are importable
_twin_gen_root = Path(settings.twin_data_dir).parent
if str(_twin_gen_root) not in sys.path:
    sys.path.insert(0, str(_twin_gen_root))

celery_app = Celery(
    "darpan_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker (LLM-bound)
    # Hard kill any task that runs past 30 minutes. A single twin simulation
    # normally takes ~4 minutes; anything close to 30m indicates a stuck
    # retry loop or hung HTTP call, and we'd rather fail fast than burn API
    # credits while a worker spins.
    task_time_limit=1800,       # SIGKILL at 30 min
    task_soft_time_limit=1680,  # SoftTimeLimitExceeded at 28 min (graceful)
    # Retry a task once on WorkerLostError / SIGKILL — safe for our idempotent
    # sim tasks (each simulation_run row is created upstream by the API).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Explicitly import tasks to ensure registration
import app.tasks.twin_tasks  # noqa: F401, E402
