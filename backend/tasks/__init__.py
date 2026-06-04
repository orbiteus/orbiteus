"""Celery tasks for Orbiteus (ADR-0013, ADR-0010).

Modules:
- `outbox_tasks` — drain `base_outbox`, mark dead, release stuck rows.
- `webhook_tasks` — HMAC-signed webhook delivery to subscribers.
- `embedding_tasks` — refresh `base_embeddings` from outbox rows.
- `ai_tasks` — async agent runs and scheduled agents.
"""
