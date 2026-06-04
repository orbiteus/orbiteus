"""Canonical Orbiteus engine component catalogue (docs/pre-prompt.md §3).

Stable ordering for Technical → System status tiles.
"""
from __future__ import annotations

# UI sort order — keep aligned with pre-prompt stack sections.
COMPONENT_ORDER: tuple[str, ...] = (
    # Runtime
    "python",
    "fastapi",
    "http_server",
    # Persistence / ORM
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "postgresql",
    "pgvector",
    "pgbouncer",
    "pydantic",
    # Data services
    "redis",
    "cache",
    # Engine subsystems (orbiteus_core)
    "module_registry",
    "rbac",
    "audit",
    "event_bus",
    "realtime",
    "auth_jwt",
    "prometheus",
    # AI layer (group ``ai`` in payload)
    "ai_module_config",
    "ai_action_palette",
    "ai_agents",
    "ai_credentials",
    "ai_secret_key",
    "ai_embeddings",
    "ai_agent_runs",
    "ai_providers",
    "ai_tooling",
    # Async queue
    "celery_lib",
    "celery_worker",
    "celery_beat",
    "outbox",
    # Infra (often skipped in dev)
    "nginx",
    "docker",
)
