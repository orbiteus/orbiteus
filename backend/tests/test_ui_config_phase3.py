"""UI config: many2one + monetary metadata for Phase 3 frontend."""
from __future__ import annotations

from modules.crm.model.schemas import OpportunityWrite
from orbiteus_core.ui_config import (
    _field_label,
    _fk_field_label,
    pydantic_schema_to_fields,
)


def test_opportunity_fields_include_many2one_and_monetary() -> None:
    fields = pydantic_schema_to_fields(OpportunityWrite, "crm.opportunity")
    by_name = {f["name"]: f for f in fields}

    assert by_name["customer_id"]["type"] == "many2one"
    assert by_name["customer_id"]["relation"] == "crm.customer"
    assert by_name["assigned_user_id"]["relation"] == "base.user"
    assert by_name["expected_revenue"]["type"] == "monetary"
    assert by_name["tags"]["type"] == "tags"


def test_many2one_labels_strip_id_suffix() -> None:
    """FK fields should render as 'Assigned User', not 'Assigned User Id'."""
    fields = pydantic_schema_to_fields(OpportunityWrite, "crm.opportunity")
    by_name = {f["name"]: f for f in fields}

    assert by_name["customer_id"]["label"] == "Customer"
    assert by_name["assigned_user_id"]["label"] == "Assigned User"


def test_fk_field_label_helper() -> None:
    """Trailing _id is stripped; single underscores become spaces; title-cased."""
    assert _fk_field_label("assigned_user_id") == "Assigned User"
    assert _fk_field_label("customer_id") == "Customer"
    assert _fk_field_label("parent_id") == "Parent"
    # Names without _id pass through unchanged (aside from humanisation).
    assert _fk_field_label("status") == "Status"


def test_field_label_helper_keeps_non_fk_id_suffix() -> None:
    """Business identifiers like tax_id must keep their suffix in default path."""
    assert _field_label("tax_id") == "Tax Id"
    assert _field_label("email") == "Email"
    assert _field_label("first_name") == "First Name"
