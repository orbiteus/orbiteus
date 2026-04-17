"""CRM module repositories."""
from __future__ import annotations

from orbiteus_core.repository import BaseRepository

from modules.crm.domain import Customer, Opportunity, Pipeline, Stage


class CustomerRepository(BaseRepository[Customer]):
    model_name = "crm.customer"
    domain_class = Customer

    @property
    def table(self):
        from modules.crm.mapping import customers_table
        return customers_table


class PipelineRepository(BaseRepository[Pipeline]):
    model_name = "crm.pipeline"
    domain_class = Pipeline

    @property
    def table(self):
        from modules.crm.mapping import pipelines_table
        return pipelines_table


class StageRepository(BaseRepository[Stage]):
    model_name = "crm.stage"
    domain_class = Stage

    @property
    def table(self):
        from modules.crm.mapping import stages_table
        return stages_table


class OpportunityRepository(BaseRepository[Opportunity]):
    model_name = "crm.opportunity"
    domain_class = Opportunity

    @property
    def table(self):
        from modules.crm.mapping import opportunities_table
        return opportunities_table

    async def get_by_stage(self, stage_id) -> list[Opportunity]:
        """Get all opportunities in a given stage (for kanban)."""
        items, _ = await self.search(domain=[("stage_id", "=", stage_id)])
        return list(items)
