"""CRM module Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class CustomerRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    company_id: uuid.UUID | None
    name: str
    email: str | None
    phone: str | None
    status: str
    is_company: bool
    city: str | None
    country_code: str
    assigned_user_id: uuid.UUID | None
    tags: list[str]
    create_date: datetime | None = None

    model_config = {"from_attributes": True}


class CustomerWrite(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    website: str | None = None
    street: str | None = None
    city: str | None = None
    country_code: str = "PL"
    is_company: bool = False
    vat: str | None = None
    status: str = "lead"
    assigned_user_id: uuid.UUID | None = None
    tags: list[str] = []
    notes: str = ""


class PipelineRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    currency_code: str
    is_default: bool

    model_config = {"from_attributes": True}


class PipelineWrite(BaseModel):
    name: str
    description: str = ""
    currency_code: str = "PLN"
    is_default: bool = False


class StageRead(BaseModel):
    id: uuid.UUID
    name: str
    pipeline_id: uuid.UUID
    sequence: int
    probability: float
    is_won: bool
    is_lost: bool
    fold: bool

    model_config = {"from_attributes": True}


class StageWrite(BaseModel):
    name: str
    pipeline_id: uuid.UUID
    sequence: int = 10
    probability: float = 0.0
    is_won: bool = False
    is_lost: bool = False
    fold: bool = False


class OpportunityRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    customer_id: uuid.UUID | None
    pipeline_id: uuid.UUID | None
    stage_id: uuid.UUID | None
    assigned_user_id: uuid.UUID | None
    expected_revenue: float
    probability: float
    close_date: str | None
    description: str | None
    lost_reason: str | None
    tags: list[str]
    workflow_run_id: str | None
    create_date: datetime | None = None

    model_config = {"from_attributes": True}


class OpportunityWrite(BaseModel):
    name: str
    customer_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    expected_revenue: float = 0.0
    probability: float = 0.0
    close_date: str | None = None
    description: str = ""
    tags: list[str] = []
