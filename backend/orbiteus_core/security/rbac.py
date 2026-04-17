"""RBAC engine – model access checks and record rule application.

Model Access (Level 1):
  Role → Model → [read, write, create, unlink]
  Stored in ir_model_access table (base module).

Record Rules (Level 2):
  Odoo-style domain filters applied at query level.
  Stored in ir_rule table (base module).

In-memory cache is populated at startup from ir_model_access and ir_rule tables.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import Select

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

# In-memory RBAC cache – populated from DB by base module at startup
# Structure:
#   _model_access[role][model_name] = {"read": bool, "write": bool, "create": bool, "unlink": bool}
_model_access: dict[str, dict[str, dict[str, bool]]] = {}

# Record rules cache:
#   _record_rules[model_name] = [{"roles": [...], "domain": [...], "global": bool}, ...]
_record_rules: dict[str, list[dict[str, Any]]] = {}


def reload_access_cache(
    access_entries: list[dict[str, Any]],
    rule_entries: list[dict[str, Any]],
) -> None:
    """Called by base module after seeding ir_model_access and ir_rule."""
    _model_access.clear()
    for entry in access_entries:
        role = entry["role_name"]
        model = entry["model_name"]
        _model_access.setdefault(role, {})[model] = {
            "read": entry.get("perm_read", False),
            "write": entry.get("perm_write", False),
            "create": entry.get("perm_create", False),
            "unlink": entry.get("perm_unlink", False),
        }

    _record_rules.clear()
    for rule in rule_entries:
        model = rule["model_name"]
        _record_rules.setdefault(model, []).append(rule)

    logger.info("RBAC cache reloaded: %d access entries, %d rules", len(access_entries), len(rule_entries))


async def check_model_access(ctx: RequestContext, model_name: str, operation: str) -> bool:
    """Return True if the current user has access to the given model+operation."""
    # Superadmin bypasses all checks
    if ctx.is_superadmin:
        return True

    # Fail closed when access cache is missing or not loaded.
    if not _model_access:
        logger.warning("RBAC cache is empty; denying %s on %s", operation, model_name)
        return False

    for role in ctx.roles:
        perms = _model_access.get(role, {}).get(model_name, {})
        if perms.get(operation, False):
            return True

    return False


def apply_record_rules(
    stmt: Select,
    table: Any,
    ctx: RequestContext,
    model_name: str,
) -> Select:
    """Apply record rules as SQLAlchemy WHERE conditions."""
    if ctx.is_superadmin:
        return stmt

    rules = _record_rules.get(model_name, [])
    for rule in rules:
        # Global rules apply to everyone
        if not rule.get("global", False):
            # Role-specific: only apply if user has the role
            rule_roles = rule.get("roles", [])
            if rule_roles and not any(r in ctx.roles for r in rule_roles):
                continue

        domain = rule.get("domain", [])
        for field_name, operator, value in domain:
            col = table.c.get(field_name)
            if col is None:
                continue
            # Resolve special values
            if value == "current_user":
                value = ctx.user_id
            elif value == "current_company":
                value = ctx.company_id

            if operator == "=":
                stmt = stmt.where(col == value)
            elif operator == "!=":
                stmt = stmt.where(col != value)
            elif operator == "in":
                stmt = stmt.where(col.in_(value))

    return stmt
