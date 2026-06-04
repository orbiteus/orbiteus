"""Base module repositories."""
from __future__ import annotations

import re
import uuid

from orbiteus_core.exceptions import ValidationError
from orbiteus_core.repository import BaseRepository

from modules.base.model.domain import (
    Agent,
    AgentRun,
    Attachment,
    Company,
    ConfigParam,
    UiTranslation,
    ModelAccess,
    RegistryModelField,
    RegistryModel,
    RecordRule,
    Role,
    UiMenu,
    UiView,
    Tenant,
    User,
)


class TenantRepository(BaseRepository[Tenant]):
    model_name = "base.tenant"
    domain_class = Tenant

    @property
    def table(self):
        from modules.base.model.mapping import tenants_table
        return tenants_table


class CompanyRepository(BaseRepository[Company]):
    model_name = "base.company"
    domain_class = Company

    @property
    def table(self):
        from modules.base.model.mapping import companies_table
        return companies_table

    async def _after_create(self, obj: Company) -> None:
        if obj.company_id is None:
            await self.update(obj.id, {"company_id": obj.id})
            obj.company_id = obj.id
        await super()._after_create(obj)


class UserRepository(BaseRepository[User]):
    model_name = "base.user"
    domain_class = User

    @property
    def table(self):
        from modules.base.model.mapping import users_table
        return users_table

    async def get(self, record_id: uuid.UUID) -> User:
        obj = await super().get(record_id)
        await self._hydrate_roles(obj)
        return obj

    async def search(
        self,
        domain: list[tuple[str, str, Any]] | None = None,
        offset: int = 0,
        limit: int = 25,
        order_by: str | None = None,
        order_dir: str = "asc",
    ):
        items, total = await super().search(
            domain=domain, offset=offset, limit=limit,
            order_by=order_by, order_dir=order_dir,
        )
        for obj in items:
            await self._hydrate_roles(obj)
        return items, total

    async def _hydrate_roles(self, user: User) -> None:
        from orbiteus_core.role_resolver import hydrate_user_role_ids

        await hydrate_user_role_ids(self.session, user)

    async def get_by_email(self, email: str) -> User | None:
        from sqlalchemy import select
        stmt = select(User).where(self.table.c.email == email)
        result = await self.session.execute(stmt)
        user = result.scalars().first()
        if user is not None:
            await self._hydrate_roles(user)
        return user

    async def _normalize_role_ids(self, role_ids: list | None) -> list[str]:
        from orbiteus_core.rbac_roles import normalize_role_codes

        return await normalize_role_codes(self.session, role_ids, allow_empty=True)

    async def _normalize_company_ids(self, company_ids: list | None) -> list[str]:
        from sqlalchemy import select

        from modules.base.model.mapping import companies_table

        raw = [str(c).strip() for c in (company_ids or []) if str(c).strip()]
        if not raw:
            return []
        try:
            ids = [uuid.UUID(v) for v in raw]
        except ValueError as exc:
            raise ValidationError("company_ids must be valid UUIDs") from exc

        result = await self.session.execute(
            select(companies_table.c.id).where(companies_table.c.id.in_(ids))
        )
        found = {str(row.id) for row in result}
        missing = set(raw) - found
        if missing:
            raise ValidationError(
                f"Unknown company ids: {', '.join(sorted(missing))}",
            )
        return [str(i) for i in ids]

    async def _normalize_preferences(self, data: dict) -> dict:
        from orbiteus_core.i18n import normalize_timezone
        from orbiteus_core.i18n_registry import normalize_registered_language

        if "language" in data:
            from orbiteus_core.module_catalog import load_enabled_map

            enabled_map = await load_enabled_map(self.session, self.ctx)
            data["language"] = normalize_registered_language(
                str(data["language"]),
                enabled_map=enabled_map,
            )
        if "timezone" in data:
            data["timezone"] = normalize_timezone(str(data["timezone"]))
        return data

    async def _before_create(self, data: dict) -> dict:
        data = await super()._before_create(data)
        data = await self._normalize_preferences(data)
        if not data.get("password_hash"):
            pwd = data.pop("password", None)
            if not pwd:
                raise ValidationError("Password is required for new users")
            from orbiteus_core.security.passwords import hash_password

            data["password_hash"] = hash_password(pwd)
        else:
            data.pop("password", None)
        role_ids = await self._normalize_role_ids(data.get("role_ids"))
        data["role_ids"] = role_ids or ["base.group_user"]
        if "company_ids" in data:
            data["company_ids"] = await self._normalize_company_ids(data.get("company_ids"))
        elif not data.get("company_ids") and self.ctx.company_id:
            data["company_ids"] = [str(self.ctx.company_id)]
        return data

    async def _after_create(self, obj: User) -> None:
        from orbiteus_core.role_resolver import sync_user_roles

        obj.role_ids = await sync_user_roles(
            self.session, obj.id, obj.role_ids or [],
        )
        await super()._after_create(obj)

    async def _before_write(self, obj: User, data: dict) -> dict:
        data = await super()._before_write(obj, data)
        data = await self._normalize_preferences(data)
        if "password" in data:
            pwd = data.pop("password")
            if pwd:
                from orbiteus_core.security.passwords import hash_password

                data["password_hash"] = hash_password(pwd)
        if "role_ids" in data:
            data["role_ids"] = await self._normalize_role_ids(data["role_ids"])
        if "company_ids" in data:
            data["company_ids"] = await self._normalize_company_ids(data["company_ids"])
        return data

    async def _after_write(self, obj: User, old_snapshot: dict) -> None:
        if "role_ids" in old_snapshot or obj.role_ids:
            from orbiteus_core.role_resolver import sync_user_roles

            new_codes = obj.role_ids or []
            old_codes = old_snapshot.get("role_ids") or []
            if set(new_codes) != set(old_codes):
                obj.role_ids = await sync_user_roles(self.session, obj.id, new_codes)
        await super()._after_write(obj, old_snapshot)


