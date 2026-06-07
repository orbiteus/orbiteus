"""Base module – SQLAlchemy imperative mapping.

All tables are registered in the shared `metadata` from orbiteus_core.db.
All domain classes are mapped imperatively (no DeclarativeBase).
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.auto_router import register_model
from orbiteus_core.db import metadata
from orbiteus_core.mapper import (
    make_base_columns,
    make_system_columns,
    register_mapping,
)

from modules.base.model.domain import (
    Company,
    AiCredential,
    Attachment,
    AuditLog,
    ConfigParam,
    UiTranslation,
    EmbeddingRecord,
    Agent,
    AgentRun,
    MailTemplate,
    RegistryModel,
    ModelAccess,
    RegistryModelField,
    Outbox,
    RecordRule,
    Role,
    UiMenu,
    UiView,
    Webhook,
    Tenant,
    User,
)
from modules.base.model import schemas


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

tenants_table = Table(
    "base_tenants",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("slug", String(100), nullable=False, unique=True),
    Column("plan", String(50), nullable=False, server_default="free"),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("settings", JSON, nullable=False, server_default="{}"),
)

companies_table = Table(
    "base_companies",
    metadata,
    *make_base_columns(),
    Column("name", String(255), nullable=False),
    Column("currency_code", String(10), nullable=False, server_default="PLN"),
    Column("country_code", String(5), nullable=False, server_default="PL"),
    Column("vat", String(50)),
    Column("email", String(255)),
    Column("phone", String(50)),
    Column("street", String(255)),
    Column("city", String(100)),
    Column("zip_code", String(20)),
    Column("parent_company_id", UUID(as_uuid=True), ForeignKey("base_companies.id"), nullable=True),
    Column("logo_url", String(500)),
    Column("settings", JSON, nullable=False, server_default="{}"),
)

users_table = Table(
    "base_users",
    metadata,
    *make_base_columns(),
    Column("email", String(255), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("is_superadmin", Boolean, nullable=False, server_default="false"),
    Column("company_ids", JSON, nullable=False, server_default="[]"),
    Column("role_ids", JSON, nullable=False, server_default="[]"),
    Column("totp_secret", String(64)),
    Column("totp_enabled", Boolean, server_default="false"),
    # JSON list of bcrypt-hashed one-time recovery codes (PR final).
    Column("recovery_codes_hashed", JSON, nullable=False, server_default="[]"),
    Column("last_login", DateTime(timezone=True)),
    Column("last_login_device", String(20)),
    Column("language", String(10), server_default="en"),
    Column("timezone", String(50), server_default="Europe/Warsaw"),
)

user_roles_table = Table(
    "base_user_roles",
    metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("base_users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("base_roles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

# ---------------------------------------------------------------------------
# base engine system tables
# ---------------------------------------------------------------------------

base_models_table = Table(
    "base_models",
    metadata,
    *make_system_columns(),
    Column("model_name", String(255), nullable=False, unique=True),
    Column("label", String(255)),
    Column("module", String(100)),
    Column("description", Text),
    Column("is_transient", Boolean, server_default="false"),
)

base_model_fields_table = Table(
    "base_model_fields",
    metadata,
    *make_system_columns(),
    Column("model_id", UUID(as_uuid=True), ForeignKey("base_models.id"), nullable=False),
    Column("model_name", String(255), nullable=False, index=True),
    Column("field_name", String(255), nullable=False),
    Column("field_type", String(50), nullable=False),
    Column("label", String(255)),
    Column("required", Boolean, server_default="false"),
    Column("readonly", Boolean, server_default="false"),
    Column("is_custom", Boolean, server_default="false"),
    Column("selection_values", JSON, server_default="[]"),
    Column("related_model", String(255)),
)

base_roles_table = Table(
    "base_roles",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("code", String(255), nullable=False, unique=True, index=True),
    Column("description", Text),
    Column("is_system", Boolean, nullable=False, server_default="false"),
    Column("active", Boolean, nullable=False, server_default="true"),
)

base_model_access_table = Table(
    "base_model_access",
    metadata,
    *make_system_columns(),
    Column("model_name", String(255), nullable=False, index=True),
    Column("role_name", String(255), nullable=False, index=True),
    Column("perm_read", Boolean, server_default="false"),
    Column("perm_write", Boolean, server_default="false"),
    Column("perm_create", Boolean, server_default="false"),
    Column("perm_unlink", Boolean, server_default="false"),
)

base_rules_table = Table(
    "base_rules",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("model_name", String(255), nullable=False, index=True),
    Column("domain_force", Text, server_default="[]"),
    Column("roles", JSON, server_default="[]"),
    Column("is_global", Boolean, server_default="false"),
    Column("perm_read", Boolean, server_default="true"),
    Column("perm_write", Boolean, server_default="true"),
    Column("perm_create", Boolean, server_default="true"),
    Column("perm_unlink", Boolean, server_default="true"),
)

base_ui_menus_table = Table(
    "base_ui_menus",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("parent_id", UUID(as_uuid=True), ForeignKey("base_ui_menus.id"), nullable=True),
    Column("sequence", Integer, server_default="10"),
    Column("action_id", UUID(as_uuid=True), nullable=True),
    Column("action_type", String(100)),
    Column("icon", String(100)),
    Column("groups", JSON, server_default="[]"),
    Column("web_icon", String(255)),
)

base_config_params_table = Table(
    "base_config_params",
    metadata,
    *make_system_columns(),
    Column("key", String(255), nullable=False, unique=True),
    Column("value", Text),
    Column("description", Text),
    Column("groups", JSON, server_default="[]"),
)

base_ui_translations_table = Table(
    "base_ui_translations",
    metadata,
    *make_system_columns(),
    Column("lang", String(16), nullable=False, index=True),
    Column("module", String(100), nullable=False, server_default=""),
    Column("msg_key", String(255), nullable=False, index=True),
    Column("value", Text, nullable=False, server_default=""),
)

base_mail_templates_table = Table(
    "base_mail_templates",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("model_name", String(255)),
    Column("subject", String(500)),
    Column("body_html", Text),
    Column("from_email", String(255)),
    Column("reply_to", String(255)),
    Column("lang", String(100)),
    Column("auto_delete", Boolean, server_default="true"),
)

base_ui_views_table = Table(
    "base_ui_views",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False, unique=True),
    Column("model", String(255), nullable=False, index=True),
    Column("type", String(50), nullable=False, server_default="form"),
    Column("arch", Text, nullable=False, server_default="<view/>"),
    Column("inherit_id", UUID(as_uuid=True), ForeignKey("base_ui_views.id"), nullable=True),
    Column("priority", Integer, server_default="16"),
    Column("active", Boolean, server_default="true"),
    Column("module", String(100)),
)

base_attachments_table = Table(
    "base_attachments",
    metadata,
    *make_base_columns(),
    Column("name", String(255), nullable=False),
    Column("res_model", String(255), index=True),
    Column("res_id", UUID(as_uuid=True), index=True),
    Column("mimetype", String(255)),
    Column("file_size", Integer, server_default="0"),
    Column("store_fname", String(500)),
    Column("url", String(1000)),
    Column("description", Text),
)

base_audit_log_table = Table(
    "base_audit_log",
    metadata,
    *make_system_columns(),
    Column("tenant_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("actor", String(20), nullable=False, server_default="system"),
    Column("user_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("request_id", String(64), nullable=True, index=True),
    Column("model", String(255), nullable=False, index=True),
    Column("record_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("operation", String(50), nullable=False, index=True),
    Column("diff", JSON, nullable=False, server_default="{}"),
    # `metadata` column intentionally; SQLAlchemy reserves the `Table.metadata`
    # *attribute*, not column names. We map it on the domain class via the
    # `properties` dict in register_mapping when needed.
    Column("metadata", JSON, nullable=False, server_default="{}"),
)

base_outbox_table = Table(
    "base_outbox",
    metadata,
    *make_system_columns(),
    Column("tenant_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("status", String(20), nullable=False, server_default="pending", index=True),
    Column("event", String(255), nullable=False, index=True),
    Column("payload", JSON, nullable=False, server_default="{}"),
    Column("target_kind", String(50), nullable=True, index=True),
    Column("target_ref", String(255), nullable=True),
    Column("retries", Integer, nullable=False, server_default="0"),
    Column("next_run_at", String(50), nullable=True, index=True),
    # last_error stays a Text — Postgres truncates anything sane.
    Column("last_error", Text, nullable=True),
)

base_webhooks_table = Table(
    "base_webhooks",
    metadata,
    *make_base_columns(),
    Column("name", String(255), nullable=False),
    Column("url", String(2048), nullable=False),
    Column("secret", String(255), nullable=False),
    # JSON list of event names this subscriber listens to (e.g. "record.created").
    Column("event_mask", JSON, nullable=False, server_default="[]"),
    # NULL → match every model in the tenant. Dotted name → exact match.
    Column("model_filter", String(128), nullable=True),
    # JSON list of fields that trigger `record.updated`. Empty list → any.
    Column("field_filter", JSON, nullable=False, server_default="[]"),
    # Optional inbound-auth header for receivers that gate webhooks
    # behind a header (Authorization, X-Token, etc.). HMAC signing is
    # unconditional, regardless of these.
    Column("auth_header_name", String(64), nullable=True),
    Column("auth_header_value", String(512), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("last_delivery_at", String(50), nullable=True),
    Column("last_delivery_status", String(50), nullable=True),
)


# AI BYOK credentials. `secret_encrypted` is Fernet ciphertext.
# A unique constraint on (tenant_id, provider) is created in the migration.
base_ai_credentials_table = Table(
    "base_ai_credentials",
    metadata,
    *make_system_columns(),
    Column("tenant_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("provider", String(50), nullable=False),
    Column("secret_encrypted", LargeBinary, nullable=False),
    Column("model_default", String(255), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("monthly_token_budget", Integer, nullable=True),
    Column("usage_tokens", Integer, nullable=False, server_default="0"),
)


# pgvector embeddings store. The `vector` column type is registered when the
# extension is installed (see migrations); we declare it as `Text` here for
# environments that don't have pgvector loaded yet — production migration
# upgrades it to `vector(N)` with an HNSW index.
base_embeddings_table = Table(
    "base_embeddings",
    metadata,
    *make_system_columns(),
    Column("tenant_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("model", String(255), nullable=False, index=True),
    Column("record_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("provider", String(50), nullable=False),
    Column("model_name", String(255), nullable=False),
    Column("dim", Integer, nullable=False, server_default="0"),
    Column("vector", Text, nullable=True),
)

base_agents_table = Table(
    "base_agents",
    metadata,
    *make_base_columns(),
    Column("slug", String(100), nullable=False),
    Column("name", String(255), nullable=False),
    Column("module_scope", String(100), nullable=False, server_default="*"),
    Column("system_prompt", Text, nullable=False, server_default=""),
    Column("allowed_models", JSON, nullable=False, server_default="[]"),
    Column("allowed_actions", JSON, nullable=False, server_default="[]"),
    Column("provider", String(50), nullable=True),
    Column("model_default", String(255), nullable=True),
    Column("is_system", Boolean, nullable=False, server_default="false"),
    Column("can_delegate", Boolean, nullable=False, server_default="false"),
    Column("allowed_delegate_slugs", JSON, nullable=False, server_default="[]"),
    Column("schedule_interval_minutes", Integer, nullable=True),
    Column("schedule_prompt", Text, nullable=False, server_default=""),
    Column("schedule_last_run_at", DateTime(timezone=True), nullable=True),
)

base_agent_runs_table = Table(
    "base_agent_runs",
    metadata,
    *make_base_columns(),
    Column("agent_id", UUID(as_uuid=True), ForeignKey("base_agents.id"), nullable=False, index=True),
    Column("parent_run_id", UUID(as_uuid=True), ForeignKey("base_agent_runs.id"), nullable=True, index=True),
    Column("depth", Integer, nullable=False, server_default="0"),
    Column("triggered_by_user_id", UUID(as_uuid=True), nullable=True, index=True),
    Column("input_prompt", Text, nullable=False, server_default=""),
    Column("status", String(32), nullable=False, server_default="pending"),
    Column("output_text", Text, nullable=True),
    Column("tool_trace", JSON, nullable=False, server_default="[]"),
    Column("tokens_used", Integer, nullable=False, server_default="0"),
    Column("error_message", Text, nullable=True),
)


# ---------------------------------------------------------------------------
# Register imperative mappings
# ---------------------------------------------------------------------------

def setup() -> None:
    """Called by ModuleRegistry during module load."""
    register_mapping(Tenant, tenants_table)
    register_mapping(Company, companies_table)
    register_mapping(User, users_table)
    register_mapping(RegistryModel, base_models_table)
    register_mapping(RegistryModelField, base_model_fields_table)
    register_mapping(Role, base_roles_table)
    register_mapping(ModelAccess, base_model_access_table)
    register_mapping(RecordRule, base_rules_table)
    register_mapping(UiMenu, base_ui_menus_table)
    register_mapping(ConfigParam, base_config_params_table)
    register_mapping(UiTranslation, base_ui_translations_table)
    register_mapping(MailTemplate, base_mail_templates_table)
    register_mapping(Attachment, base_attachments_table)
    register_mapping(UiView, base_ui_views_table)
    register_mapping(AuditLog, base_audit_log_table)
    register_mapping(Outbox, base_outbox_table)
    register_mapping(Webhook, base_webhooks_table)
    register_mapping(AiCredential, base_ai_credentials_table)
    register_mapping(EmbeddingRecord, base_embeddings_table)
    register_mapping(Agent, base_agents_table)
    register_mapping(AgentRun, base_agent_runs_table)

    _register_auto_crud()


def _register_auto_crud() -> None:
    from modules.base.controller.repositories import (
        AgentRepository,
        AgentRunRepository,
        CompanyRepository,
        ConfigParamRepository,
        UiTranslationRepository,
        ModelAccessRepository,
        RoleRepository,
        RegistryModelFieldRepository,
        RegistryModelRepository,
        RecordRuleRepository,
        UiMenuRepository,
        UiViewRepository,
        TenantRepository,
        UserRepository,
    )

    register_model("base.tenant", Tenant, TenantRepository, tenants_table,
                   schemas.TenantRead, schemas.TenantWrite)
    register_model("base.company", Company, CompanyRepository, companies_table,
                   schemas.CompanyRead, schemas.CompanyWrite)
    register_model("base.user", User, UserRepository, users_table,
                   schemas.UserRead, schemas.UserWrite)
    register_model("base.registry-model", RegistryModel, RegistryModelRepository, base_models_table,
                   schemas.RegistryModelRead, schemas.RegistryModelWrite)
    register_model("base.registry-model-field", RegistryModelField, RegistryModelFieldRepository,
                   base_model_fields_table, schemas.RegistryModelFieldRead, schemas.RegistryModelFieldWrite)
    register_model("base.role", Role, RoleRepository, base_roles_table,
                   schemas.RoleRead, schemas.RoleWrite)
    register_model("base.model-access", ModelAccess, ModelAccessRepository,
                   base_model_access_table, schemas.ModelAccessRead, schemas.ModelAccessWrite)
    register_model("base.record-rule", RecordRule, RecordRuleRepository, base_rules_table,
                   schemas.RecordRuleRead, schemas.RecordRuleWrite)
    register_model("base.ui-menu", UiMenu, UiMenuRepository, base_ui_menus_table,
                   schemas.UiMenuRead, schemas.UiMenuWrite)
    register_model("base.config-param", ConfigParam, ConfigParamRepository,
                   base_config_params_table, schemas.ConfigParamRead, schemas.ConfigParamWrite)
    register_model("base.ui-translation", UiTranslation, UiTranslationRepository,
                   base_ui_translations_table, schemas.UiTranslationRead, schemas.UiTranslationWrite)
    register_model("base.ui-view", UiView, UiViewRepository, base_ui_views_table,
                   schemas.UiViewRead, schemas.UiViewWrite)
    register_model("base.agent", Agent, AgentRepository, base_agents_table,
                   schemas.AgentRead, schemas.AgentWrite)
    register_model("base.agent-run", AgentRun, AgentRunRepository, base_agent_runs_table,
                   schemas.AgentRunRead, schemas.AgentRunWrite)
