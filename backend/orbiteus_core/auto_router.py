"""Auto-CRUD router generator.

For every model registered in the ModuleRegistry, this module generates
a standard FastAPI router with 5 endpoints:

  GET    /api/{module}/{model}          → list (paginated)
  POST   /api/{module}/{model}          → create
  GET    /api/{module}/{model}/{id}     → get one
  PUT    /api/{module}/{model}/{id}     → update
  DELETE /api/{module}/{model}/{id}     → soft delete

The router is built from the domain class and its SQLAlchemy Table,
auto-generating Pydantic schemas on the fly.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel as PydanticBase
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.exceptions import AccessDenied, NotFound
from orbiteus_core.security.middleware import require_auth

logger = logging.getLogger(__name__)

# Registry of model_name → (domain_class, repository_class, table)
_model_registry: dict[str, dict[str, Any]] = {}

# Query params that control pagination / ordering — NOT treated as filters
_CONTROL_PARAMS = {"offset", "limit", "order_by", "order_dir"}

# Special convenience param aliases → (field_name, operator)
_PARAM_ALIASES: dict[str, tuple[str, str]] = {
    "created_after":  ("create_date", ">="),
    "created_before": ("create_date", "<="),
    "updated_after":  ("write_date",  ">="),
    "updated_before": ("write_date",  "<="),
}

# Suffix → domain operator
_SUFFIX_OPS: list[tuple[str, str]] = [
    ("__contains", "ilike"),
    ("__gte",      ">="),
    ("__gt",       ">"),
    ("__lte",      "<="),
    ("__lt",       "<"),
    ("__in",       "in"),
    ("__ne",       "!="),
]


def _parse_query_domain(params: dict[str, str]) -> tuple[list[tuple], str | None, str]:
    """Convert raw query-string params into a domain + order_by + order_dir triple.

    Supported patterns:
      ?status=prospect            → ("status", "=", "prospect")
      ?name__contains=acme        → ("name", "ilike", "%acme%")
      ?created_after=2024-01-01   → ("create_date", ">=", "2024-01-01")
      ?order_by=name&order_dir=asc
      ?amount__gte=100
      ?tags__in=a,b,c             → ("tags", "in", ["a","b","c"])
    """
    domain: list[tuple] = []
    order_by = params.get("order_by")
    order_dir = params.get("order_dir", "asc")

    for key, value in params.items():
        if key in _CONTROL_PARAMS:
            continue

        # Alias shorthand
        if key in _PARAM_ALIASES:
            field, op = _PARAM_ALIASES[key]
            domain.append((field, op, value))
            continue

        # Suffix operators
        matched = False
        for suffix, op in _SUFFIX_OPS:
            if key.endswith(suffix):
                field = key[: -len(suffix)]
                parsed_value: Any = value
                if op == "in":
                    parsed_value = [v.strip() for v in value.split(",")]
                elif op == "ilike":
                    parsed_value = f"%{value}%"
                domain.append((field, op, parsed_value))
                matched = True
                break

        if not matched:
            # Plain equality
            domain.append((key, "=", value))

    return domain, order_by, order_dir


def register_model(
    model_name: str,
    domain_class: type,
    repository_class: type,
    table: Any,
    read_schema: type[PydanticBase],
    write_schema: type[PydanticBase],
) -> None:
    """Called from module mapping.py to expose a model for auto-CRUD."""
    _model_registry[model_name] = {
        "domain_class": domain_class,
        "repository_class": repository_class,
        "table": table,
        "read_schema": read_schema,
        "write_schema": write_schema,
    }
    logger.debug("Model registered for auto-CRUD: %s", model_name)


def build_crud_router(model_name: str) -> APIRouter | None:
    """Build and return a CRUD APIRouter for the given model_name."""
    entry = _model_registry.get(model_name)
    if entry is None:
        logger.warning("No model registration found for '%s', skipping auto-CRUD.", model_name)
        return None

    repo_class = entry["repository_class"]
    read_schema = entry["read_schema"]
    write_schema = entry["write_schema"]

    router = APIRouter(tags=[model_name])

    # ---- LIST ----
    @router.get("", response_model=dict, summary=f"List {model_name}")
    async def list_records(
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(25, ge=1, le=200),
        order_by: str | None = Query(None),
        order_dir: str = Query("asc", pattern="^(asc|desc)$"),
        session: AsyncSession = Depends(get_session),
        ctx: RequestContext = Depends(require_auth),
    ):
        # Build domain from all remaining query params
        raw_params = {k: v for k, v in request.query_params.items()
                      if k not in {"offset", "limit", "order_by", "order_dir"}}
        domain, _ob, _od = _parse_query_domain(raw_params)
        # Explicit Query params win for order
        effective_order_by = order_by or _ob
        effective_order_dir = order_dir or _od

        repo = repo_class(session, ctx)
        try:
            items, total = await repo.search(
                domain=domain,
                offset=offset,
                limit=limit,
                order_by=effective_order_by,
                order_dir=effective_order_dir,
            )
        except AccessDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        return {
            "items": [read_schema.model_validate(i, from_attributes=True) for i in items],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    # ---- GET ONE ----
    @router.get("/{record_id}", response_model=read_schema, summary=f"Get {model_name}")
    async def get_record(
        record_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        ctx: RequestContext = Depends(require_auth),
    ):
        repo = repo_class(session, ctx)
        try:
            return read_schema.model_validate(await repo.get(record_id), from_attributes=True)
        except NotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except AccessDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

    # ---- CREATE ----
    # FastAPI can't infer body from a dynamic type variable, so we read raw JSON
    # and validate manually with the write_schema.
    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED, summary=f"Create {model_name}")
    async def create_record(
        request: Request,
        session: AsyncSession = Depends(get_session),
        ctx: RequestContext = Depends(require_auth),
    ):
        body = write_schema.model_validate(await request.json())
        repo = repo_class(session, ctx)
        try:
            obj = await repo.create(body.model_dump(exclude_unset=True))
            return read_schema.model_validate(obj, from_attributes=True)
        except AccessDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

    # ---- UPDATE ----
    @router.put("/{record_id}", response_model=read_schema, summary=f"Update {model_name}")
    async def update_record(
        record_id: uuid.UUID,
        request: Request,
        session: AsyncSession = Depends(get_session),
        ctx: RequestContext = Depends(require_auth),
    ):
        """Merge JSON body with the existing record, then validate (supports partial updates)."""
        raw = await request.json()
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail="Request body must be a JSON object")

        repo = repo_class(session, ctx)
        try:
            existing_obj = await repo.get(record_id)
        except NotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except AccessDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

        existing_data = read_schema.model_validate(
            existing_obj, from_attributes=True
        ).model_dump(mode="json")
        write_keys = set(write_schema.model_fields.keys())
        merged: dict[str, Any] = {
            k: existing_data[k] for k in write_keys if k in existing_data
        }
        merged.update({k: v for k, v in raw.items() if k in write_keys})

        try:
            body = write_schema.model_validate(merged)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors()) from e

        try:
            obj = await repo.update(record_id, body.model_dump(exclude_unset=True))
            return read_schema.model_validate(obj, from_attributes=True)
        except AccessDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

    # ---- DELETE ----
    @router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary=f"Delete {model_name}")
    async def delete_record(
        record_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        ctx: RequestContext = Depends(require_auth),
    ):
        repo = repo_class(session, ctx)
        try:
            await repo.delete(record_id)
        except NotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except AccessDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e

    return router
