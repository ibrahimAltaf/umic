"""Celery application factory for background workers."""

import os
import sys

from celery import Celery

# Allow importing shared API config when running inside the worker container
API_PATH = os.environ.get("API_APP_PATH", "/app/api")
if API_PATH not in sys.path and os.path.isdir(API_PATH):
    sys.path.insert(0, API_PATH)

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery = Celery(
    "umic_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.tasks.health",
        "app.tasks.sync_placeholders",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_annotations={
        "*": {
            "max_retries": 5,
            "retry_backoff": True,
            "retry_backoff_max": 600,
            "retry_jitter": True,
        }
    },
    beat_schedule={
        "gmail-sync-hourly": {
            "task": "integrations.gmail.sync",
            "schedule": 3600.0,
            "args": (),
            "kwargs": {"max_results": 100},
        },
        "drive-sync-hourly": {
            "task": "integrations.google_drive.sync",
            "schedule": 3600.0,
            "kwargs": {"max_results": 100},
        },
        "dropbox-sync-hourly": {
            "task": "integrations.dropbox.sync",
            "schedule": 3600.0,
            "kwargs": {"limit": 200},
        },
    },
)
