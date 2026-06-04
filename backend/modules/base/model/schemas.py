"""Pydantic schemas for base module – used by auto-CRUD router."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


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
    last_login: datetime | None = None
    last_login_device: str | None = None
    company_ids: list[uuid.UUID] = Field(default_factory=list)
    role_ids: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserWrite(BaseModel):
    email: str
    name: str
    password: str | None = None  # required on create; hashed in UserRepository
    language: str = "en"
    timezone: str = "Europe/Warsaw"
    is_active: bool = True
    company_ids: list[uuid.UUID] = Field(default_factory=list)
    role_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Role (RBAC group)
# ---------------------------------------------------------------------------

class RoleRead(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    description: str | None
    is_system: bool
    active: bool

    model_config = {"from_attributes": True}


class RoleWrite(BaseModel):
    name: str
    code: str
    description: str | None = None


# ---------------------------------------------------------------------------
# registry model metadata
# ---------------------------------------------------------------------------

class RegistryModelRead(BaseModel):
    id: uuid.UUID
    model_name: str
    label: str | None
    module: str | None
    description: str | None
    is_transient: bool

    model_config = {"from_attributes": True}


class RegistryModelWrite(BaseModel):
    model_name: str
    label: str | None = None
    module: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# registry model metadata_field
# ---------------------------------------------------------------------------

class RegistryModelFieldRead(BaseModel):
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


class RegistryModelFieldWrite(BaseModel):
    model_name: str
    field_name: str
    field_type: str
    label: str | None = None
    required: bool = False
    readonly: bool = False
    is_custom: bool = False
    related_model: str | None = None


# ---------------------------------------------------------------------------
# base_model_access
# ---------------------------------------------------------------------------

class ModelAccessRead(BaseModel):
    id: uuid.UUID
    model_name: str
    role_name: str
    perm_read: bool
    perm_write: bool
    perm_create: bool
    perm_unlink: bool

    model_config = {"from_attributes": True}


class ModelAccessWrite(BaseModel):
    model_name: str
    role_name: str
    perm_read: bool = False
    perm_write: bool = False
    perm_create: bool = False
    perm_unlink: bool = False


# ---------------------------------------------------------------------------
# record rule
# ---------------------------------------------------------------------------

class RecordRuleRead(BaseModel):
    id: uuid.UUID
    name: str
    model_name: str
    domain_force: str
    roles: list[str]
    is_global: bool

    model_config = {"from_attributes": True}


class RecordRuleWrite(BaseModel):
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
# ui menu
# ---------------------------------------------------------------------------

class UiMenuRead(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    sequence: int
    icon: str | None
    groups: list[str]

    model_config = {"from_attributes": True}


class UiMenuWrite(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None
    sequence: int = 10
    action_id: uuid.UUID | None = None
    action_type: str = ""
    icon: str = ""
    groups: list[str] = []


# ---------------------------------------------------------------------------
# config param
# ---------------------------------------------------------------------------

class ConfigParamRead(BaseModel):
    id: uuid.UUID
    key: str
    value: str | None
    description: str | None
    groups: list[str]

    model_config = {"from_attributes": True}


class ConfigParamWrite(BaseModel):
    key: str
    value: str = ""
    description: str = ""
    groups: list[str] = []


# ---------------------------------------------------------------------------
# ui translation
# ---------------------------------------------------------------------------

class UiTranslationRead(BaseModel):
    id: uuid.UUID
    lang: str
    module: str
    msg_key: str
    value: str

    model_config = {"from_attributes": True}


class UiTranslationWrite(BaseModel):
    lang: str
    module: str = ""
    msg_key: str
    value: str = ""


# ---------------------------------------------------------------------------
# ui view
# ---------------------------------------------------------------------------

class UiViewRead(BaseModel):
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


class UiViewWrite(BaseModel):
    name: str
    model: str
    type: str = "form"
    arch: str = "<view/>"
    inherit_id: uuid.UUID | None = None
    priority: int = 16
    active: bool = True
    module: str = ""


# ---------------------------------------------------------------------------
# AI agents (ADR-0018)
# ---------------------------------------------------------------------------

class AgentRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    module_scope: str
    system_prompt: str
    allowed_models: list[str]
    allowed_actions: list[str]
    provider: str | None
    model_default: str | None
    is_system: bool
    can_delegate: bool
    allowed_delegate_slugs: list[str]
    schedule_interval_minutes: int | None
    schedule_prompt: str
    schedule_last_run_at: datetime | None
    active: bool

    model_config = {"from_attributes": True}


class AgentWrite(BaseModel):
    slug: str
    name: str
    module_scope: str = "*"
    system_prompt: str = ""
    allowed_models: list[str] = []
    allowed_actions: list[str] = []
    provider: str | None = None
    model_default: str | None = None
    can_delegate: bool = False
    allowed_delegate_slugs: list[str] = []
    schedule_interval_minutes: int | None = None
    schedule_prompt: str = ""
    active: bool = True


class AgentRunRead(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    parent_run_id: uuid.UUID | None
    depth: int
    triggered_by_user_id: uuid.UUID | None
    input_prompt: str
    status: str
    output_text: str | None
    tool_trace: list[dict]
    tokens_used: int
    error_message: str | None
    active: bool

    model_config = {"from_attributes": True}


class AgentRunWrite(BaseModel):
    agent_id: uuid.UUID
    input_prompt: str = ""
    status: str = "pending"
    output_text: str | None = None
    tool_trace: list[dict] = []
    tokens_used: int = 0
    error_message: str | None = None
