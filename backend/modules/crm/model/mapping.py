"""CRM module – SQLAlchemy imperative mapping."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.auto_router import register_model
from orbiteus_core.db import metadata
from orbiteus_core.mapper import make_base_columns, register_mapping

from modules.crm.model.domain import Customer, Opportunity, Pipeline, Stage
from modules.crm.model import schemas


# Module-level table references (set in setup())
customers_table = None
pipelines_table = None
stages_table = None
opportunities_table = None


def _build_tables():
    from sqlalchemy import Table

    customers = Table(
        "crm_customers",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("email", String(255)),
        Column("phone", String(50)),
        Column("mobile", String(50)),
        Column("website", String(255)),
        Column("street", String(255)),
        Column("city", String(100)),
        Column("country_code", String(5), server_default="PL"),
        Column("is_company", Boolean, server_default="false"),
        Column("vat", String(50)),
        Column("status", String(50), server_default="lead", index=True),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("partner_id", UUID(as_uuid=True), ForeignKey("base_partners.id"), nullable=True),
        Column("tags", JSON, server_default="[]"),
        Column("notes", Text),
    )

    pipelines = Table(
        "crm_pipelines",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("description", Text),
        Column("currency_code", String(10), server_default="PLN"),
        Column("is_default", Boolean, server_default="false"),
    )

    stages = Table(
        "crm_stages",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("pipeline_id", UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=False),
        Column("sequence", Integer, server_default="10"),
        Column("probability", Float, server_default="0"),
        Column("is_won", Boolean, server_default="false"),
        Column("is_lost", Boolean, server_default="false"),
        Column("fold", Boolean, server_default="false"),
    )

    opportunities = Table(
        "crm_opportunities",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("customer_id", UUID(as_uuid=True), ForeignKey("crm_customers.id"), nullable=True),
        Column("pipeline_id", UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=True),
        Column("stage_id", UUID(as_uuid=True), ForeignKey("crm_stages.id"), nullable=True),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("expected_revenue", Float, server_default="0"),
        Column("probability", Float, server_default="0"),
        Column("close_date", String(50)),
        Column("description", Text),
        Column("lost_reason", String(500)),
        Column("tags", JSON, server_default="[]"),
        Column("workflow_run_id", String(255)),
    )

    return customers, pipelines, stages, opportunities


def setup() -> None:
    """Called by ModuleRegistry during module load."""
    global customers_table, pipelines_table, stages_table, opportunities_table

    customers_table, pipelines_table, stages_table, opportunities_table = _build_tables()

    register_mapping(Customer, customers_table)
    register_mapping(Pipeline, pipelines_table)
    register_mapping(Stage, stages_table)
    register_mapping(Opportunity, opportunities_table)

    # Register for auto-CRUD
    from modules.crm.controller.repositories import (
        CustomerRepository,
        OpportunityRepository,
        PipelineRepository,
        StageRepository,
    )

    register_model("crm.customer", Customer, CustomerRepository, customers_table,
                   schemas.CustomerRead, schemas.CustomerWrite)
    register_model("crm.pipeline", Pipeline, PipelineRepository, pipelines_table,
                   schemas.PipelineRead, schemas.PipelineWrite)
    register_model("crm.stage", Stage, StageRepository, stages_table,
                   schemas.StageRead, schemas.StageWrite)
    register_model("crm.opportunity", Opportunity, OpportunityRepository, opportunities_table,
                   schemas.OpportunityRead, schemas.OpportunityWrite)
