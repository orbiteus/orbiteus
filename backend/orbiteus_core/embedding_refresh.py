"""Outbox-driven embedding refresh for `embed_models` (tree spec §4.9).

When a record in a module-declared `embed_models` list is created, updated,
or deleted, Celery drains an outbox row and upserts/deletes the matching
`base_embeddings` row. Semantic search then works without manual indexing.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.config import ai_registry
from orbiteus_core.auto_router import _model_registry
from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

EMBEDDING_PROVIDER = "openai"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Fields concatenated (in order) when building the embeddable document text.
_EMBED_FIELD_PRIORITY = (
    "name",
    "title",
    "email",
    "phone",
    "code",
    "description",
    "notes",
    "status",
    "kind",
    "expected_close_date",
    "probability",
    "revenue",
)


def build_embed_text(record: dict[str, Any]) -> str:
    """Turn a record dict into a single line suitable for embedding."""
    parts: list[str] = []
    seen: set[str] = set()
    for key in _EMBED_FIELD_PRIORITY:
        val = record.get(key)
        if val is None or val == "" or val is False:
            continue
        text = str(val).strip()
        if text and text not in seen:
            parts.append(f"{key}: {text}")
            seen.add(text)
    # Fallback: any remaining string-ish scalar fields.
    for key, val in sorted(record.items()):
        if key in seen or key.startswith("_") or key.endswith("_id"):
            continue
        if isinstance(val, (str, int, float, bool)) and val not in ("", None, False):
            text = str(val).strip()
            if text and text not in seen:
                parts.append(f"{key}: {text}")
                seen.add(text)
    return " | ".join(parts)


async def refresh_embedding_from_payload(
    session: AsyncSession,
    *,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Apply create/update/delete embedding side-effects for one outbox row."""
    model = str(payload.get("model") or "")
    record_id_raw = payload.get("id")
    tenant_id_raw = payload.get("tenant_id")

    if not model or not record_id_raw or not tenant_id_raw:
        return {"status": "skipped", "reason": "missing model/id/tenant_id"}

    if model not in ai_registry.embed_models():
        return {"status": "skipped", "reason": "model_not_in_embed_registry"}

    tenant_id = uuid.UUID(str(tenant_id_raw))
    record_id = uuid.UUID(str(record_id_raw))

    if event == "record.deleted":
        removed = await _delete_embedding(session, tenant_id, model, record_id)
        await session.commit()
        return {"status": "deleted", "removed": removed}

    ctx = RequestContext(
        tenant_id=tenant_id,
        is_superadmin=True,
        actor="system",
        scope="internal",
    )

    entry = _model_registry.get(model)
    if entry is None:
        return {"status": "skipped", "reason": "model_not_registered"}

    repo_class = entry["repository_class"]
    read_schema = entry["read_schema"]
    repo = repo_class(session, ctx)

    try:
        obj = await repo.get(record_id)
    except Exception:  # noqa: BLE001
        logger.warning(
            "embedding_refresh.record_missing",
            extra={"model": model, "record_id": str(record_id)},
        )
        removed = await _delete_embedding(session, tenant_id, model, record_id)
        await session.commit()
        return {"status": "deleted", "removed": removed, "reason": "record_gone"}

    record = read_schema.model_validate(obj, from_attributes=True).model_dump(mode="json")
    text = build_embed_text(record)
    if not text.strip():
        return {"status": "skipped", "reason": "empty_text"}

    from orbiteus_core.ai.keys import fetch_credential
    from orbiteus_core.ai.providers import get_provider

    cred = await fetch_credential(session, tenant_id=tenant_id, provider=EMBEDDING_PROVIDER)
    if cred is None:
        logger.info(
            "embedding_refresh.no_credential",
            extra={"tenant_id": str(tenant_id), "model": model},
        )
        return {"status": "skipped", "reason": "no_openai_credential"}

    provider = get_provider(EMBEDDING_PROVIDER)
    embed_model = cred.get("model_default") or DEFAULT_EMBED_MODEL
    vectors = await provider.embed(cred["secret"], texts=[text], model=embed_model)
    if not vectors:
        return {"status": "skipped", "reason": "empty_vector"}

    vector = vectors[0]
    dim = len(vector)
    vec_literal = "[" + ",".join(str(float(x)) for x in vector) + "]"

    await _upsert_embedding(
        session,
        tenant_id=tenant_id,
        model=model,
        record_id=record_id,
        provider=EMBEDDING_PROVIDER,
        model_name=embed_model,
        dim=dim,
        vec_literal=vec_literal,
    )
    await session.commit()
    return {"status": "indexed", "model": model, "record_id": str(record_id), "dim": dim}


async def _delete_embedding(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    model: str,
    record_id: uuid.UUID,
) -> int:
    from modules.base.model.mapping import base_embeddings_table

    result = await session.execute(
        delete(base_embeddings_table).where(
            base_embeddings_table.c.tenant_id == tenant_id,
            base_embeddings_table.c.model == model,
            base_embeddings_table.c.record_id == record_id,
        )
    )
    return int(result.rowcount or 0)


async def _upsert_embedding(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    model: str,
    record_id: uuid.UUID,
    provider: str,
    model_name: str,
    dim: int,
    vec_literal: str,
) -> None:
    from sqlalchemy import text

    row_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await session.execute(
        text(
            """
            INSERT INTO base_embeddings (
                id, create_date, write_date, tenant_id, model, record_id,
                provider, model_name, dim, vector
            ) VALUES (
                CAST(:id AS uuid), :now, :now, CAST(:tenant_id AS uuid),
                :model, CAST(:record_id AS uuid), :provider, :model_name, :dim,
                CAST(:vec AS vector)
            )
            ON CONFLICT (tenant_id, model, record_id, provider, model_name)
            DO UPDATE SET
                write_date = EXCLUDED.write_date,
                dim = EXCLUDED.dim,
                vector = EXCLUDED.vector
            """
        ),
        {
            "id": str(row_id),
            "now": now,
            "tenant_id": str(tenant_id),
            "model": model,
            "record_id": str(record_id),
            "provider": provider,
            "model_name": model_name,
            "dim": dim,
            "vec": vec_literal,
        },
    )