class RegistryModelRepository(BaseRepository[RegistryModel]):
    model_name = "base.registry-model"
    domain_class = RegistryModel

    @property
    def table(self):
        from modules.base.model.mapping import base_models_table
        return base_models_table


class RegistryModelFieldRepository(BaseRepository[RegistryModelField]):
    model_name = "base.registry-model-field"
    domain_class = RegistryModelField

    @property
    def table(self):
        from modules.base.model.mapping import base_model_fields_table
        return base_model_fields_table


class ModelAccessRepository(BaseRepository[ModelAccess]):
    model_name = "base.model-access"
    domain_class = ModelAccess

    @property
    def table(self):
        from modules.base.model.mapping import base_model_access_table
        return base_model_access_table

    async def _before_create(self, data: dict) -> dict:
        data = await super()._before_create(data)
        from orbiteus_core.rbac_roles import normalize_role_codes

        data["role_name"] = (
            await normalize_role_codes(
                self.session, [data.get("role_name", "")], allow_empty=False,
            )
        )[0]
        return data

    async def _before_write(self, obj: ModelAccess, data: dict) -> dict:
        data = await super()._before_write(obj, data)
        if "role_name" in data:
            from orbiteus_core.rbac_roles import normalize_role_codes

            data["role_name"] = (
                await normalize_role_codes(
                    self.session, [data["role_name"]], allow_empty=False,
                )
            )[0]
        return data


_ROLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*\.group_[a-z0-9_]+$")


class RoleRepository(BaseRepository[Role]):
    model_name = "base.role"
    domain_class = Role

    @property
    def table(self):
        from modules.base.model.mapping import base_roles_table
        return base_roles_table

    async def _before_create(self, data: dict) -> dict:
        data = await super()._before_create(data)
        data["is_system"] = False
        data["code"] = self._normalize_code(data.get("code", ""))
        return data

    async def _before_write(self, obj: Role, data: dict) -> dict:
        data = await super()._before_write(obj, data)
        if obj.is_system:
            if "code" in data and data["code"] != obj.code:
                raise ValidationError("System role code cannot be changed")
            data.pop("is_system", None)
        if "code" in data:
            data["code"] = self._normalize_code(data["code"])
        return data

    async def _before_unlink(self, obj: Role) -> None:
        await super()._before_unlink(obj)
        if obj.is_system:
            raise ValidationError("System roles cannot be deleted")
        from orbiteus_core.rbac_roles import purge_role_references

        await purge_role_references(self.session, obj.code)

    @staticmethod
    def _normalize_code(raw: str) -> str:
        code = raw.strip()
        if not _ROLE_CODE_RE.match(code):
            raise ValidationError(
                "Role code must match module.group_name (e.g. base.group_sales)",
            )
        return code


class RecordRuleRepository(BaseRepository[RecordRule]):
    model_name = "base.record-rule"
    domain_class = RecordRule

    @property
    def table(self):
        from modules.base.model.mapping import base_rules_table
        return base_rules_table

    async def _before_create(self, data: dict) -> dict:
        data = await super()._before_create(data)
        from orbiteus_core.rbac_roles import normalize_role_codes

        data["roles"] = await normalize_role_codes(
            self.session, data.get("roles"), allow_empty=True,
        )
        return data

    async def _before_write(self, obj: RecordRule, data: dict) -> dict:
        data = await super()._before_write(obj, data)
        if "roles" in data:
            from orbiteus_core.rbac_roles import normalize_role_codes

            data["roles"] = await normalize_role_codes(
                self.session, data["roles"], allow_empty=True,
            )
        return data


