"""Base module – SQLAlchemy imperative mapping.

All tables are registered in the shared `metadata` from orbiteus_core.db.
All domain classes are mapped imperatively (no DeclarativeBase).
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
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

from modules.base.domain import (
    Company,
    IrActionServer,
    IrActionWindow,
    IrAttachment,
    IrConfigParam,
    IrCron,
    IrMailTemplate,
    IrModel,
    IrModelAccess,
    IrModelField,
    IrRule,
    IrSequence,
    IrUiMenu,
    Partner,
    Tenant,
    User,
)
from modules.base import schemas


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

partners_table = Table(
    "base_partners",
    metadata,
    *make_base_columns(),
    Column("name", String(255), nullable=False),
    Column("email", String(255)),
    Column("phone", String(50)),
    Column("mobile", String(50)),
    Column("street", String(255)),
    Column("city", String(100)),
    Column("zip_code", String(20)),
    Column("country_code", String(5), server_default="PL"),
    Column("is_company", Boolean, server_default="false"),
    Column("vat", String(50)),
    Column("parent_partner_id", UUID(as_uuid=True), ForeignKey("base_partners.id"), nullable=True),
    Column("company_name", String(255)),
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
    Column("partner_id", UUID(as_uuid=True), ForeignKey("base_partners.id"), nullable=True),
    Column("company_ids", JSON, nullable=False, server_default="[]"),
    Column("role_ids", JSON, nullable=False, server_default="[]"),
    Column("totp_secret", String(64)),
    Column("totp_enabled", Boolean, server_default="false"),
    Column("last_login", String(50)),  # stored as ISO string for simplicity
    Column("language", String(10), server_default="pl"),
    Column("timezone", String(50), server_default="Europe/Warsaw"),
)

# ---------------------------------------------------------------------------
# ir_* system tables
# ---------------------------------------------------------------------------

ir_models_table = Table(
    "ir_models",
    metadata,
    *make_system_columns(),
    Column("model_name", String(255), nullable=False, unique=True),
    Column("label", String(255)),
    Column("module", String(100)),
    Column("description", Text),
    Column("is_transient", Boolean, server_default="false"),
)

ir_model_fields_table = Table(
    "ir_model_fields",
    metadata,
    *make_system_columns(),
    Column("model_id", UUID(as_uuid=True), ForeignKey("ir_models.id"), nullable=False),
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

ir_model_access_table = Table(
    "ir_model_access",
    metadata,
    *make_system_columns(),
    Column("model_name", String(255), nullable=False, index=True),
    Column("role_name", String(255), nullable=False, index=True),
    Column("perm_read", Boolean, server_default="false"),
    Column("perm_write", Boolean, server_default="false"),
    Column("perm_create", Boolean, server_default="false"),
    Column("perm_unlink", Boolean, server_default="false"),
)

ir_rules_table = Table(
    "ir_rules",
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

ir_ui_menus_table = Table(
    "ir_ui_menus",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("parent_id", UUID(as_uuid=True), ForeignKey("ir_ui_menus.id"), nullable=True),
    Column("sequence", Integer, server_default="10"),
    Column("action_id", UUID(as_uuid=True), nullable=True),
    Column("action_type", String(100)),
    Column("icon", String(100)),
    Column("groups", JSON, server_default="[]"),
    Column("web_icon", String(255)),
)

ir_action_windows_table = Table(
    "ir_action_windows",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("model_name", String(255), nullable=False),
    Column("view_mode", String(100), server_default="list,form"),
    Column("domain", Text, server_default="[]"),
    Column("context", Text, server_default="{}"),
    Column("target", String(50), server_default="current"),
)

ir_action_servers_table = Table(
    "ir_action_servers",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("model_name", String(255), nullable=False),
    Column("code", Text),
    Column("action_type", String(50), server_default="code"),
    Column("workflow_name", String(255)),
)

ir_sequences_table = Table(
    "ir_sequences",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("code", String(100), nullable=False, unique=True),
    Column("prefix", String(50)),
    Column("suffix", String(50)),
    Column("padding", Integer, server_default="5"),
    Column("number_next", Integer, server_default="1"),
    Column("number_increment", Integer, server_default="1"),
    Column("use_date_range", Boolean, server_default="false"),
)

ir_config_params_table = Table(
    "ir_config_params",
    metadata,
    *make_system_columns(),
    Column("key", String(255), nullable=False, unique=True),
    Column("value", Text),
    Column("description", Text),
    Column("groups", JSON, server_default="[]"),
)

ir_crons_table = Table(
    "ir_crons",
    metadata,
    *make_system_columns(),
    Column("name", String(255), nullable=False),
    Column("model_name", String(255)),
    Column("function_name", String(255)),
    Column("args", Text, server_default="[]"),
    Column("kwargs", Text, server_default="{}"),
    Column("interval_number", Integer, server_default="1"),
    Column("interval_type", String(20), server_default="hours"),
    Column("is_active", Boolean, server_default="true"),
    Column("next_call", String(50)),
    Column("temporal_schedule_id", String(255)),
)

ir_mail_templates_table = Table(
    "ir_mail_templates",
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

ir_attachments_table = Table(
    "ir_attachments",
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


# ---------------------------------------------------------------------------
# Register imperative mappings
# ---------------------------------------------------------------------------

def setup() -> None:
    """Called by ModuleRegistry during module load."""
    register_mapping(Tenant, tenants_table)
    register_mapping(Company, companies_table)
    register_mapping(Partner, partners_table)
    register_mapping(User, users_table)
    register_mapping(IrModel, ir_models_table)
    register_mapping(IrModelField, ir_model_fields_table)
    register_mapping(IrModelAccess, ir_model_access_table)
    register_mapping(IrRule, ir_rules_table)
    register_mapping(IrUiMenu, ir_ui_menus_table)
    register_mapping(IrActionWindow, ir_action_windows_table)
    register_mapping(IrActionServer, ir_action_servers_table)
    register_mapping(IrSequence, ir_sequences_table)
    register_mapping(IrConfigParam, ir_config_params_table)
    register_mapping(IrCron, ir_crons_table)
    register_mapping(IrMailTemplate, ir_mail_templates_table)
    register_mapping(IrAttachment, ir_attachments_table)

    # Register models for auto-CRUD
    _register_auto_crud()


def _register_auto_crud() -> None:
    from modules.base import schemas

    register_model("base.tenant", Tenant, TenantRepository, tenants_table,
                   schemas.TenantRead, schemas.TenantWrite)
    register_model("base.company", Company, CompanyRepository, companies_table,
                   schemas.CompanyRead, schemas.CompanyWrite)
    register_model("base.partner", Partner, PartnerRepository, partners_table,
                   schemas.PartnerRead, schemas.PartnerWrite)
    register_model("base.user", User, UserRepository, users_table,
                   schemas.UserRead, schemas.UserWrite)
    register_model("base.ir-model", IrModel, IrModelRepository, ir_models_table,
                   schemas.IrModelRead, schemas.IrModelWrite)
    register_model("base.ir-model-field", IrModelField, IrModelFieldRepository,
                   ir_model_fields_table, schemas.IrModelFieldRead, schemas.IrModelFieldWrite)
    register_model("base.ir-model-access", IrModelAccess, IrModelAccessRepository,
                   ir_model_access_table, schemas.IrModelAccessRead, schemas.IrModelAccessWrite)
    register_model("base.ir-rule", IrRule, IrRuleRepository, ir_rules_table,
                   schemas.IrRuleRead, schemas.IrRuleWrite)
    register_model("base.ir-ui-menu", IrUiMenu, IrUiMenuRepository, ir_ui_menus_table,
                   schemas.IrUiMenuRead, schemas.IrUiMenuWrite)
    register_model("base.ir-sequence", IrSequence, IrSequenceRepository, ir_sequences_table,
                   schemas.IrSequenceRead, schemas.IrSequenceWrite)
    register_model("base.ir-config-param", IrConfigParam, IrConfigParamRepository,
                   ir_config_params_table, schemas.IrConfigParamRead, schemas.IrConfigParamWrite)
    register_model("base.ir-cron", IrCron, IrCronRepository, ir_crons_table,
                   schemas.IrCronRead, schemas.IrCronWrite)


# ---------------------------------------------------------------------------
# Repositories (imported here to avoid circular imports)
# ---------------------------------------------------------------------------

from modules.base.repositories import (  # noqa: E402
    CompanyRepository,
    IrConfigParamRepository,
    IrCronRepository,
    IrModelAccessRepository,
    IrModelFieldRepository,
    IrModelRepository,
    IrRuleRepository,
    IrSequenceRepository,
    IrUiMenuRepository,
    PartnerRepository,
    TenantRepository,
    UserRepository,
)

