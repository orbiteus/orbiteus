"""YAML security loader for Orbiteus modules.

Loads access rights and record rules from security/access.yaml files.
Seeds them into base_model_access and base_rules tables in the database,
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
        domain:
          - field: assigned_user_id
            op: "="
            value: current_user
        global: false          # optional, default false

Legacy domain strings (Odoo-style Python tuples) are still accepted on import.
"""
from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class DomainFilter(BaseModel):
    field: str
    op: str = "="
    value: Any = None


class RecordRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    model: str
    domain: list[list[Any]] = Field(default_factory=list)
    roles: list[str] = []
    is_global: bool = Field(default=False, validation_alias="global")

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_domain_field(cls, v: Any) -> list[list[Any]]:
        return normalize_domain(v)


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

def normalize_domain(value: Any) -> list[list[Any]]:
    """Normalize YAML domain to list of [field, op, value] triples."""
    if value is None:
        return []
    if isinstance(value, str):
        return _parse_domain_string(value)
    if isinstance(value, list):
        triples: list[list[Any]] = []
        for item in value:
            if isinstance(item, DomainFilter):
                triples.append([item.field, item.op, item.value])
            elif isinstance(item, dict):
                filt = DomainFilter.model_validate(item)
                triples.append([filt.field, filt.op, filt.value])
            elif isinstance(item, (list, tuple)) and len(item) == 3:
                triples.append([item[0], item[1], item[2]])
        return triples
    return []


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
            "domain":  rule.domain,
            "global":  rule.is_global,
        })

    logger.info(
        "RBAC cache updated: +%d access entries, +%d record rules",
        len(config.access), len(config.record_rules),
    )


async def seed_security_to_db(config: SecurityConfig, session, ctx) -> None:
    """Upsert access rights and record rules into base_model_access and base_rules tables.

    This persists the security config so it survives cache reloads
    and is visible in the Technical Admin UI.
    """
    from modules.base.controller.repositories import (
        ModelAccessRepository,
        RecordRuleRepository,
    )

    access_repo = ModelAccessRepository(session, ctx)
    rule_repo = RecordRuleRepository(session, ctx)

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

    for rule in config.record_rules:
        existing, _ = await rule_repo.search(
            domain=[("name", "=", rule.name)], limit=1,
        )
        domain_json = json.dumps(rule.domain, ensure_ascii=False)
        data = {
            "name":         rule.name,
            "model_name":   rule.model,
            "domain_force": domain_json,
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

def _parse_domain_string(domain_str: str) -> list[list[Any]]:
    """Parse legacy domain string to triple list. Returns [] on failure."""
    domain_str = domain_str.strip()
    if not domain_str or domain_str == "[]":
        return []
    if not (domain_str.startswith("[") and domain_str.endswith("]")):
        logger.warning("Could not parse domain: %r — using []", domain_str)
        return []
    try:
        result = ast.literal_eval(domain_str)
        if not isinstance(result, list):
            return []
        triples: list[list[Any]] = []
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                triples.append([item[0], item[1], item[2]])
        return triples
    except Exception:
        logger.warning("Could not parse domain: %r — using []", domain_str)
        return []