class UiMenuRepository(BaseRepository[UiMenu]):
    model_name = "base.ui-menu"
    domain_class = UiMenu

    @property
    def table(self):
        from modules.base.model.mapping import base_ui_menus_table
        return base_ui_menus_table


class ConfigParamRepository(BaseRepository[ConfigParam]):
    model_name = "base.config-param"
    domain_class = ConfigParam

    @property
    def table(self):
        from modules.base.model.mapping import base_config_params_table
        return base_config_params_table


class UiTranslationRepository(BaseRepository[UiTranslation]):
    model_name = "base.ui-translation"
    domain_class = UiTranslation

    @property
    def table(self):
        from modules.base.model.mapping import base_ui_translations_table
        return base_ui_translations_table

    def _invalidate_i18n_cache(self, lang: str | None = None) -> None:
        from orbiteus_core.i18n_registry import clear_ui_translation_cache

        clear_ui_translation_cache()

    async def _after_create(self, record: UiTranslation) -> None:
        await super()._after_create(record)
        self._invalidate_i18n_cache(record.lang)

    async def _after_write(self, record: UiTranslation, old_snapshot: dict) -> None:
        await super()._after_write(record, old_snapshot)
        self._invalidate_i18n_cache(record.lang)

    async def _after_unlink(self, record_id: uuid.UUID) -> None:
        await super()._after_unlink(record_id)
        self._invalidate_i18n_cache()


class UiViewRepository(BaseRepository[UiView]):
    model_name = "base.ui-view"
    domain_class = UiView

    @property
    def table(self):
        from modules.base.model.mapping import base_ui_views_table
        return base_ui_views_table


_AGENT_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_AGENT_STATUSES = frozenset({"pending", "running", "completed", "failed"})


class AgentRepository(BaseRepository[Agent]):
    model_name = "base.agent"
    domain_class = Agent

    @property
    def table(self):
        from modules.base.model.mapping import base_agents_table
        return base_agents_table

    async def _before_create(self, data: dict) -> dict:
        data = await super()._before_create(data)
        data["is_system"] = False
        data["slug"] = self._normalize_slug(data.get("slug", ""))
        data["allowed_models"] = list(data.get("allowed_models") or [])
        data["allowed_actions"] = list(data.get("allowed_actions") or [])
        data["allowed_delegate_slugs"] = list(data.get("allowed_delegate_slugs") or [])
        return data

    async def _before_write(self, obj: Agent, data: dict) -> dict:
        data = await super()._before_write(obj, data)
        if obj.is_system:
            data.pop("is_system", None)
            if "slug" in data and data["slug"] != obj.slug:
                raise ValidationError("System agent slug cannot be changed")
        if "slug" in data:
            data["slug"] = self._normalize_slug(data["slug"])
        if "allowed_models" in data:
            data["allowed_models"] = list(data["allowed_models"] or [])
        if "allowed_actions" in data:
            data["allowed_actions"] = list(data["allowed_actions"] or [])
        if "allowed_delegate_slugs" in data:
            data["allowed_delegate_slugs"] = list(data["allowed_delegate_slugs"] or [])
        return data

    async def _before_unlink(self, obj: Agent) -> None:
        await super()._before_unlink(obj)
        if obj.is_system:
            raise ValidationError("System agents cannot be deleted")

    @staticmethod
    def _normalize_slug(raw: str) -> str:
        slug = raw.strip().lower()
        if not _AGENT_SLUG_RE.match(slug):
            raise ValidationError(
                "Agent slug must match [a-z][a-z0-9-]* (e.g. crm-assistant)",
            )
        return slug


class AttachmentRepository(BaseRepository[Attachment]):
    model_name = "base.attachment"
    domain_class = Attachment

    @property
    def table(self):
        from modules.base.model.mapping import base_attachments_table
        return base_attachments_table


class AgentRunRepository(BaseRepository[AgentRun]):
    model_name = "base.agent-run"
    domain_class = AgentRun

    @property
    def table(self):
        from modules.base.model.mapping import base_agent_runs_table
        return base_agent_runs_table

    async def _before_create(self, data: dict) -> dict:
        data = await super()._before_create(data)
        status = data.get("status", "pending")
        if status not in _AGENT_STATUSES:
            raise ValidationError(f"Invalid agent run status: {status!r}")
        data["tool_trace"] = list(data.get("tool_trace") or [])
        return data

    async def _before_write(self, obj: AgentRun, data: dict) -> dict:
        data = await super()._before_write(obj, data)
        if "status" in data and data["status"] not in _AGENT_STATUSES:
            raise ValidationError(f"Invalid agent run status: {data['status']!r}")
        if "tool_trace" in data:
            data["tool_trace"] = list(data["tool_trace"] or [])
        return data
