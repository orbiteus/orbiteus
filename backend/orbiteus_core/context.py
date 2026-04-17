"""Request context – tenant, company, and user information per request."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    """Carries authenticated request context through the system."""

    tenant_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    roles: list[str] = field(default_factory=list)
    is_superadmin: bool = False

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    def has_role(self, role: str) -> bool:
        return role in self.roles or self.is_superadmin
