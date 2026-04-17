"""ModuleManifest – Pydantic-validated descriptor for Orbiteus modules.

Usage in manifest.py:
    from orbiteus_core.manifest import ModuleManifest

    MANIFEST = ModuleManifest(
        name="crm",
        label="CRM",
        version="1.0.0",
        category="Sales",
        depends_on=["base", "auth"],
        models=["crm.customer", "crm.pipeline"],
        data=["security/access.yaml"],
    )
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class ModuleManifest(BaseModel):
    name: str
    label: str = ""
    version: str = "1.0.0"
    category: str = ""
    description: str = ""
    depends_on: list[str] = []
    models: list[str] = []
    # data: security YAMLs, JSON views, seed YAMLs — processed in order
    data: list[str] = []
    demo: list[str] = []
    # i18n: list of language codes with .po files in module/i18n/
    i18n: list[str] = []

    @field_validator("name")
    @classmethod
    def name_is_slug(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Module name must not be empty")
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                f"Module name must contain only letters, digits and underscores, got: {v!r}"
            )
        return v

    @field_validator("models", mode="before")
    @classmethod
    def models_dot_notation(cls, v: list) -> list:
        for m in v:
            if "." not in str(m):
                raise ValueError(
                    f"Model names must use dot notation (e.g. 'crm.customer'), got: {m!r}"
                )
        return v

    def to_dict(self) -> dict:
        """Backwards-compatible dict for registry code that reads manifest as dict."""
        return self.model_dump()
