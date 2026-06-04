"""Celery 5 application factory (ADR-0013).

Run the worker:

    celery -A celery_app worker -l info -Q default,outbox

Run the scheduler:

    celery -A celery_app beat -l info

Broker and result backend both use Redis (REDIS_URL). Tasks are sync —
async work uses `asyncio.run(coro)` inside the task. This is the boring,
well-known pattern; senior fluency is high (ADR-0013).
"""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

# Honour the same env var that powers `orbiteus_core.cache` / `orbiteus_core.health`.
broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", broker_url)

app = Celery(
    "orbiteus",
    broker=broker_url,
    backend=result_backend,
    include=[
        "tasks.outbox_tasks",
        "tasks.webhook_tasks",
        "tasks.embedding_tasks",
        "tasks.ai_tasks",
    ],
)

app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_default_retry_delay=10,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_max_tasks_per_child=2000,
    worker_max_memory_per_child=400_000,  # 400 MB
    broker_connection_retry_on_startup=True,
)

# Periodic schedule (Celery Beat). docs/12-events-and-queues.md.
app.conf.beat_schedule = {
    "drain-outbox-every-5s": {
        "task": "tasks.outbox_tasks.drain_outbox",
        "schedule": 5.0,
    },
    "release-stuck-processing-every-minute": {
        "task": "tasks.outbox_tasks.release_stuck_processing",
        "schedule": crontab(minute="*"),
    },
    "poll-scheduled-agents-every-5-min": {
        "task": "tasks.ai_tasks.poll_scheduled_agents",
        "schedule": 300.0,
    },
}
