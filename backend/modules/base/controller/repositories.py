"""Base module repositories."""
from __future__ import annotations

from orbiteus_core.repository import BaseRepository

from modules.base.model.domain import (
    Company,
    IrConfigParam,
    IrCron,
    IrModelAccess,
    IrModelField,
    IrModel,
    IrRule,
    IrSequence,
    IrUiMenu,
    IrUiView,
    Partner,
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


class PartnerRepository(BaseRepository[Partner]):
    model_name = "base.partner"
    domain_class = Partner

    @property
    def table(self):
        from modules.base.model.mapping import partners_table
        return partners_table


class UserRepository(BaseRepository[User]):
    model_name = "base.user"
    domain_class = User

    @property
    def table(self):
        from modules.base.model.mapping import users_table
        return users_table

    async def get_by_email(self, email: str) -> User | None:
        from sqlalchemy import select
        stmt = select(User).where(self.table.c.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class IrModelRepository(BaseRepository[IrModel]):
    model_name = "base.ir-model"
    domain_class = IrModel

    @property
    def table(self):
        from modules.base.model.mapping import ir_models_table
        return ir_models_table


class IrModelFieldRepository(BaseRepository[IrModelField]):
    model_name = "base.ir-model-field"
    domain_class = IrModelField

    @property
    def table(self):
        from modules.base.model.mapping import ir_model_fields_table
        return ir_model_fields_table


class IrModelAccessRepository(BaseRepository[IrModelAccess]):
    model_name = "base.ir-model-access"
    domain_class = IrModelAccess

    @property
    def table(self):
        from modules.base.model.mapping import ir_model_access_table
        return ir_model_access_table


class IrRuleRepository(BaseRepository[IrRule]):
    model_name = "base.ir-rule"
    domain_class = IrRule

    @property
    def table(self):
        from modules.base.model.mapping import ir_rules_table
        return ir_rules_table


class IrUiMenuRepository(BaseRepository[IrUiMenu]):
    model_name = "base.ir-ui-menu"
    domain_class = IrUiMenu

    @property
    def table(self):
        from modules.base.model.mapping import ir_ui_menus_table
        return ir_ui_menus_table


class IrSequenceRepository(BaseRepository[IrSequence]):
    model_name = "base.ir-sequence"
    domain_class = IrSequence

    @property
    def table(self):
        from modules.base.model.mapping import ir_sequences_table
        return ir_sequences_table


class IrConfigParamRepository(BaseRepository[IrConfigParam]):
    model_name = "base.ir-config-param"
    domain_class = IrConfigParam

    @property
    def table(self):
        from modules.base.model.mapping import ir_config_params_table
        return ir_config_params_table


class IrCronRepository(BaseRepository[IrCron]):
    model_name = "base.ir-cron"
    domain_class = IrCron

    @property
    def table(self):
        from modules.base.model.mapping import ir_crons_table
        return ir_crons_table


class IrUiViewRepository(BaseRepository[IrUiView]):
    model_name = "base.ir-ui-view"
    domain_class = IrUiView

    @property
    def table(self):
        from modules.base.model.mapping import ir_ui_views_table
        return ir_ui_views_table
