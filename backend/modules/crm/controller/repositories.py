"""CRM module repositories."""
from __future__ import annotations

import uuid
from typing import Any

from orbiteus_core.repository import BaseRepository

from modules.crm.model.domain import Customer, Opportunity, Pipeline, Stage


class CustomerRepository(BaseRepository[Customer]):
    model_name = "crm.customer"
    domain_class = Customer

    @property
    def table(self):
        from modules.crm.model.mapping import customers_table
        return customers_table


class PipelineRepository(BaseRepository[Pipeline]):
    model_name = "crm.pipeline"
    domain_class = Pipeline

    @property
    def table(self):
        from modules.crm.model.mapping import pipelines_table
        return pipelines_table


class StageRepository(BaseRepository[Stage]):
    model_name = "crm.stage"
    domain_class = Stage

    @property
    def table(self):
        from modules.crm.model.mapping import stages_table
        return stages_table

    async def create(self, data: dict[str, Any]) -> Stage:
        await self._normalize_terminal_flags_on_create(data)
        return await super().create(data)

    async def update(self, record_id: uuid.UUID, data: dict[str, Any]) -> Stage:
        current = await self.get(record_id)
        pipeline_id = data.get("pipeline_id", current.pipeline_id)
        is_won = bool(data.get("is_won", current.is_won))
        is_lost = bool(data.get("is_lost", current.is_lost))
        self._assert_terminal_flags(is_won, is_lost)
        if is_won:
            await self._unset_other_terminal_stage(pipeline_id, "is_won", record_id)
        if is_lost:
            await self._unset_other_terminal_stage(pipeline_id, "is_lost", record_id)
        return await super().update(record_id, data)

    def _assert_terminal_flags(self, is_won: bool, is_lost: bool) -> None:
        if is_won and is_lost:
            raise ValueError("Stage cannot be both won and lost.")

    async def _normalize_terminal_flags_on_create(self, data: dict[str, Any]) -> None:
        pipeline_id = data.get("pipeline_id")
        if not pipeline_id:
            raise ValueError("pipeline_id is required for stage.")
        is_won = bool(data.get("is_won", False))
        is_lost = bool(data.get("is_lost", False))
        self._assert_terminal_flags(is_won, is_lost)
        if is_won:
            await self._unset_other_terminal_stage(pipeline_id, "is_won")
        if is_lost:
            await self._unset_other_terminal_stage(pipeline_id, "is_lost")

    async def _unset_other_terminal_stage(
        self,
        pipeline_id: uuid.UUID,
        flag: str,
        current_id: uuid.UUID | None = None,
    ) -> None:
        stages, _ = await self.search(domain=[("pipeline_id", "=", pipeline_id)], limit=500)
        for stage in stages:
            if getattr(stage, flag, False) and (current_id is None or stage.id != current_id):
                await super().update(stage.id, {flag: False})


class OpportunityRepository(BaseRepository[Opportunity]):
    model_name = "crm.opportunity"
    domain_class = Opportunity

    @property
    def table(self):
        from modules.crm.model.mapping import opportunities_table
        return opportunities_table

    async def create(self, data: dict[str, Any]) -> Opportunity:
        stage_id = data.get("stage_id")
        pipeline_id = data.get("pipeline_id")

        stage_repo = StageRepository(self.session, self.ctx)
        pipeline_repo = PipelineRepository(self.session, self.ctx)

        if stage_id and not pipeline_id:
            stage = await stage_repo.get(stage_id)
            data["pipeline_id"] = stage.pipeline_id
            if "probability" not in data:
                data["probability"] = stage.probability

        if not data.get("pipeline_id"):
            pipeline = await self._pick_default_pipeline(pipeline_repo)
            if pipeline:
                data["pipeline_id"] = pipeline.id

        if not data.get("stage_id") and data.get("pipeline_id"):
            stage = await self._pick_default_stage(stage_repo, data["pipeline_id"])
            if stage:
                data["stage_id"] = stage.id
                if "probability" not in data:
                    data["probability"] = stage.probability

        if data.get("stage_id") and data.get("pipeline_id"):
            stage = await stage_repo.get(data["stage_id"])
            data["pipeline_id"] = stage.pipeline_id
            if "probability" not in data:
                data["probability"] = stage.probability

        return await super().create(data)

    async def _pick_default_pipeline(self, pipeline_repo: PipelineRepository) -> Pipeline | None:
        defaults, _ = await pipeline_repo.search(domain=[("is_default", "=", True)], limit=1)
        if defaults:
            return defaults[0]
        pipelines, _ = await pipeline_repo.search(limit=1)
        return pipelines[0] if pipelines else None

    async def _pick_default_stage(
        self,
        stage_repo: StageRepository,
        pipeline_id: uuid.UUID,
    ) -> Stage | None:
        stages, _ = await stage_repo.search(domain=[("pipeline_id", "=", pipeline_id)], limit=500)
        if not stages:
            return None
        non_terminal = [s for s in stages if not s.is_won and not s.is_lost]
        pool = non_terminal if non_terminal else list(stages)
        return sorted(
            pool,
            key=lambda s: (
                s.sequence,
                s.create_date.isoformat() if s.create_date else "",
            ),
        )[0]

    async def get_by_stage(self, stage_id) -> list[Opportunity]:
        """Get all opportunities in a given stage (for kanban)."""
        items, _ = await self.search(domain=[("stage_id", "=", stage_id)])
        return list(items)
