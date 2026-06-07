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
class User(BaseModel):
    """System user – can belong to multiple companies within a tenant."""

    email: str = ""
    name: str = ""
    password_hash: str = ""
    is_active: bool = True
    is_superadmin: bool = False
    company_ids: list[uuid.UUID] = field(default_factory=list)  # stored as JSONB
    role_ids: list[str] = field(default_factory=list)  # RBAC role codes, JSONB
    totp_secret: str | None = None
    totp_enabled: bool = False
    # PR final: bcrypt-hashed list of single-use TOTP recovery codes.
    recovery_codes_hashed: list[str] = field(default_factory=list)
    last_login: datetime | None = None
    last_login_device: str | None = None
    language: str = "en"
    timezone: str = "Europe/Warsaw"


# ---------------------------------------------------------------------------
# System / engine system objects
# ---------------------------------------------------------------------------

@dataclass
class RegistryModel(SystemModel):
    """Registered model metadata (populated by ModuleRegistry at startup)."""

    model_name: str = ""         # e.g. "crm.customer"
    label: str = ""              # Human-readable name
    module: str = ""             # Owning module name
    description: str = ""
    is_transient: bool = False   # True for wizard models


@dataclass
class RegistryModelField(SystemModel):
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
class Role(SystemModel):
    """Named RBAC group referenced by model access, record rules, and users."""

    name: str = ""
    code: str = ""  # technical id, e.g. base.group_system
    description: str | None = None
    is_system: bool = False
    active: bool = True


@dataclass
class ModelAccess(SystemModel):
    """RBAC: role → model → CRUD permissions."""

    model_name: str = ""
    role_name: str = ""
    perm_read: bool = False
    perm_write: bool = False
    perm_create: bool = False
    perm_unlink: bool = False


@dataclass
class RecordRule(SystemModel):
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
class UiMenu(SystemModel):
    """Menu tree – defines Admin UI navigation structure."""

    name: str = ""
    parent_id: uuid.UUID | None = None
    sequence: int = 10
    action_id: uuid.UUID | None = None
    action_type: str = ""        # base.action.window / base.action.server / …
    icon: str = ""
    groups: list[str] = field(default_factory=list)
    web_icon: str | None = None


@dataclass
class ConfigParam(SystemModel):
    """System-wide key-value configuration parameters."""

    key: str = ""
    value: str = ""
    description: str = ""
    groups: list[str] = field(default_factory=list)  # access groups


@dataclass
class UiTranslation(SystemModel):
    """UI message override (module packs + runtime customization)."""

    lang: str = ""
    module: str = ""       # contributing module or empty for global
    msg_key: str = ""      # e.g. common.save, nav.dashboard
    value: str = ""


@dataclass
class MailTemplate(SystemModel):
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
class UiView(SystemModel):
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
class Attachment(BaseModel):
    """File attachments – linked to any record."""

    name: str = ""
    res_model: str = ""          # e.g. "crm.customer"
    res_id: uuid.UUID | None = None
    mimetype: str = ""
    file_size: int = 0
    store_fname: str = ""        # path on disk or S3 key
    url: str | None = None
    description: str = ""


# ---------------------------------------------------------------------------
# Audit log (PR 3) — mandatory, opt-out only via AUDIT_OPTOUT_MODELS in
# orbiteus_core.repository.
# ---------------------------------------------------------------------------

@dataclass
class AuditLog(SystemModel):
    """One row per CRUD operation through `BaseRepository`.

    See `docs/14-audit.md` for the full policy.
    """

    tenant_id: uuid.UUID | None = None
    actor: str = "system"          # "user" | "ai" | "system"
    user_id: uuid.UUID | None = None
    request_id: str | None = None
    model: str = ""
    record_id: uuid.UUID | None = None
    operation: str = ""            # "create" | "update" | "delete" | "tool_call" | "login" | ...
    diff: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Outbox (PR 4) — durable side-effect queue committed with the business txn.
# Drained by Celery workers in PR 5. See docs/12-events-and-queues.md.
# ---------------------------------------------------------------------------

