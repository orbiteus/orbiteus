"""UI Config builder — introspects Pydantic write schemas and view XML
to produce the field/view metadata consumed by the frontend auto-render pipeline.

GET /api/base/ui-config returns:
  {
    "modules": [
      {
        "name": "crm",
        "label": "CRM",
        "category": "Sales",
        "models": [
          {
            "name": "crm.customer",
            "label": "Customer",
            "fields": [
              {"name": "email", "type": "email", "required": false, "label": "Email"},
              ...
            ],
            "views": {
              "list": "<list>...</list>",
              "form": "<form>...</form>",
              "kanban": null,
              "search": null,
            }
          }
        ]
      }
    ]
  }
"""
from __future__ import annotations

import inspect
import logging
import types
import uuid
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic annotation → UI type mapping
# ---------------------------------------------------------------------------

_SKIP_TYPES = {uuid.UUID}

# Float/int fields that should render as money in the UI
_MONETARY_FIELD_NAMES = frozenset({
    "expected_revenue", "amount", "unit_price", "price", "total", "subtotal",
    "tax_amount", "wage", "planned_hours", "effective_hours",
})

_SIMPLE_MAP: dict[type, str] = {
    str:   "text",
    int:   "number",
    float: "number",
    bool:  "boolean",
}


def _resolve_annotation(annotation: Any) -> str | None:
    """Map a Python type annotation to a UI field type string.

    Returns None if the field should be hidden from the UI (IDs, internal fields).
    """
    if annotation is None:
        return "text"

    origin = get_origin(annotation)

    # Handle Optional[X] / Union[X, None]
    if origin is types.UnionType or str(origin) in ("<class 'types.UnionType'>",):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if args:
            return _resolve_annotation(args[0])
    # typing.Optional / typing.Union
    if origin is not None and hasattr(origin, "__mro__"):
        pass

    # Unwrap Optional via get_args
    args = get_args(annotation)
    if args:
        non_none = [a for a in args if a is not type(None)]
        if non_none and get_origin(annotation) is not None:
            return _resolve_annotation(non_none[0])

    # UUID → hide (IDs)
    if annotation is uuid.UUID:
        return None

    # Enum → select
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return "select"

    # datetime / date → date
    import datetime as dt
    if annotation in (dt.datetime, dt.date):
        return "date"

    # list[...] → skip (complex multi-value, not rendered in simple form)
    if get_origin(annotation) is list:
        return None

    # Check __name__ for EmailStr (pydantic)
    name = getattr(annotation, "__name__", "") or ""
    if name == "EmailStr" or "EmailStr" in str(annotation):
        return "email"

    return _SIMPLE_MAP.get(annotation, "text")


def _field_label(name: str) -> str:
    """Convert snake_case field name to Title Case label."""
    return name.replace("_", " ").replace("-", " ").title()


def _fk_field_label(name: str) -> str:
    """Convert a foreign-key field name (``*_id``) to its display label.

    FK fields are named ``<target>_id`` by convention (``assigned_user_id``,
    ``customer_id``). Rendering the raw suffix in the UI produces labels like
    ``Assigned User Id`` which is both redundant and visually noisy. This
    helper strips the trailing ``_id`` before Title-Casing so the same field
    becomes ``Assigned User``.

    Business-identifier fields like ``tax_id`` or ``vat_id`` are NOT FKs
    (they have no ``relation``) and should keep their suffix — callers must
    therefore only use this helper when they already know the field is an
    FK / many2one. ``_field_label`` remains the default for everything else.
    """
    base = name[:-3] if name.endswith("_id") else name
    return base.replace("_", " ").replace("-", " ").title()


def _unwrap_optional(annotation: Any) -> Any:
    """Return inner type for Optional[X] / X | None."""
    if annotation is None:
        return None
    args = get_args(annotation)
    if not args:
        return annotation
    non_none = [a for a in args if a is not type(None)]
    if len(non_none) == 1:
        return non_none[0]
    return annotation


def _infer_fk_relation(field_name: str, parent_model: str) -> str | None:
    """Map a *_id field to a dotted model name (e.g. crm.customer) for many2one UI."""
    _INTERNAL = {"id", "tenant_id", "company_id", "active", "create_date", "write_date"}
    if field_name in _INTERNAL:
        return None
    if not field_name.endswith("_id"):
        return None
    mod = parent_model.split(".")[0]
    stem = field_name[:-3]
    if field_name == "assigned_user_id":
        return "base.user"
    if field_name == "company_id":
        return "base.company"
    if field_name == "partner_id":
        return "base.partner"
    if field_name == "parent_id":
        return None
    if field_name == "user_id":
        return "base.user"
    if field_name == "manager_id":
        return f"{mod}.employee"
    return f"{mod}.{stem}"


