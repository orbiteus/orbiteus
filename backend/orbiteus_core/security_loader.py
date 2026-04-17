"""YAML security loader for Orbiteus modules.

Loads access rights and record rules from security/access.yaml files.
Seeds them into ir_model_access and ir_rule tables in the database,
and reloads the in-memory RBAC cache.

YAML format:
    access:
      - name: unique_name
        role: module.group_name
        model: module.model_name
        read: true
        write: true
        create: true
        delete: false

    record_rules:
      - name: unique_rule_name
        model: module.model_name
        roles: [module.group_name]
        domain: "[('field', '=', 'value')]"
        global: false          # optional, default false
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic validation schemas for YAML structure
# ---------------------------------------------------------------------------

class AccessEntry(BaseModel):
    name: str
    role: str
    model: str
    read: bool = False
    write: bool = False
    create: bool = False
    delete: bool = False

    @field_validator("name", "role", "model")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()


class RecordRule(BaseModel):
    name: str
    model: str
    domain: str = "[]"
    roles: list[str] = []
    is_global: bool = False

    @field_validator("domain")
    @classmethod
    def valid_domain(cls, v: str) -> str:
        # Basic sanity check — must start with [ and end with ]
        v = v.strip()
        if not (v.startswith("[") and v.endswith("]")):
            raise ValueError(f"Domain must be a list string, got: {v!r}")
        return v


class GroupEntry(BaseModel):
    name: str
    label: str = ""


class SecurityConfig(BaseModel):
    groups: list[GroupEntry] = []
    access: list[AccessEntry] = []
    record_rules: list[RecordRule] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_yaml_security(yaml_path: Path) -> SecurityConfig:
    """Parse and validate a security/access.yaml file."""
    if not yaml_path.exists():
        raise FileNotFoundError(f"Security file not found: {yaml_path}")

    with yaml_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    try:
        config = SecurityConfig.model_validate(raw)
    except Exception as e:
        raise ValueError(f"Invalid security YAML at {yaml_path}: {e}") from e

    logger.debug(
        "Loaded security from %s: %d access entries, %d record rules",
        yaml_path, len(config.access), len(config.record_rules),
    )
    return config


def apply_security_to_cache(config: SecurityConfig) -> None:
    """Apply loaded security config to the in-memory RBAC cache."""
    from orbiteus_core.security import rbac

    for entry in config.access:
        role_perms = rbac._model_access.setdefault(entry.role, {})
        role_perms[entry.model] = {
            "read":   entry.read,
            "write":  entry.write,
            "create": entry.create,
            "unlink": entry.delete,
        }

    for rule in config.record_rules:
        rbac._record_rules.setdefault(rule.model, []).append({
            "name":    rule.name,
            "model_name": rule.model,
            "roles":   rule.roles,
            "domain":  _parse_domain(rule.domain),
            "global":  rule.is_global,
        })

    logger.info(
        "RBAC cache updated: +%d access entries, +%d record rules",
        len(config.access), len(config.record_rules),
    )


async def seed_security_to_db(config: SecurityConfig, session, ctx) -> None:
    """Upsert access rights and record rules into ir_model_access and ir_rules tables.

    This persists the security config so it survives cache reloads
    and is visible in the Technical Admin UI.
    """
    from modules.base.controller.repositories import (
        IrModelAccessRepository,
        IrRuleRepository,
    )

    access_repo = IrModelAccessRepository(session, ctx)
    rule_repo = IrRuleRepository(session, ctx)

    for entry in config.access:
        existing, _ = await access_repo.search(
            domain=[("model_name", "=", entry.model), ("role_name", "=", entry.role)],
            limit=1,
        )
        data = {
            "model_name":   entry.model,
            "role_name":    entry.role,
            "perm_read":    entry.read,
            "perm_write":   entry.write,
            "perm_create":  entry.create,
            "perm_unlink":  entry.delete,
        }
        if existing:
            await access_repo.update(existing[0].id, data)
        else:
            await access_repo.create(data)

    import json
    for rule in config.record_rules:
        existing, _ = await rule_repo.search(
            domain=[("name", "=", rule.name)], limit=1,
        )
        data = {
            "name":         rule.name,
            "model_name":   rule.model,
            "domain_force": rule.domain,
            "roles":        rule.roles,
            "is_global":    rule.is_global,
        }
        if existing:
            await rule_repo.update(existing[0].id, data)
        else:
            await rule_repo.create(data)

    logger.info(
        "Security seeded to DB: %d access entries, %d record rules",
        len(config.access), len(config.record_rules),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_domain(domain_str: str) -> list:
    """Parse domain string to list. Returns [] on failure."""
    import ast
    try:
        result = ast.literal_eval(domain_str)
        return result if isinstance(result, list) else []
    except Exception:
        logger.warning("Could not parse domain: %r — using []", domain_str)
        return []
