"""JSON View Schema loader — primary view source (ADR-0022).

Modules ship `views/<model>.<type>.view.json` files referenced in
`manifest.data[]`. Validated with Pydantic; consumed by `ui_config.py` and
optionally seeded to `base_ui_views` for Technical admin.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

ViewType = Literal["list", "form", "kanban", "search", "calendar", "graph"]


class ListColumn(BaseModel):
    key: str
    label: str | None = None
    widget: str | None = None


class FormSection(BaseModel):
    title: str | None = None
    fields: list[str] = Field(default_factory=list)


class FormTab(BaseModel):
    title: str
    sections: list[FormSection] = Field(default_factory=list)


class JsonViewDefinition(BaseModel):
    """Canonical JSON view document."""

    model: str
    type: ViewType
    columns: list[ListColumn] | None = None
    sections: list[FormSection] | None = None
    tabs: list[FormTab] | None = None
    group_by: str | None = None
    card_fields: list[str] | None = None
    filters: list[str] | None = None

    @field_validator("model")
    @classmethod
    def model_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or "." not in v:
            raise ValueError("model must be a dotted name, e.g. crm.lead")
        return v


def load_json_view(path: Path, module: str) -> JsonViewDefinition:
    """Parse and validate a `.view.json` file."""
    if not path.exists():
        raise FileNotFoundError(f"View file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)

    try:
        view = JsonViewDefinition.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"Invalid JSON view at {path}: {exc}") from exc

    logger.debug("Loaded JSON view %s (%s) from %s", view.model, view.type, path)
    return view


def view_to_ui_payload(view: JsonViewDefinition) -> dict[str, Any]:
    """Return the dict embedded in ui-config (excludes redundant keys)."""
    return view.model_dump(exclude_none=True, mode="json")


def infer_view_name(view: JsonViewDefinition, module: str) -> str:
    """Stable view name for DB seeding."""
    slug = view.model.replace(".", "_")
    return f"{module}_{slug}_{view.type}"


async def seed_json_views_to_db(
    views: list[JsonViewDefinition],
    module: str,
    session: Any,
    ctx: Any,
) -> None:
    """Upsert JSON views into base_ui_views (arch stored as JSON text)."""
    from modules.base.controller.repositories import UiViewRepository

    repo = UiViewRepository(session, ctx)
    for view in views:
        name = infer_view_name(view, module)
        arch = json.dumps(view_to_ui_payload(view), ensure_ascii=False)
        existing, _ = await repo.search(domain=[("name", "=", name)], limit=1)
        data = {
            "name": name,
            "model": view.model,
            "type": view.type,
            "arch": arch,
            "module": module,
            "active": True,
        }
        if existing:
            await repo.update(existing[0].id, data)
        else:
            await repo.create(data)
