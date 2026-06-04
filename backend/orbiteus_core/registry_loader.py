"""Sync in-code model registry → base_models / base_model_fields tables.

The Technical → Models screen reads from these tables. Without seeding they
stay empty even though auto-CRUD routes exist for every registered model.
"""
from __future__ import annotations

import logging

from orbiteus_core.ui_config import _field_label, pydantic_schema_to_fields

logger = logging.getLogger(__name__)

_UI_TO_REGISTRY_TYPE = {
    "text": "char",
    "email": "char",
    "tel": "char",
    "number": "integer",
    "textarea": "text",
    "select": "selection",
    "boolean": "boolean",
    "date": "datetime",
    "many2one": "many2one",
    "monetary": "float",
    "tags": "json",
}


def _model_label(model_name: str) -> str:
    segment = model_name.split(".")[-1]
    return _field_label(segment)


async def seed_registry_to_db(session, ctx) -> None:
    """Upsert every auto-CRUD model and its fields into registry tables."""
    from orbiteus_core.auto_router import _model_registry
    from modules.base.controller.repositories import (
        RegistryModelFieldRepository,
        RegistryModelRepository,
    )

    model_repo = RegistryModelRepository(session, ctx)
    field_repo = RegistryModelFieldRepository(session, ctx)
    models_synced = 0
    fields_synced = 0

    for model_name, entry in sorted(_model_registry.items()):
        module = model_name.split(".", 1)[0]
        read_schema = entry.get("read_schema") or entry["write_schema"]
        write_schema = entry["write_schema"]

        existing, _ = await model_repo.search(
            domain=[("model_name", "=", model_name)],
            limit=1,
        )
        payload = {
            "model_name": model_name,
            "label": _model_label(model_name),
            "module": module,
            "description": f"Registered by ModuleRegistry ({module})",
            "is_transient": False,
        }
        if existing:
            record = await model_repo.update(existing[0].id, payload)
        else:
            record = await model_repo.create(payload)
        models_synced += 1

        ui_fields = pydantic_schema_to_fields(read_schema, model_name)
        if read_schema is not write_schema:
            write_ui = pydantic_schema_to_fields(write_schema, model_name)
            seen = {f["name"] for f in ui_fields}
            for wf in write_ui:
                if wf["name"] not in seen:
                    ui_fields.append(wf)

        for field in ui_fields:
            field_name = field["name"]
            existing_fields, _ = await field_repo.search(
                domain=[
                    ("model_name", "=", model_name),
                    ("field_name", "=", field_name),
                ],
                limit=1,
            )
            field_payload = {
                "model_id": record.id,
                "model_name": model_name,
                "field_name": field_name,
                "field_type": _UI_TO_REGISTRY_TYPE.get(field["type"], field["type"]),
                "label": field.get("label") or _field_label(field_name),
                "required": bool(field.get("required")),
                "readonly": False,
                "is_custom": False,
                "selection_values": field.get("options") or [],
                "related_model": field.get("relation"),
            }
            if existing_fields:
                await field_repo.update(existing_fields[0].id, field_payload)
            else:
                await field_repo.create(field_payload)
            fields_synced += 1

    removed = await _prune_stale_registry_models(
        model_repo, field_repo, set(_model_registry.keys())
    )

    logger.info(
        "Registry metadata seeded: %d models, %d fields, %d stale removed",
        models_synced,
        fields_synced,
        removed,
    )


async def _prune_stale_registry_models(
    model_repo,
    field_repo,
    live_models: set[str],
) -> int:
    """Drop registry rows for models no longer registered in code (e.g. removed CRM)."""
    stale, _ = await model_repo.search(domain=[], limit=5000)
    removed = 0
    for row in stale:
        if row.model_name in live_models:
            continue
        fields, _ = await field_repo.search(
            domain=[("model_name", "=", row.model_name)],
            limit=5000,
        )
        for field_row in fields:
            await field_repo.hard_delete(field_row.id)
        await model_repo.hard_delete(row.id)
        removed += 1
    return removed
