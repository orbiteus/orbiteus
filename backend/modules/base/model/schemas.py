"""Pydantic schemas for base module – used by auto-CRUD router."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class TenantRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    create_date: datetime | None = None

    model_config = {"from_attributes": True}


class TenantWrite(BaseModel):
    name: str
    slug: str
    plan: str = "free"


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class CompanyRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    currency_code: str
    country_code: str
    vat: str | None
    email: str | None
    city: str | None
    parent_company_id: uuid.UUID | None
    create_date: datetime | None = None

    model_config = {"from_attributes": True}


class CompanyWrite(BaseModel):
    name: str
    currency_code: str = "PLN"
    country_code: str = "PL"
    vat: str | None = None
    email: str | None = None
    phone: str | None = None
    street: str | None = None
    city: str | None = None
    zip_code: str | None = None
    parent_company_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Partner
# ---------------------------------------------------------------------------

class PartnerRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    email: str | None
    phone: str | None
    city: str | None
    country_code: str
    is_company: bool
    vat: str | None

    model_config = {"from_attributes": True}


class PartnerWrite(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    street: str | None = None
    city: str | None = None
    zip_code: str | None = None
    country_code: str = "PL"
    is_company: bool = False
    vat: str | None = None
    parent_partner_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    email: str
    name: str
    is_active: bool
    is_superadmin: bool
    language: str
    timezone: str
    totp_enabled: bool
    last_login: str | None

    model_config = {"from_attributes": True}


class UserWrite(BaseModel):
    email: str
    name: str
    password: str  # plain – hashed in service layer
    language: str = "pl"
    timezone: str = "Europe/Warsaw"


# ---------------------------------------------------------------------------
# ir_model
# ---------------------------------------------------------------------------

class IrModelRead(BaseModel):
    id: uuid.UUID
    model_name: str
    label: str | None
    module: str | None
    description: str | None
    is_transient: bool

    model_config = {"from_attributes": True}


class IrModelWrite(BaseModel):
    model_name: str
    label: str | None = None
    module: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# ir_model_field
# ---------------------------------------------------------------------------

class IrModelFieldRead(BaseModel):
    id: uuid.UUID
    model_name: str
    field_name: str
    field_type: str
    label: str | None
    required: bool
    readonly: bool
    is_custom: bool
    related_model: str | None

    model_config = {"from_attributes": True}


class IrModelFieldWrite(BaseModel):
    model_name: str
    field_name: str
    field_type: str
    label: str | None = None
    required: bool = False
    readonly: bool = False
    is_custom: bool = False
    related_model: str | None = None


# ---------------------------------------------------------------------------
# ir_model_access
# ---------------------------------------------------------------------------

class IrModelAccessRead(BaseModel):
    id: uuid.UUID
    model_name: str
    role_name: str
    perm_read: bool
    perm_write: bool
    perm_create: bool
    perm_unlink: bool

    model_config = {"from_attributes": True}


class IrModelAccessWrite(BaseModel):
    model_name: str
    role_name: str
    perm_read: bool = False
    perm_write: bool = False
    perm_create: bool = False
    perm_unlink: bool = False


# ---------------------------------------------------------------------------
# ir_rule
# ---------------------------------------------------------------------------

class IrRuleRead(BaseModel):
    id: uuid.UUID
    name: str
    model_name: str
    domain_force: str
    roles: list[str]
    is_global: bool

    model_config = {"from_attributes": True}


class IrRuleWrite(BaseModel):
    name: str
    model_name: str
    domain_force: str = "[]"
    roles: list[str] = []
    is_global: bool = False
    perm_read: bool = True
    perm_write: bool = True
    perm_create: bool = True
    perm_unlink: bool = True


# ---------------------------------------------------------------------------
# ir_ui_menu
# ---------------------------------------------------------------------------

class IrUiMenuRead(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    sequence: int
    icon: str | None
    groups: list[str]

    model_config = {"from_attributes": True}


class IrUiMenuWrite(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None
    sequence: int = 10
    action_id: uuid.UUID | None = None
    action_type: str = ""
    icon: str = ""
    groups: list[str] = []


# ---------------------------------------------------------------------------
# ir_sequence
# ---------------------------------------------------------------------------

class IrSequenceRead(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    prefix: str | None
    padding: int
    number_next: int

    model_config = {"from_attributes": True}


class IrSequenceWrite(BaseModel):
    name: str
    code: str
    prefix: str = ""
    suffix: str = ""
    padding: int = 5
    number_next: int = 1
    number_increment: int = 1


# ---------------------------------------------------------------------------
# ir_config_param
# ---------------------------------------------------------------------------

class IrConfigParamRead(BaseModel):
    id: uuid.UUID
    key: str
    value: str | None
    description: str | None
    groups: list[str]

    model_config = {"from_attributes": True}


class IrConfigParamWrite(BaseModel):
    key: str
    value: str = ""
    description: str = ""
    groups: list[str] = []


# ---------------------------------------------------------------------------
# ir_cron
# ---------------------------------------------------------------------------

class IrCronRead(BaseModel):
    id: uuid.UUID
    name: str
    model_name: str | None
    function_name: str | None
    interval_number: int
    interval_type: str
    is_active: bool
    next_call: str | None
    temporal_schedule_id: str | None

    model_config = {"from_attributes": True}


class IrCronWrite(BaseModel):
    name: str
    model_name: str | None = None
    function_name: str | None = None
    interval_number: int = 1
    interval_type: str = "hours"
    is_active: bool = True


# ---------------------------------------------------------------------------
# ir_ui_view
# ---------------------------------------------------------------------------

class IrUiViewRead(BaseModel):
    id: uuid.UUID
    name: str
    model: str
    type: str
    arch: str
    inherit_id: uuid.UUID | None
    priority: int
    active: bool
    module: str | None

    model_config = {"from_attributes": True}


class IrUiViewWrite(BaseModel):
    name: str
    model: str
    type: str = "form"
    arch: str = "<view/>"
    inherit_id: uuid.UUID | None = None
    priority: int = 16
    active: bool = True
    module: str = ""