@dataclass
class Outbox(SystemModel):
    """Durable side-effect intent — drained by Celery workers."""

    tenant_id: uuid.UUID | None = None
    status: str = "pending"          # "pending" | "processing" | "done" | "dead"
    event: str = ""                  # logical name, e.g. "record.created"
    payload: dict[str, Any] = field(default_factory=dict)
    target_kind: str | None = None   # dispatcher hint: "webhook" | "email" | ...
    target_ref: str | None = None    # dispatcher ref: subscriber id / template id
    retries: int = 0
    next_run_at: datetime | None = None
    last_error: str | None = None


@dataclass
class Webhook(BaseModel):
    """Outbound webhook subscriber (Standard-Webhooks-style delivery)."""

    name: str = ""
    url: str = ""
    secret: str = ""                 # HMAC-SHA256 signing key
    event_mask: list[str] = field(default_factory=list)  # ["record.created", ...]
    # NULL → fan out for every business model in the tenant.
    # A dotted name like "crm.person" → only that model fires this webhook.
    model_filter: str | None = None
    # Only applies to "record.updated". Empty list → any field change fires.
    # Otherwise a delivery is enqueued only when at least one of the listed
    # fields appears in the payload's `diff` keys.
    field_filter: list[str] = field(default_factory=list)
    # Optional inbound-auth header on the receiver side, e.g.
    # `Authorization: Bearer xyz` or `X-Custom-Token: abc`. The HMAC
    # signature on `X-Orbiteus-Signature` is unconditional.
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    is_active: bool = True
    last_delivery_at: datetime | None = None
    last_delivery_status: str = ""


# ---------------------------------------------------------------------------
# AI layer (PR 8) — BYOK credentials, embeddings, prompts/dashboards.
# See docs/15-ai-layer.md and ADR-0004 / ADR-0005 / ADR-0009.
# ---------------------------------------------------------------------------

@dataclass
class AiCredential(SystemModel):
    """Per-tenant AI provider credential (BYOK, Fernet-encrypted at rest)."""

    tenant_id: uuid.UUID | None = None
    provider: str = "anthropic"      # "anthropic" | "openai" | "ollama" | "gemini"
    secret_encrypted: bytes = b""    # Fernet ciphertext of the API key
    model_default: str = ""          # e.g. "claude-3-5-sonnet"
    is_active: bool = True
    monthly_token_budget: int | None = None
    usage_tokens: int = 0


@dataclass
class EmbeddingRecord(SystemModel):
    """pgvector row keyed by (tenant_id, model, record_id, provider, model_name)."""

    tenant_id: uuid.UUID | None = None
    model: str = ""                  # e.g. "crm.lead"
    record_id: uuid.UUID | None = None
    provider: str = ""
    model_name: str = ""             # provider-side model used for embedding
    dim: int = 0
    # `vector` column is an actual pgvector value; we leave it as bytes-ish here
    # so callers that don't load pgvector still see the dataclass shape.
    vector: Any = None


@dataclass
class Agent(BaseModel):
    """Named AI persona with scoped tools — framework primitive (ADR-0018)."""

    slug: str = ""
    name: str = ""
    module_scope: str = "*"          # module name or "*" for all enabled modules
    system_prompt: str = ""
    allowed_models: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    provider: str | None = None      # optional BYOK provider override
    model_default: str | None = None
    is_system: bool = False
    can_delegate: bool = False
    allowed_delegate_slugs: list[str] = field(default_factory=list)
    schedule_interval_minutes: int | None = None
    schedule_prompt: str = ""
    schedule_last_run_at: datetime | None = None


@dataclass
class AgentRun(BaseModel):
    """One execution of a `base.agent` definition."""

    agent_id: uuid.UUID | None = None
    parent_run_id: uuid.UUID | None = None
    depth: int = 0
    triggered_by_user_id: uuid.UUID | None = None
    input_prompt: str = ""
    status: str = "pending"          # pending | running | completed | failed
    output_text: str | None = None
    tool_trace: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    error_message: str | None = None