def _enum_options(annotation: Any) -> list[dict[str, str]] | None:
    """Extract enum members as select options."""
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return [{"value": m.value, "label": m.name.replace("_", " ").title()} for m in annotation]
    return None


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def pydantic_schema_to_fields(schema: type[BaseModel], model_name: str) -> list[dict[str, Any]]:
    """Introspect a Pydantic Write schema and return UI field descriptors.

    Skips:
    - list fields (complex, deferred)
    - id / tenant_id / company_id / active (internal)
    - UUID fields without a resolvable FK relation

    Returns list of field dicts with keys: name, type, required, label,
    optional options, optional relation (many2one).
    """
    _INTERNAL_FIELDS = {"id", "tenant_id", "company_id", "active", "create_date", "write_date"}

    # Field name → UI type override (applied after type inference)
    _NAME_HINTS: dict[str, str] = {
        "phone": "tel", "mobile": "tel", "fax": "tel",
        "email": "email",
        "website": "text",
        "description": "textarea", "notes": "textarea", "body": "textarea",
        "password": "text",  # never render passwords
    }

    result = []

    for field_name, field_info in schema.model_fields.items():
        if field_name in _INTERNAL_FIELDS:
            continue

        annotation = field_info.annotation
        # list[str] → tags widget; other list[...] still skipped
        if get_origin(annotation) is list:
            inner = [a for a in get_args(annotation) if a is not type(None)]
            if inner == [str] or (len(inner) == 1 and inner[0] is str):
                result.append({
                    "name":     field_name,
                    "type":     "tags",
                    "required": field_info.is_required(),
                    "label":    field_info.title or _field_label(field_name),
                })
            continue

        unwrapped = _unwrap_optional(annotation)

        # UUID foreign keys → many2one (relation inferred from field + parent model)
        if unwrapped is uuid.UUID or unwrapped == uuid.UUID:
            rel = _infer_fk_relation(field_name, model_name)
            if not rel:
                continue
            result.append({
                "name":     field_name,
                "type":     "many2one",
                "required": field_info.is_required(),
                "label":    field_info.title or _fk_field_label(field_name),
                "relation": rel,
            })
            continue

        ui_type = _resolve_annotation(annotation)
        if ui_type is None:
            continue

        # Field-name overrides (more specific than type inference)
        ui_type = _NAME_HINTS.get(field_name, ui_type)

        if ui_type == "number" and field_name in _MONETARY_FIELD_NAMES:
            ui_type = "monetary"

        required = field_info.is_required()
        label_str = field_info.title or _field_label(field_name)
        options = None

        if ui_type == "select":
            options = _enum_options(annotation)
            # Also try unwrapped Optional[Enum]
            if options is None:
                inner_args = [a for a in get_args(annotation) if a is not type(None)]
                first = inner_args[0] if inner_args else None
                if first and inspect.isclass(first) and issubclass(first, Enum):
                    options = _enum_options(first)

        entry: dict[str, Any] = {
            "name":     field_name,
            "type":     ui_type,
            "required": required,
            "label":    label_str,
        }
        if options is not None:
            entry["options"] = options

        result.append(entry)

    return result


def build_ui_config() -> dict[str, Any]:
    """Build the full UI config payload from registered modules and models.

    Called from GET /api/base/ui-config.
    """
    from orbiteus_core.auto_router import _model_registry
    from orbiteus_core.registry import registry
    from orbiteus_core.view_loader import get_resolved_arch_for_model

    all_views = registry.get_all_views()
    modules_out: list[dict[str, Any]] = []

    for mod_name in registry.loaded_modules:
        try:
            desc = registry.get_module(mod_name)
        except Exception:
            continue

        manifest = desc.manifest
        model_names: list[str] = manifest.get("models", [])
        label = manifest.get("name", mod_name.title())
        category = manifest.get("category", "")

        models_out: list[dict[str, Any]] = []
        for model_name in model_names:
            entry = _model_registry.get(model_name)
            if entry is None:
                continue

            write_schema = entry["write_schema"]
            try:
                fields = pydantic_schema_to_fields(write_schema, model_name)
            except Exception as e:
                logger.warning("Could not introspect schema for %s: %s", model_name, e)
                fields = []

            # Resolve view arch strings (XML) for each view type
            def _view(vtype: str) -> str | None:
                return get_resolved_arch_for_model(model_name, vtype, all_views)

            # Model label = last segment of dotted name, Title Case
            model_label = model_name.split(".")[-1].replace("_", " ").replace("-", " ").title()

            models_out.append({
                "name":   model_name,
                "label":  model_label,
                "fields": fields,
                "views": {
                    "list":     _view("list"),
                    "form":     _view("form"),
                    "kanban":   _view("kanban"),
                    "search":   _view("search"),
                    "calendar": _view("calendar"),
                    "graph":    _view("graph"),
                },
            })

        if models_out:
            modules_out.append({
                "name":     mod_name,
                "label":    label,
                "category": category,
                "models":   models_out,
            })

    return {"modules": modules_out}
