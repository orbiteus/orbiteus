"""Structured JSON record-rule domains in security YAML."""
from __future__ import annotations

from orbiteus_core.security_loader import normalize_domain


def test_legacy_domain_string_still_parses():
    domain = normalize_domain("[('assigned_user_id', '=', 'current_user')]")
    assert domain == [["assigned_user_id", "=", "current_user"]]


def test_structured_domain_dict_list():
    domain = normalize_domain(
        [{"field": "company_id", "op": "=", "value": "current_company"}]
    )
    assert domain == [["company_id", "=", "current_company"]]
