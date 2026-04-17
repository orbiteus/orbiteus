"""CRM module domain models – pure Python dataclasses."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from orbiteus_core.base_domain import BaseModel


@dataclass
class Customer(BaseModel):
    """A CRM customer (person or organization)."""

    name: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    website: str = ""
    street: str = ""
    city: str = ""
    country_code: str = "PL"
    is_company: bool = False
    vat: str = ""
    status: str = "lead"        # lead / prospect / customer / churned
    assigned_user_id: uuid.UUID | None = None
    partner_id: uuid.UUID | None = None  # link to base.partner
    tags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Pipeline(BaseModel):
    """A sales pipeline (e.g. 'New Business', 'Renewals')."""

    name: str = ""
    description: str = ""
    currency_code: str = "PLN"
    is_default: bool = False


@dataclass
class Stage(BaseModel):
    """A stage within a pipeline (e.g. Lead → Qualified → Proposal → Won)."""

    name: str = ""
    pipeline_id: uuid.UUID = field(default_factory=uuid.uuid4)
    sequence: int = 10
    probability: float = 0.0     # 0-100
    is_won: bool = False
    is_lost: bool = False
    fold: bool = False           # Collapsed in kanban by default


@dataclass
class Opportunity(BaseModel):
    """A sales opportunity linked to a customer and pipeline stage."""

    name: str = ""
    customer_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    expected_revenue: float = 0.0
    probability: float = 0.0
    close_date: datetime | None = None
    description: str = ""
    lost_reason: str = ""
    tags: list[str] = field(default_factory=list)
    # Workflow state managed by Temporal
    workflow_run_id: str | None = None
