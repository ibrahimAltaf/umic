"""Worker health / heartbeat tasks."""

from app.celery_app.celery import celery


@celery.task(name="worker.health.ping")
def ping() -> dict:
    return {"status": "ok", "service": "worker"}
