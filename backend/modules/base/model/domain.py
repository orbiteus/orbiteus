"""Base module domain models – pure Python dataclasses, no ORM dependency."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from orbiteus_core.base_domain import BaseModel, SystemModel


# ---------------------------------------------------------------------------
# Core business entities
# ---------------------------------------------------------------------------

@dataclass
class Tenant(SystemModel):
    """An isolated organizational unit (top-level multi-tenancy boundary)."""

    name: str = ""
    slug: str = ""  # URL-safe identifier
    plan: str = "free"  # free / starter / professional / enterprise
    is_active: bool = True
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class Company(BaseModel):
    """A legal entity within a Tenant. Users can belong to multiple companies."""

    name: str = ""
    currency_code: str = "PLN"
    country_code: str = "PL"
    vat: str = ""
    email: str = ""
    phone: str = ""
    street: str = ""
    city: str = ""
    zip_code: str = ""
    parent_company_id: uuid.UUID | None = None
    logo_url: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class Partner(BaseModel):
    """Contacts/partners – reusable across CRM, HR, Accounting, etc."""

    name: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    street: str = ""
    city: str = ""
    zip_code: str = ""
    country_code: str = "PL"
    is_company: bool = False
    vat: str = ""
    parent_partner_id: uuid.UUID | None = None
    company_name: str = ""


@dataclass
class User(BaseModel):
    """System user – can belong to multiple companies within a tenant."""

    email: str = ""
    name: str = ""
    password_hash: str = ""
    is_active: bool = True
    is_superadmin: bool = False
    partner_id: uuid.UUID | None = None
    company_ids: list[uuid.UUID] = field(default_factory=list)  # stored as JSONB
    role_ids: list[uuid.UUID] = field(default_factory=list)     # stored as JSONB
    totp_secret: str | None = None
    totp_enabled: bool = False
    last_login: datetime | None = None
    language: str = "pl"
    timezone: str = "Europe/Warsaw"


# ---------------------------------------------------------------------------
# System / ir_* objects
# ---------------------------------------------------------------------------

@dataclass
class IrModel(SystemModel):
    """Registered model metadata (populated by ModuleRegistry at startup)."""

    model_name: str = ""         # e.g. "crm.customer"
    label: str = ""              # Human-readable name
    module: str = ""             # Owning module name
    description: str = ""
    is_transient: bool = False   # True for wizard models


@dataclass
class IrModelField(SystemModel):
    """Field metadata for registered models."""

    model_id: uuid.UUID = field(default_factory=uuid.uuid4)
    model_name: str = ""
    field_name: str = ""
    field_type: str = ""         # char, integer, float, boolean, date, datetime, many2one, …
    label: str = ""
    required: bool = False
    readonly: bool = False
    is_custom: bool = False      # True = added via admin UI (stored in JSONB)
    selection_values: list[dict] = field(default_factory=list)
    related_model: str | None = None


@dataclass
class IrModelAccess(SystemModel):
    """RBAC: role → model → CRUD permissions."""

    model_name: str = ""
    role_name: str = ""
    perm_read: bool = False
    perm_write: bool = False
    perm_create: bool = False
    perm_unlink: bool = False


@dataclass
class IrRule(SystemModel):
    """Record rules – domain-based row-level filters per role."""

    name: str = ""
    model_name: str = ""
    domain_force: str = "[]"     # JSON-serialized domain list
    roles: list[str] = field(default_factory=list)  # empty = global
    is_global: bool = False
    perm_read: bool = True
    perm_write: bool = True
    perm_create: bool = True
    perm_unlink: bool = True


@dataclass
class IrUiMenu(SystemModel):
    """Menu tree – defines Admin UI navigation structure."""

    name: str = ""
    parent_id: uuid.UUID | None = None
    sequence: int = 10
    action_id: uuid.UUID | None = None
    action_type: str = ""        # ir.action.window / ir.action.server / …
    icon: str = ""
    groups: list[str] = field(default_factory=list)
    web_icon: str | None = None


@dataclass
class IrActionWindow(SystemModel):
    """Window action – links a menu item to a model view."""

    name: str = ""
    model_name: str = ""
    view_mode: str = "list,form"
    domain: str = "[]"
    context: str = "{}"
    target: str = "current"      # current / new / inline


@dataclass
class IrActionServer(SystemModel):
    """Server action – executes Python code or triggers a Temporal workflow."""

    name: str = ""
    model_name: str = ""
    code: str = ""               # Python snippet or Temporal workflow name
    action_type: str = "code"    # code / temporal_workflow
    workflow_name: str | None = None


@dataclass
class IrSequence(SystemModel):
    """Named sequences for document numbering (INV/2024/00001)."""

    name: str = ""
    code: str = ""               # e.g. "account.invoice"
    prefix: str = ""
    suffix: str = ""
    padding: int = 5
    number_next: int = 1
    number_increment: int = 1
    use_date_range: bool = False


@dataclass
class IrConfigParam(SystemModel):
    """System-wide key-value configuration parameters."""

    key: str = ""
    value: str = ""
    description: str = ""
    groups: list[str] = field(default_factory=list)  # access groups


@dataclass
class IrCron(SystemModel):
    """Scheduled actions – mapped to Temporal schedules."""

    name: str = ""
    model_name: str = ""
    function_name: str = ""      # Python function or Temporal workflow
    args: str = "[]"
    kwargs: str = "{}"
    interval_number: int = 1
    interval_type: str = "hours"  # minutes / hours / days / weeks / months
    is_active: bool = True
    next_call: datetime | None = None
    temporal_schedule_id: str | None = None


@dataclass
class IrMailTemplate(SystemModel):
    """Email templates using Jinja2."""

    name: str = ""
    model_name: str = ""
    subject: str = ""
    body_html: str = ""
    from_email: str = ""
    reply_to: str = ""
    lang: str = ""               # Jinja2 expression for language
    auto_delete: bool = True


@dataclass
class IrUiView(SystemModel):
    """UI view definitions – XML arch stored in DB, supports XPath inheritance."""

    name: str = ""            # e.g. "crm.customer.form"
    model: str = ""           # e.g. "crm.customer"
    type: str = "form"        # form / list / kanban / calendar / search
    arch: str = "<view/>"     # XML content (raw string)
    inherit_id: uuid.UUID | None = None   # parent view id (for inherited views)
    priority: int = 16        # lower = higher priority; base views use 16, inherit views use 100
    active: bool = True
    module: str = ""          # owning module name


@dataclass
class IrAttachment(BaseModel):
    """File attachments – linked to any record."""

    name: str = ""
    res_model: str = ""          # e.g. "crm.customer"
    res_id: uuid.UUID | None = None
    mimetype: str = ""
    file_size: int = 0
    store_fname: str = ""        # path on disk or S3 key
    url: str | None = None
    description: str = ""
