"""UI config: many2one + monetary metadata for Phase 3 frontend."""
from __future__ import annotations

from modules.crm.model.schemas import OpportunityWrite
from orbiteus_core.ui_config import pydantic_schema_to_fields


def test_opportunity_fields_include_many2one_and_monetary() -> None:
    fields = pydantic_schema_to_fields(OpportunityWrite, "crm.opportunity")
    by_name = {f["name"]: f for f in fields}

    assert by_name["customer_id"]["type"] == "many2one"
    assert by_name["customer_id"]["relation"] == "crm.customer"
    assert by_name["assigned_user_id"]["relation"] == "base.user"
    assert by_name["expected_revenue"]["type"] == "monetary"
    assert by_name["tags"]["type"] == "tags"
