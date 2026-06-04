"""Base module security – default access rights for system roles."""
from __future__ import annotations

import logging

from orbiteus_core.security.rbac import reload_access_cache

logger = logging.getLogger(__name__)

# Default access rights (seeded into RBAC cache at startup)
# Format: {"role_name": str, "model_name": str, "perm_read/write/create/unlink": bool}
DEFAULT_ACCESS_RIGHTS = [
    # Superadmin gets everything (enforced in rbac.py via is_superadmin flag)
    # Admin role
    *[
        {
            "role_name": "base.group_system",
            "model_name": model,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": True,
        }
        for model in [
            "base.tenant", "base.company", "base.user", "base.role",
            "base.registry-model", "base.registry-model-field", "base.model-access",
            "base.record-rule", "base.ui-menu", "base.ui-view",
            "base.config-param",
            "base.agent", "base.agent-run",
        ]
    ],
    {
        "role_name": "base.group_user",
        "model_name": "base.company",
        "perm_read": True,
        "perm_write": False,
        "perm_create": False,
        "perm_unlink": False,
    },
]


def setup() -> None:
    """Seed RBAC cache with default access rights."""
    reload_access_cache(DEFAULT_ACCESS_RIGHTS, [])
    logger.info("Base module security loaded: %d access entries", len(DEFAULT_ACCESS_RIGHTS))
