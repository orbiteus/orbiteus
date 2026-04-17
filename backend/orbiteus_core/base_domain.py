"""Base domain model for all Orbiteus entities.

Every business entity inherits from BaseModel, which provides:
  - id: UUID primary key
  - tenant_id: multi-tenancy isolation (RLS)
  - company_id: multi-company support
  - create_date / write_date: audit timestamps
  - active: soft-delete flag
  - custom_fields: JSONB bag for runtime-added fields (V1 feature)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BaseModel:
    """Base for all Orbiteus domain entities."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    create_date: datetime | None = None
    write_date: datetime | None = None
    active: bool = True
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemModel:
    """Base for system/ir_* objects (no tenant isolation – global config)."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    create_date: datetime | None = None
    write_date: datetime | None = None
