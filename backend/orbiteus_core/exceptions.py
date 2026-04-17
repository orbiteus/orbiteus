"""Orbiteus domain exceptions."""
from __future__ import annotations

import uuid


class OrbiteusError(Exception):
    """Base exception for all Orbiteus errors."""


class NotFound(OrbiteusError):
    def __init__(self, model: str, record_id: uuid.UUID | str) -> None:
        super().__init__(f"{model} with id={record_id} not found")
        self.model = model
        self.record_id = record_id


class AccessDenied(OrbiteusError):
    def __init__(self, model: str, operation: str) -> None:
        super().__init__(f"Access denied: {operation} on {model}")
        self.model = model
        self.operation = operation


class ModuleNotFound(OrbiteusError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Module '{name}' not found")


class DependencyError(OrbiteusError):
    def __init__(self, module: str, missing_dep: str) -> None:
        super().__init__(f"Module '{module}' requires '{missing_dep}' which is not registered")


class ValidationError(OrbiteusError):
    pass
